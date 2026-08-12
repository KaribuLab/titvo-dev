## ADDED Requirements

### Requirement: El indexer detecta un checkpoint existente y reanuda
Cuando `IndexRepositoryUseCase.execute` recibe `branch` sin `commit_sha` (modo full) y existe un checkpoint en el artifact store para el `(repository_url, branch, commit_sha)` resuelto, el sistema SHALL descargar el checkpoint, abrir el DB local y omitir del split/embed los `file_path` que ya figuran en la tabla `indexed_files`.

#### Scenario: Checkpoint presente y hay archivos ya procesados
- **WHEN** `_execute_full` se ejecuta para un commit con checkpoint descargable
- **THEN** el sistema carga el DB local, consulta la tabla `indexed_files` y procesa solo los archivos cuyo `file_path` no está registrado

#### Scenario: Checkpoint ausente (run nuevo)
- **WHEN** `_execute_full` se ejecuta para un commit sin checkpoint descargable
- **THEN** el sistema crea un DB local vacío y procesa todos los archivos normalmente

#### Scenario: Checkpoint corrupto o DB inválido
- **WHEN** el checkpoint descargado no se puede abrir como sqlite-vec válido
- **THEN** el sistema registra el error, borra el archivo local y trata el caso como "run nuevo" (sin checkpoint)

### Requirement: Flush periódico de checkpoint a S3
Durante `_execute_full`, después de procesar cada lote de `TITVO_CHECKPOINT_EVERY_N_FILES` archivos (default 100), el sistema SHALL subir el DB local completo al artifact store bajo la clave de checkpoint correspondiente al `(repository_url, branch, commit_sha)`. El flush SHALL ser no-bloqueante respecto al split/embed siguiente (registra y continúa).

#### Scenario: Flush tras N archivos procesados
- **WHEN** el contador de archivos procesados en el run alcanza un múltiplo de `TITVO_CHECKPOINT_EVERY_N_FILES`
- **THEN** el sistema invoca `IArtifactStorePort.upload_checkpoint(repository_url, branch, commit_sha, db_path)` antes de procesar el siguiente archivo

#### Scenario: Flush final al terminar full index con éxito
- **WHEN** `_execute_full` completa todos los archivos y la subida final a S3 fue exitosa
- **THEN** el sistema elimina el checkpoint del artifact store para evitar archivos huérfanos

#### Scenario: Job interrumpido entre flush y fin
- **WHEN** el proceso muere después de un flush exitoso pero antes del upload final
- **THEN** el siguiente run detecta el checkpoint, lo descarga y reanuda sin perder progreso

### Requirement: Tabla `indexed_files` para tracking idempotente intra-commit
El sqlite-vec local SHALL contener una tabla `indexed_files(file_path TEXT PRIMARY KEY, indexed_at TEXT NOT NULL)` que persiste por cada archivo cuyo split+embed se completó exitosamente. La tabla SHALL crearse al inicializar el DB si no existe.

#### Scenario: Archivo procesado se registra
- **WHEN** un archivo termina de ser procesado por `_process_files` (todos sus chunks insertados en `chunks`)
- **THEN** el sistema ejecuta `INSERT OR IGNORE INTO indexed_files(file_path, indexed_at) VALUES (?, ?)` con timestamp UTC ISO-8601

#### Scenario: Resume omite archivos ya en `indexed_files`
- **WHEN** `_process_files` recibe una lista de archivos y existe un DB local con `indexed_files`
- **THEN** filtra la lista antes de splitear, conservando solo los archivos cuyo path no está en la tabla

#### Scenario: Crash entre split y registro
- **WHEN** el proceso muere después de partir y embeber un archivo pero antes del `INSERT` en `indexed_files`
- **THEN** el resume detecta el archivo no registrado y lo reprocesa (posibles duplicados en `chunks` por file_path, aceptables para RAG recall)

### Requirement: Artifact store expone upload y download de checkpoints
`IArtifactStorePort` SHALL declarar los métodos:
- `upload_checkpoint(repository_url: str, branch: str, commit_sha: str, db_path: str) -> str` — sube el DB como checkpoint, retorna la S3 key.
- `download_checkpoint(repository_url: str, branch: str, commit_sha: str, target_path: str) -> Optional[str]` — descarga a `target_path`; retorna la ruta local o `None` si no existe.

La clave S3 del checkpoint SHALL seguir el template `TITVO_CHECKPOINT_KEY` con placeholders `{repo_host}`, `{owner}`, `{repo}`, `{branch}`, `{commit_sha}`. Default: `{repo_host}/{owner}/{repo}/branches/{branch}/checkpoints/{commit_sha}/index.db`.

#### Scenario: Subida de checkpoint exitosa
- **WHEN** `upload_checkpoint` se invoca con un DB local existente y permisos S3 válidos
- **THEN** el archivo se sube al bucket configurado bajo la clave templateada y retorna la key absoluta

#### Scenario: Descarga de checkpoint existente
- **WHEN** `download_checkpoint` se invoca y el objeto existe en S3
- **THEN** el archivo se descarga a `target_path` y retorna esa ruta

#### Scenario: Descarga cuando no hay checkpoint
- **WHEN** `download_checkpoint` se invoca y no existe el objeto en S3
- **THEN** retorna `None` sin lanzar excepción

### Requirement: IndexResultDto reporta archivos omitidos por resume
`IndexResultDto` SHALL incluir el campo `files_skipped_resume: int` que cuantifica cuántos archivos se omitieron por estar en la tabla `indexed_files` al reanudar. En runs sin resume SHALL ser 0.

#### Scenario: Run con resume parcial
- **WHEN** el run reanuda desde un checkpoint con 4500 archivos ya en `indexed_files` y procesa 6218 nuevos
- **THEN** `IndexResultDto.files_skipped_resume == 4500` y `IndexResultDto.files_processed == 6218`

#### Scenario: Run fresh sin checkpoint
- **WHEN** el run inicia sin checkpoint
- **THEN** `IndexResultDto.files_skipped_resume == 0`

### Requirement: Snapshot del repo local acelera el resume
El sistema SHALL subir a S3 un tarball `.tar.gz` del directorio `.git` local (sin working tree) una sola vez por run, después del primer `get_files()` exitoso. En resume, SHALL descargar y extraer el snapshot antes del `get_files()` y usar el repo restaurado en lugar de hacer `git fetch`. El snapshot SHALL eliminarse al finalizar el full index con éxito.

#### Scenario: Subida del snapshot tras el primer get_files exitoso
- **WHEN** `_execute_full` completa el primer `get_files()` (lista + contenido leído) y el adapter tiene un `_repo_dir` válido
- **THEN** el sistema invoca `IArtifactStorePort.upload_source_snapshot(repository_url, branch, commit_sha, repo_dir)` y registra el tamaño del tarball en log `INFO`

#### Scenario: Resume usa snapshot y evita git fetch
- **WHEN** `_execute_full` detecta checkpoint descargable y existe `repo.tar.gz` en la misma key
- **THEN** descarga el tarball, lo extrae a un temp dir, llama `IRepositoryProvider.restore_from_snapshot(temp_dir, commit_sha)` antes de `get_files`, y el adapter skipea el `git fetch` (usa el repo local restaurado)

#### Scenario: Snapshot ausente pero checkpoint presente
- **WHEN** existe `index.db` de checkpoint pero NO `repo.tar.gz` en la misma key
- **THEN** el sistema degrada a `git fetch --depth=1` normal y loguea `WARNING: source snapshot missing, falling back to git fetch`

#### Scenario: Cleanup del snapshot tras éxito
- **WHEN** el upload final del DB a S3 fue exitoso
- **THEN** el sistema elimina `repo.tar.gz` del artifact store (mantiene la S3 key limpia post-éxito)

#### Scenario: Snapshot corrupto
- **WHEN** el tarball descargado no se puede extraer o no contiene un `.git` válido
- **THEN** el sistema registra `WARNING`, elimina el archivo y degrada a `git fetch` normal

### Requirement: get_files acepta exclude_paths para reducir cat-file
`IRepositoryProvider.get_files(url, commit_sha, exclude_paths)` SHALL aceptar opcionalmente un `set[str]` de `file_path` que ya fueron indexados y SHALL omitir el `git cat-file blob` para esos paths (retornando solo los archivos cuyo path no está en el set).

#### Scenario: Resume pasa exclude_paths derivados de indexed_files
- **WHEN** `_execute_full` tiene un DB local con N paths en `indexed_files`
- **THEN** invoca `repository_provider.get_files(url, sha, exclude_paths={esos N paths})` y solo lee el contenido de los archivos restantes

#### Scenario: Exclude_paths reduce subprocess calls
- **WHEN** `exclude_paths` contiene 19000 de los 20000 paths
- **THEN** el adapter ejecuta `git ls-tree` (lista paths) y `git cat-file blob` solo para los 1000 paths no excluidos

#### Scenario: exclude_paths vacío o ausente
- **WHEN** `get_files` se invoca sin `exclude_paths` (o con set vacío)
- **THEN** el comportamiento es idéntico al actual (lee todos los blobs)

### Requirement: Batching explícito de embeddings con tamaño configurable
`LangChainEmbeddingAdapter.embed(texts)` SHALL particionar la lista de entrada en bloques de `TITVO_EMBEDDING_BATCH_SIZE` chunks (default 1000) y enviar cada bloque con un `embed_documents` independiente. El adapter SHALL loguear `INFO Embedded batch i/N chunks=N duration_ms=Y` por bloque, SHALL reintentar cada bloque hasta 3 veces ante error transitorio, y SHALL retornar la concatenación de los embeddings en el orden original.

#### Scenario: Batching funcionado con tamaño por defecto
- **WHEN** `embed(texts)` recibe 3500 chunks y `TITVO_EMBEDDING_BATCH_SIZE` no está definido (default 1000)
- **THEN** el adapter hace 4 llamadas al provider (1000 + 1000 + 1000 + 500) y retorna 3500 embeddings

#### Scenario: Batching con tamaño custom
- **WHEN** `TITVO_EMBEDDING_BATCH_SIZE=500` y `embed` recibe 1200 chunks
- **THEN** el adapter hace 3 llamadas (500 + 500 + 200) y retorna 1200 embeddings

#### Scenario: Batch vacío o lista vacía
- **WHEN** `embed` recibe una lista vacía o un solo batch que resulta en 0 chunks
- **THEN** el adapter retorna `[]` sin llamar al provider

#### Scenario: Reintento per-batch ante error transitorio
- **WHEN** el provider retorna error 429 o 5xx en el batch N
- **THEN** el adapter reintenta el mismo batch hasta 3 veces con backoff exponencial (1s, 2s, 4s), loguea `WARNING Retry batch N attempt=X error=...` y continúa si recupera, o aborta si supera el máximo

### Requirement: Streaming del pipeline split → embed → insert
El flujo de indexación SHALL procesar archivos en bloques y, dentro de cada bloque, consumir chunks como `Iterator` (no como `List`). El `ICodeSplitter` SHALL exponer `iter_chunks(file) -> Iterator[str]` y el `IEmbeddingProvider` SHALL exponer `embed_iter(texts_iter: Iterator[str]) -> Iterator[list[float]]` que agrupa automáticamente en batches de `TITVO_EMBEDDING_BATCH_SIZE` y emite embeddings uno a uno. El use case SHALL consumir ambos iteradores en un zip para llamar `vector_store.insert_one(...)` por cada chunk, sin acumular listas en memoria.

#### Scenario: Memoria pico del bloque es ~1 chunk
- **WHEN** el use case procesa un bloque de 50 archivos con 1000 chunks totales
- **THEN** la memoria pico del bloque es ~1 chunk en texto (~500 bytes) + 1 embedding en float (~6 KB) = ~10 KB, no los 1000 chunks acumulados (~1 MB)

#### Scenario: Pipeline streaming con batch interno
- **WHEN** `embed_iter` recibe un iterador de 5000 chunks y `TITVO_EMBEDDING_BATCH_SIZE=1000`
- **THEN** el adapter hace 5 llamadas al SDK (cada una con 1000 chunks) y emite 5000 embeddings uno a uno a través del iterador retornado

#### Scenario: Pipeline CPU-bound y I/O-bound no se mezclan en memoria
- **WHEN** el splitting es lento (CPU) y el embedding es rápido (I/O)
- **THEN** solo 1 chunk viaja a la vez en el pipeline, sin cola intermedia que infle RAM

#### Scenario: Failure mid-stream no pierde chunks ya commiteados
- **WHEN** un chunk N falla en insert después de haber commiteado N-1 exitosamente
- **THEN** el run aborta y los N-1 chunks ya están en el DB + `indexed_files` para los archivos completos; el resume retoma desde el siguiente archivo

#### Scenario: ICodeSplitter.iter_chunks como iterator lazy
- **WHEN** se llama `iter_chunks(file)` sobre un archivo de 10k líneas
- **THEN** retorna un `Iterator[str]` que produce chunks on-demand al ser consumido, sin construir la lista completa upfront

### Requirement: Lock distribuido impide runs concurrentes sobre la misma rama
Antes de iniciar cualquier indexación (full o delta) para `(repository_url, branch)`, el sistema SHALL adquirir un lock en S3. **El lock se adquiere ANTES de cualquier llamada a `get_files()` o `embed()`** — un Job 2 que no pueda adquirirlo falla con `RuntimeError` sin gastar tokens de OpenAI. Si el lock ya está activo y no expiró, SHALL fallar con error descriptivo (no espera activa). El lock SHALL liberarse al terminar el run con éxito. El TTL SHALL ser de 360 minutos (6h) por defecto para exceder el peor caso de run real (~4h) con margen.

#### Scenario: Lock adquirido ANTES de iniciar embeddings
- **WHEN** `execute()` arranca con un lock adquirido
- **THEN** ningún embedding se ha enviado a OpenAI todavía; el primer `get_files()` y la primera llamada a `embed()` ocurren solo después de que el lock es nuestro

#### Scenario: Job 2 falla rápido sin embeber (camino normal)
- **WHEN** Job 2 intenta `acquire_lock` y Job 1 ya tiene el lock activo
- **THEN** Job 2 lanza `RuntimeError("Lock held by {owner} until {expires_at}")` y termina con código no-cero, sin haber llamado a `get_files()` ni a `embed()`. Costo OpenAI: $0

#### Scenario: Adquisición exitosa cuando no hay lock
- **WHEN** `execute()` arranca y no existe `locks/{branch}.json` en S3 para `(repository_url, branch)`
- **THEN** el sistema escribe el lock con `IfNoneMatch="*"` y registra `Lock acquired owner=... expires_at=...`

#### Scenario: Stale lock takeover
- **WHEN** existe un lock con `expires_at < now`
- **THEN** el sistema lo borra (best effort) y reintenta la adquisición; si la segunda adquisición falla porque otro job tomó el lock entre el delete y el reintento, trata como "lock activo"

#### Scenario: Lock perdido durante el run (job ya estaba embeberando)
- **WHEN** durante `_process_files` el `renew_lock` retorna `False` (otro job tomó el lock porque el nuestro expiró)
- **THEN** el sistema registra `ERROR Lock lost during renewal, aborting run` y termina el run con chunks parcialmente commiteados. Los chunks commiteados están en el DB checkpoint → el siguiente run retoma.

#### Scenario: Defensa en profundidad — check per-file antes de insertar
- **WHEN** `_process_files` está por procesar un archivo
- **THEN** consulta `vector_store.is_file_indexed(file.path)` antes de split/embed; si retorna `True`, registra `Skipping file already indexed: path=X` y continúa con el siguiente. Cubre el race corner-case donde Job 1 perdió el lock pero Job 2 ya commiteó ese archivo.

#### Scenario: Liberación del lock al éxito
- **WHEN** el run termina con éxito (full o delta) y el lock actual tiene `owner == current_owner`
- **THEN** el sistema elimina el lock de S3 y registra `Lock released`

#### Scenario: Lock no se libera si el job muere
- **WHEN** el proceso muere durante el run sin pasar por el finally
- **THEN** el lock queda con su `expires_at` y eventualmente expira, permitiendo que otro job tome el control después del TTL

### Requirement: Lock TTL con renovación automática
El lock SHALL tener un TTL inicial configurable (`TITVO_LOCK_TTL_MINUTES`, default 180). Si el run excede la mitad del TTL desde `acquired_at`, el sistema SHALL renovar el `expires_at` (best effort con `IfMatch`). Si la renovación falla, SHALL loguear WARNING pero no matar el job.

#### Scenario: Renovación exitosa a mitad del TTL
- **WHEN** han pasado más de `TITVO_LOCK_TTL_MINUTES / 2` desde `acquired_at`
- **THEN** el sistema actualiza el lock con un nuevo `expires_at = now + TITVO_LOCK_TTL_MINUTES` y registra `Lock renewed new_expires_at=...`

#### Scenario: Renovación falla por S3 transitorio
- **WHEN** el PUT de renovación retorna error de red o 5xx
- **THEN** el sistema registra `WARNING Lock renewal failed` y continúa el run con el TTL actual

#### Scenario: Renovación con IfMatch protege contra robo
- **WHEN** el lock original expiró y otro job lo adquirió antes de nuestra renovación
- **THEN** el PUT con `IfMatch="{etag_original}"` falla con 412 y el sistema registra `WARNING Lock lost during renewal, aborting run` y termina el run

### Requirement: Lock observable desde otros servicios (consulta externa)
El lock SHALL ser observable por otros servicios (notablemente el `src/agent`) sin necesidad de instanciar el `IndexRepositoryUseCase`. El método `IArtifactStorePort.get_lock(repository_url, branch)` ya provisto SHALL retornar un `LockInfo` parseado con `owner`, `aws_batch_job_id`, `acquired_at`, `expires_at`, `commit_sha` y `etag`. La S3 key SHALL seguir el patrón `{repo_host}/{owner}/{repo}/locks/{branch}.json`.

#### Scenario: El lock incluye el AWS Batch job ID para polling del agent
- **WHEN** el indexer adquiere el lock desde dentro de un AWS Batch container
- **THEN** el lock body incluye el campo `aws_batch_job_id` con el valor de `os.environ["AWS_BATCH_JOB_ID"]`. El agent puede leer este campo y usarlo para hacer polling con `batch.get_job_status(job_id)` sin necesidad de mantener un mapping paralelo.

#### Scenario: Agent A y Agent B ven la misma calidad de análisis
- **WHEN** dos análisis (A y B) del mismo `(repo, branch, commit)` se inician con 30s de diferencia
- **THEN** A gatilla el RAG job, B detecta el lock activo de A, B hace polling con `lock.aws_batch_job_id` y NO dispara un job propio. Cuando A termina, B continúa su análisis usando el MISMO RAG index que A. Ambos análisis tienen la misma calidad porque operan sobre el mismo DB final.

#### Scenario: El agente lee el lock antes de gatillar un nuevo job
- **WHEN** el `analyse_code_use_case` en `src/agent` está por gatillar un full RAG index para `(repo_url, branch)`
- **THEN** invoca `IRagIndexStatusPort.get_active_lock(repo_url, branch)` (futuro change en el agente) que internamente lee el lock file. Si retorna `LockInfo` con `expires_at > now`, el agente SHALL usar `lock.aws_batch_job_id` para hacer polling del job existente en lugar de gatillar uno nuevo.

#### Scenario: El agent polling hasta SUCCEEDED del job existente
- **WHEN** el agent detectó un lock activo y está esperando
- **THEN** llama `aws_batch.describe_jobs(jobs=[lock.aws_batch_job_id])` cada N segundos hasta que el status sea `SUCCEEDED` (continúa al análisis) o `FAILED` (lanza error).

#### Scenario: El agent espera el lock completo, no solo el commit
- **WHEN** el agent A dispara full RAG para `(repo, branch)` y el agent B detecta el lock activo
- **THEN** B SHALL esperar a que el job de A termine (incluyendo el upload final del DB a S3), no solo al "embedding done". Esto garantiza que cuando B hace `is_commit_indexed(...)` después, retorna `True` y el análisis de B usa el RAG completo.

#### Scenario: El agente dispara después de que el lock expiró
- **WHEN** el lock existe con `expires_at < now`
- **THEN** `get_active_lock` retorna `None` (lock considerado libre), y el agente procede con `trigger_full` normal.

#### Scenario: Lock vacío = no hay job corriendo
- **WHEN** no existe `locks/{branch}.json`
- **THEN** `get_active_lock` retorna `None` y el agente gatilla el job normalmente.

### Requirement: Artifact store expone métodos de lock
`IArtifactStorePort` SHALL declarar:
- `acquire_lock(repository_url, branch, owner, ttl_minutes, commit_sha) -> bool` — retorna `True` si adquirió, `False` si ya hay uno activo.
- `release_lock(repository_url, branch, owner) -> bool` — elimina el lock solo si `owner` coincide. Retorna `False` si no se liberó.
- `renew_lock(repository_url, branch, owner, etag, new_expires_at) -> bool` — PUT con `IfMatch="{etag}"`. Retorna `False` si el lock cambió de dueño.
- `get_lock(repository_url, branch) -> Optional[LockInfo]` — lee y parsea el lock actual; retorna `None` si no existe.

#### Scenario: acquire_lock con IfNoneMatch atómico
- **WHEN** `acquire_lock` se invoca y no existe el objeto lock
- **THEN** el PUT con `IfNoneMatch="*"` crea el objeto y retorna `True`

#### Scenario: acquire_lock cuando ya existe
- **WHEN** `acquire_lock` se invoca y el objeto lock existe
- **THEN** el PUT con `IfNoneMatch="*"` falla con 412 y retorna `False`

#### Scenario: release_lock con IfMatch
- **WHEN** `release_lock` se invoca con `owner == lock_owner_actual`
- **THEN** el DELETE procede y retorna `True`

#### Scenario: release_lock cuando el owner cambió
- **WHEN** `release_lock` se invoca con `owner != lock_owner_actual`
- **THEN** el DELETE falla con 412 y retorna `False` (no se elimina nada)

### Requirement: Configuración por variables de entorno
El binario SHALL leer dos variables nuevas sin fallar si no están:
- `TITVO_CHECKPOINT_EVERY_N_FILES` — entero; default `100`. Controla la frecuencia de flush.
- `TITVO_CHECKPOINT_KEY` — string con placeholders `{repo_host}`, `{owner}`, `{repo}`, `{branch}`, `{commit_sha}`; default `{repo_host}/{owner}/{repo}/branches/{branch}/checkpoints/{commit_sha}/index.db`.

#### Scenario: Variables no definidas (defaults)
- **WHEN** el binario arranca sin `TITVO_CHECKPOINT_EVERY_N_FILES` ni `TITVO_CHECKPOINT_KEY`
- **THEN** usa los defaults documentados y registra un log `INFO` con los valores efectivos

#### Scenario: Variables inválidas
- **WHEN** `TITVO_CHECKPOINT_EVERY_N_FILES` no es parseable como entero positivo
- **THEN** el binario falla con `ValueError` descriptivo antes de iniciar la indexación
