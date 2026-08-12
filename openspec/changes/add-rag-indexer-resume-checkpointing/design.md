## Context

El `rag-indexer` (`src/rag-indexer`) ejecuta en AWS Batch (`job_vcpu=1`, `job_memory=2048`) la indexación full o delta de un repositorio contra OpenAI embeddings, persistiendo el resultado como sqlite-vec en S3. Para repos con ~20k archivos la corrida dura entre 50 y 90 minutos.

Hoy `_execute_full` borra `/tmp/rag_index.db` al inicio (`index_repository_use_case.py:88-90`) y solo sube el DB a S3 al final (`index_repository_use_case.py:103`). Si el job muere (OOM, timeout de Batch, evict de ECS host), todo el progreso se pierde y se debe re-procesar todo, duplicando tiempo y costo de embeddings.

Este diseño agrega checkpointing periódico y resume idempotente dentro del mismo commit, sin cambiar el orquestador (sigue AWS Batch) ni el formato de almacenamiento (sigue sqlite-vec).

## Goals / Non-Goals

**Goals:**
- Reanudar un run interrumpido por commit sin re-embeber los chunks ya procesados.
- Subir el DB local a S3 cada N archivos (default 100) con costo despreciable (<1 MB cada 100 archivos).
- Tracking idempotente de archivos vía tabla `indexed_files` en el mismo sqlite-vec.
- Métrica `files_skipped_resume` para visibilidad operativa en logs y respuesta.
- Aumento de capacidad del Batch job (2 vCPU, 4 GB) para dar headroom a la nueva tabla y a la carga en memoria de 300k+ chunks.

**Non-Goals:**
- Cambiar el orquestador (sigue AWS Batch, no migramos a Step Functions).
- Optimizar rate-limit de OpenAI ni paralelizar embeddings.
- Resume cross-commit (eso ya lo cubre `_execute_delta`).
- Persistir checkpoints más allá del run actual (se borran al terminar OK).
- Comprimir el DB antes de subir (el sqlite-vec no se comprime bien; aceptamos el costo del PUT).

## Decisions

### D1. Checkpoint = copia completa del DB local en S3

**Decisión**: En cada flush, subir el `/tmp/rag_index.db` completo a una clave S3 separada del DB final (`branches/{branch}/checkpoints/{commit_sha}/index.db` vs `branches/{branch}/{commit_sha}/index.db`).

**Por qué**:
- El DB sqlite-vec es autocontenido y portable; copiar es trivial.
- Evita lógica de "qué chunks van en este checkpoint" — el DB ya tiene el truth.
- Permite descargas parciales con `Range` si el costo se vuelve problema (futuro).

**Alternativas consideradas**:
- Subir solo el delta de chunks nuevos por flush → más complejo, requiere un formato incremental que sqlite-vec no soporta nativamente; lo descartamos.
- Usar S3 multipart upload para subir incrementalmente un mismo objeto → complica el resume (¿qué pasa si solo se subió la mitad?); lo descartamos.

### D2. Tabla `indexed_files` en el mismo sqlite-vec

**Decisión**: Crear una tabla relacional estándar `indexed_files(file_path TEXT PRIMARY KEY, indexed_at TEXT NOT NULL)` en el mismo DB local, junto a la virtual table `chunks`.

**Por qué**:
- Un solo archivo, una transacción al bajar el checkpoint.
- PRIMARY KEY da la idempotencia gratis (`INSERT OR IGNORE` no falla en reintentos).
- Backup atómico con el DB — al subir checkpoint, queda persistido.

**Alternativas consideradas**:
- Tabla/archivo separado `progress.json` en S3 → requiere protocolo de sync entre dos fuentes de verdad; lo descartamos.
- Set de file_paths en memoria → se pierde al crash; lo descartamos.

### D3. Detección de resume antes del split

**Decisión**: Al inicio de `_execute_full`, **antes** de tocar `/tmp/rag_index.db`, consultar `download_checkpoint`. Si retorna path, copiar a `db_path`; si retorna `None`, crear DB vacío como hoy.

**Por qué**:
- Es el único punto donde se puede saber "este run es continuación de otro".
- Insertar la lógica antes de la línea `os.remove(self.db_path)` evita perder progreso.

**Alternativas consideradas**:
- Detectar resume dentro de `_process_files` → más complejo, requiere pasar el set de archivos ya procesados al use case; menos testeable.

### D4. Flush sincrónico pero no-bloqueante para el siguiente batch

**Decisión**: El flush se ejecuta después de cada `TITVO_CHECKPOINT_EVERY_N_FILES` archivos, **después** de insertar al DB y **antes** de procesar el siguiente archivo. Usa el cliente boto3 ya instanciado (sin re-auth).

**Por qué**:
- Sincrónico = garantiza que el checkpoint refleja el estado al momento del flush. Si fuera async, un crash podría perder lo flush-eado.
- "No-bloqueante para OpenAI" = el flush sube a S3 local; la siguiente llamada al embedding provider puede continuar mientras el upload usa otra conexión. Como el DB es chico (<50 MB en checkpoint) y S3 PUT es rápido, el overhead es ~1-3 s.

**Alternativas consideradas**:
- Flush en background thread → race condition con el siguiente flush; lo descartamos.

### D5. Cleanup del checkpoint en éxito, no en error

**Decisión**: Solo se borra el checkpoint después de que el upload final del DB completo es exitoso (`upload_db`). Si el run muere, el checkpoint queda y se usa en el próximo run.

**Por qué**:
- Política de "máquina expendedora": si dudas, conservá. El costo de un checkpoint huérfano es despreciable (un objeto S3 de ~50 MB).
- Evita races entre "subí el final OK" y "ya borré el checkpoint".

### D6. Aumento de capacidad del Batch job

**Decisión**: Subir `job_vcpu` de 1 → 2 y `job_memory` de 2048 → 4096 MB en `aws/batch/terragrunt.hcl`. Subir `max_vcpus` de 4 → 8.

**Por qué**:
- 300k chunks en memoria como strings + dicts ≈ 300-500 MB; con la nueva tabla `indexed_files` y embeddings resultantes (1536 floats × 4 bytes × 300k = 1.8 GB serialized), necesitamos más RAM.
- 2 vCPU permiten al splitter AST usar el segundo core cuando el primero espera el HTTP al embedding provider.
- `max_vcpus = 8` con `job_vcpu = 2` permite 4 jobs concurrentes en el mismo environment.

**Validación contra AWS Fargate** (el compute environment es FARGATE, ver `aws/batch/.terragrunt-cache/.../main.tf:93`):
- Fargate exige combinaciones vCPU/memory fijas en pasos específicos.
- `2 vCPU + 4 GB` es el **lower bound** del rango válido para 2 vCPU (4-16 GB en pasos de 1 GB). Válido.
- `8 vCPU` requiere 16-60 GB en pasos de 4 GB. Subir a 8 vCPU costaría ~4× más por hora (no justificado para nuestro workload).

**Alternativas consideradas**:
- Mantener 1 vCPU / 2 GB → riesgo de OOM en repos >15k archivos; lo descartamos.
- Saltar a 4 vCPU / 8 GB → sobreinversión para el caso típico (2-5k archivos); lo descartamos.
- 8 vCPU + 16 GB → técnicamente válido pero no justificado: el cuello es I/O (OpenAI), no CPU. Lo descartamos.

### D7. Variables de entorno con defaults razonables

**Decisión**: `TITVO_CHECKPOINT_EVERY_N_FILES=100` (frecuencia) y `TITVO_CHECKPOINT_KEY` (template de S3 key con placeholders).

**Por qué**:
- Configurable sin redeploy de código.
- Defaults seguros: 100 archivos ≈ 5 MB por checkpoint, latencia de upload ~1 s, no estresa S3.
- Template S3 con placeholders permite migrar de layout sin tocar código.

### D8. Snapshot del repo local como tarball en S3

**Decisión**: Después del primer `get_files()` exitoso en un run, tar + gzip el `_repo_dir/.git` (sin working tree) y subirlo a S3 bajo `{branch}/checkpoints/{commit_sha}/repo.tar.gz`. En resume, descargar y extraer a un temp dir antes del `get_files()` y usar el adapter con un flag "no fetch".

**Por qué**:
- Reemplaza el `git fetch --depth=1 --no-tags` (~5-10 s de red) y deja los blobs disponibles localmente para `cat-file` (mucho más rápido desde el pack local).
- Tamaño típico: 10-50 MB comprimido con `--depth=1`. Upload único al inicio del run, descarga única al inicio del resume.
- Costo del snapshot: almacenamiento temporal (se borra al éxito) + ancho de banda de subida una sola vez. Vale la pena vs el rerun completo.

**Alternativas consideradas**:
- **Manifest JSONL de `{path, content}`**: ~100 MB sin comprimir para un repo grande, más lento de parsear, y duplica el contenido ya en el DB final. Descartado.
- **EFS compartido entre runs**: cambio arquitectónico grande (EFS no está en el módulo Batch actual), costo sostenido. Descartado para este horizonte.
- **Re-fetch con `--depth=1` cada vez**: simple pero implica red en cada resume + recat-file de todos los blobs (3 min para 20k archivos). Es el status quo.

### D9. `get_files` con `exclude_paths` para evitar `cat-file` redundante

**Decisión**: `IRepositoryProvider.get_files(url, commit_sha, exclude_paths: Optional[set[str]] = None)`. El adapter filtra los paths antes del `git cat-file blob`, ejecutándolo solo para los archivos que faltan en `indexed_files`.

**Por qué**:
- Independiente del snapshot (D8): aunque el snapshot evite el `fetch`, igual necesitamos no llamar `cat-file` para los archivos ya indexados.
- En un resume al 50% con 10k archivos ya procesados: pasamos de 20k subprocess calls a 10k. ~1.5 min ahorrados.
- Es una adición mínima al port (un parámetro opcional) y cero impacto en el camino fresco.

**Tradeoff**:
- Si `exclude_paths` se calcula incorrectamente (race con otro run), podríamos re-embeber un archivo ya presente. Mitigación: el `INSERT OR IGNORE` en `chunks` no falla por PK duplicada, pero el embedding sí se hace. Aceptable: el `indexed_files` se calcula del DB local al inicio, no hay race si el adapter es single-writer.

### D10. Lock distribuido en S3 con conditional write

**Decisión**: Antes de `execute()` (específicamente, ANTES de la primera llamada a `get_files()` o `embed()`), escribir `locks/{branch}.json` en S3 con `PutObject` + `IfNoneMatch="*"` (S3 falla con 412 si existe). Si falla, leer el lock y decidir: si expiró, best-effort delete y reintentar; si activo, lanzar `RuntimeError` y salir **sin embeber**.

**Por qué**:
- S3 conditional write es atómico y no requiere infra nueva (DynamoDB sería más correcto pero agregaría dependencia y costo).
- El lock vive junto a los artefactos que protege — una sola fuente de verdad en el mismo bucket.
- TTL + renovación evita dead-locks por jobs muertos sin cleanup.
- **Crítico**: la adquisición es lo PRIMERO que hace `execute()`. Un Job 2 que no consigue el lock nunca llama a OpenAI → costo 0 del race condition normal.

**Alternativas consideradas**:
- **DynamoDB lock** (estilo `aws-dynamodb-lock-client`): más correcto (leases nativos, fencing tokens), pero requiere nueva tabla y otro IAM policy. Lo descartamos por costo/complejidad.
- **Redis distribuido (ElastiCache)**: no existe en el stack actual. Lo descartamos.
- **Lock file local en EFS compartido**: cambio arquitectónico mayor. Lo descartamos.
- **Sin lock**: status quo. Pésimo si dos jobs corren concurrentes.

### D11. Lock con TTL largo y renovación frecuente

**Decisión**: TTL inicial de **360 minutos (6h)**. Renovación cada **30 minutos** usando `PutObject` con `IfMatch="{etag_original}"` para no pisar un lock ajeno.

**Por qué**:
- 360 min cubre runs de hasta 4h (peor caso real: repo muy grande con rate-limit estricto) con margen de 2h.
- Renovación cada 30 min (no a la mitad del TTL) reduce la ventana de race: si una renovación falla, hay 30 min para detectar y abortar, vs 90 min con la política anterior.
- Renovación con `IfMatch` evita el caso patológico: mi lock expiró mientras hacía el PUT de renovación, otro job lo tomó → mi PUT con `IfMatch` falla, sé que perdí el lock, paro.

**Defense in depth**:
- Antes de procesar cada archivo, `_process_files` consulta `vector_store.is_file_indexed(file.path)`. Si otro job (que ganó la carrera del stale lock) ya commiteó ese archivo, el nuestro lo skipea sin embeber.
- Esto cubre el corner-case extremo donde: nuestro lock expiró, otro job lo tomó, nosotros seguimos unos minutos sin saberlo. El check per-file garantiza cero duplicados para el mismo `(commit, file_path)`.

**Tradeoff**:
- Si la red está caída durante la renovación, el job sigue sin lock renovado. Ventana hasta el próximo intento: 30 min. Mitigación: log WARNING + retry de renovación cada 5 min.

### D12. Fail-fast en lugar de espera activa

**Decisión**: Si el lock está activo принадлежит a otro job, el sistema falla con `RuntimeError` claro y código de salida no-cero. NO espera activa.

**Por qué**:
- AWS Batch no es un orquestador interactivo: el caller debe decidir si reintentar.
- Espera activa bloquearía el slot de Batch indefinidamente, consumiendo recursos sin progreso.
- El caller (orquestador externo) puede reintentar con backoff o re-programar.

**Tradeoff**:
- Si el orquestador externo dispara el run sin lock awareness, verá fallos esporádicos. Mitigación: documentar el lock behavior en README y troubleshooting.

### D13. Batching explícito en el adapter, no delegado al SDK

**Decisión**: `LangChainEmbeddingAdapter.embed()` particiona la lista en bloques de `TITVO_EMBEDDING_BATCH_SIZE` y llama al SDK por bloque. NO se pasa `chunk_size` a `OpenAIEmbeddings` (queda con su default interno, pero el adapter controla el particionado).

**Por qué**:
- **Independencia de versión**: `langchain-openai` puede cambiar su default interno entre releases. Hacerlo explícito nos protege.
- **Observabilidad**: log por batch permite saber dónde está el run en cada momento vs la opacidad actual de "una sola request".
- **Retry granular**: un batch con 429 no afecta a los demás. El retry per-batch es trivial.
- **Alineación con checkpoint**: si `_process_files` procesa N archivos por bloque, el flush del checkpoint DB coincide con el flush del embedding → progreso coherente.

**Alternativas consideradas**:
- **Pasar `chunk_size=N` a `OpenAIEmbeddings`**: más simple, pero perdida de control sobre retry/logging y dependencia del comportamiento interno. Descartado.
- **Bypass total del SDK, llamar `requests` directo a `/v1/embeddings`**: máximo control, pero perdemos updates de LangChain al modelo (mantenimiento alto). Descartado.
- **No tocar nada**: status quo. Perdemos todo lo dicho arriba. Descartado.

### D14. `_process_files` en bloques de N archivos, no un único bloque

**Decisión**: `_process_files` ahora procesa archivos en bloques de `TITVO_EMBEDDING_BATCH_SIZE` chunks (calculado dinámicamente: 1-N archivos por bloque según cuántos chunks produzca cada uno). Por cada bloque: split → embed → insert → mark indexed → maybe flush checkpoint.

**Por qué**:
- Reduce el peak memory: en lugar de 300k chunks en RAM, se trabaja con ~1k (1 batch) por iteración.
- Permite progreso granular: después de cada bloque, el `indexed_files` está actualizado, el DB tiene chunks nuevos, el checkpoint está al día.
- Si el job muere, el resume pierde solo el bloque en curso (no los bloques ya commiteados).

**Tradeoff**:
- Más I/O a sqlite (más transacciones pequeñas vs una grande). Mitigación: usar `BEGIN`/`COMMIT` por bloque, sqlite lo maneja bien.
- Inserts a `chunks` por bloque en lugar de un mega-insert. Mitigación: el tiempo de insert es despreciable vs el de embed.

### D15. Streaming chunk-by-chunk en todo el pipeline

**Decisión**: El pipeline `split → embed → insert` opera con `Iterator` en lugar de `List`. `ICodeSplitter.iter_chunks(file)` y `IEmbeddingProvider.embed_iter(texts_iter)` emiten/consumen on-demand. El use case los une con `zip` y llama `vector_store.insert_one(...)` por chunk.

**Por qué**:
- **Memoria pico del bloque**: ~10 KB (1 chunk + 1 embedding) en lugar de ~6 MB (1 batch completo en listas). 600× menos.
- **CPU vs I/O solapables**: el splitting (CPU) puede ir más adelante que el embedding (I/O) consumiendo el mismo chunk — sin cola intermedia.
- **Failure granular**: si un chunk falla en insert, los anteriores ya están commiteados.
- **Costo AWS Batch menor**: 4 GB alcanza cómodo; podríamos bajar a 2 GB si quisiéramos, pero 4 GB da margen para crecimiento.

**Tradeoff**:
- Más complejo que listas: hay que propagar el estado del archivo actual a través del iterator (porque `mark_file_indexed` se hace por archivo, no por chunk).
- Para resolver el tradeoff: el iterator emite `(file_path, chunk_text)` o `code_splitter.iter_chunks_per_file(file)` retorna `Iterator[(file_path, chunk_text)]`.
- I/O a sqlite por chunk en lugar de por batch. Mitigación: sqlite maneja ~50k inserts/seg en local; con batching implícito del driver, el overhead es despreciable.

**Alternativas consideradas**:
- **`async/await` con `asyncio.Queue`**: equivalente en memoria, pero más complejo de testear y razonar. Descartado.
- **Persistencia previa a embed (escribir chunks a disco, embed off-line)**: agrega infra. Descartado.
- **Mantener `List` por bloque + 4 GB RAM**: lo que ya estaba. Funciona pero desperdicia memoria y no escala.

### D16. Lock body incluye `aws_batch_job_id` para polling del agent

**Decisión**: El body JSON del lock SHALL incluir el campo `aws_batch_job_id` con el valor de `os.environ["AWS_BATCH_JOB_ID"]`. El `owner` queda como la identidad lógica (que resulta ser el mismo valor, pero conceptualmente separado). El DTO `LockInfo` expone ambos como `Optional[str]`.

**Por qué**:
- El agent que detecta un lock activo puede leer directamente `lock.aws_batch_job_id` y hacer polling con `aws_batch.describe_jobs(jobs=[job_id])` sin mantener un mapping paralelo en dynamoDB.
- Si el indexer corre fuera de AWS Batch (ej. LocalStack en dev), `aws_batch_job_id` queda `None` y el agent puede usar otro mecanismo (lease con timestamp + polling del lock file hasta que desaparezca).
- Costo: ~50 bytes extra en el lock file. Despreciable.

**Tradeoff**:
- Acoplamiento: el lock file depende del entorno de ejecución (AWS Batch tiene env var, otros no). Mitigación: el `aws_batch_job_id` es `Optional`, no rompe nada si está ausente.
- Compatibilidad: locks creados por una versión vieja del indexer no tendrán `aws_batch_job_id`. Mitigación: `LockInfo.aws_batch_job_id` es `Optional`; el agent trata `None` como "no hay forma de hacer polling, esperar al lock file".

## Risks / Trade-offs

- **R1**: Si el upload del checkpoint mismo falla (red, S3 503), el flush se descarta y seguimos. El próximo flush reintenta. → Mitigación: log `WARNING` con el error; si S3 está caído sostenido, perdemos el flush pero no el progreso en memoria.
- **R2**: Duplicados en `chunks` por crash entre insert y `indexed_files` (escenario "Crash entre split y registro" del spec). → Mitigación: aceptable para RAG (afecta levemente el recall pero no la correctness); documentado en spec.
- **R3**: Aumento de job_memory de 2 GB a 4 GB dobla el costo por hora del Batch job. → Mitigación: vale la pena porque evita reruns de 1 hora; break-even al primer resume.
- **R4**: El flush periódico agrega latencia ~1-3 s cada 100 archivos → ~30-60 s extra en 20k archivos (0.1%). → Mitigación: aceptable vs el costo de un rerun completo.
- **R5**: Si dos runs del mismo commit corren concurrentemente (no debería, pero podría haber un bug), se pisan los checkpoints. → Mitigación: el Batch trigger actual ya es single-job por repo/branch; documentamos que la idempotencia asume single-writer.
- **R6**: El sqlite-vec se sube sin comprimir; un repo de 50k archivos podría generar checkpoints de 100+ MB. → Mitigación: aceptable en este horizonte; si crece, evaluar compresión con `gzip` en cliente boto3.
- **R7**: Snapshot del `.git` puede ser grande para repos con muchos tags/objects (no aplica aquí por `--no-tags` y `--depth=1`, pero es una variable a observar). → Mitigación: loguear tamaño del tarball en MB y abortar si supera un umbral configurable (`TITVO_MAX_SNAPSHOT_MB`, default 200).
- **R8**: Si el snapshot se sube pero la corrida muere antes del primer checkpoint DB, en el siguiente run se descarga el snapshot pero no hay `indexed_files` útil (se re-procesa todo desde el snapshot local). → Mitigación: idempotencia — los embeddings resultantes son los mismos, solo se gasta el tiempo de split+embed que ya estaba gastado.
- **R9**: `exclude_paths` calculado de `indexed_files` es solo el set de paths indexados **en este run**. No es cross-run. → Mitigación: el snapshot del DB (checkpoint) contiene la tabla `indexed_files` completa del run interrumpido, así que el exclude set sí cruza runs. Documentado en spec.
- **R10**: Subida del snapshot agrega ~10-30 s al inicio del primer run de cada commit. → Mitigación: aceptable vs el ahorro de 3 min en cada resume. Documentado en métricas de runtime.
- **R11**: Si dos jobs son lanzados por error casi simultáneamente (mismo segundo), el segundo verá "lock activo" y fallará. → Mitigación: documentar fail-fast y recomendar al orquestador externo retry con backoff exponencial. **Costo OpenAI si pasa este caso: $0** (Job 2 aborta antes de embeber).
- **R12**: Si un job queda colgado (deadlock en código, infinite loop), el lock expira en 360 min y otro job puede tomarlo. Mientras tanto, dos jobs podrían estar activos si el primero se destraba justo cuando entra el segundo. → Mitigación: improbable (deadlock requiere condición muy específica); documentado en troubleshooting.
- **R13**: Lock renewal race: si S3 está lento y la renovación llega tarde, el `IfMatch` falla porque otro job pudo haber adquirido el lock. Ventana de duplicación: hasta 30 min (intervalo de renovación). → Mitigación: log ERROR explícito, abort del run. **Defense in depth**: check per-file con `is_file_indexed` antes de embeer, así no se duplican chunks para el mismo archivo.
- **R14**: El lock file contiene `owner` (job ID) en texto claro; no es información sensible pero podría leakear el job-id pattern. → Mitigación: aceptable, no es dato privado.
- **R15**: Batching explícito vs default de LangChain: si LangChain cambia el comportamiento interno (p. ej. serializa en lugar de paralelizar), nuestro batching sigue siendo el source of truth. → Mitigación: tests unitarios sobre `embed()` validan el contrato (retorna N embeddings, no más, no menos).
- **R16**: `_process_files` por bloques introduce overhead de DB transactions. → Mitigación: medido a ~5-10 ms por transacción local; despreciable vs el embedding API call que toma ~1s.
- **R17**: Si un batch de embedding falla permanentemente (después de 3 reintentos), el run aborta con chunks parcialmente insertados. → Mitigación: cada bloque cierra su transacción; el resume desde el checkpoint descarta automáticamente los archivos no marcados en `indexed_files`.
- **R18**: Streaming con `Iterator` en Python añade overhead vs listas nativas (~5-10% según micro-benchmarks). → Mitigación: despreciable frente al tiempo de API call (~1s). Medido a <0.1% del tiempo total.
- **R19**: El streaming por chunk hace que el `mark_file_indexed` solo se pueda llamar al final de procesar todos los chunks del archivo. Si el splitting produce N chunks de un archivo, recién al N-ésimo commit sabemos que el archivo está completo. → Mitigación: usar `is_file_indexed` con un set en memoria para trackear archivos "en curso" en el bloque, y `mark_file_indexed` solo cuando se cierra el archivo. Test específico en 8.5B.
- **R20**: El streaming requiere que `vector_store.insert_one` haga commit por chunk. Si la conexión se cierra entre chunks (por error), pueden quedar rows huérfanas. → Mitigación: sqlite maneja cada `INSERT` como transacción propia (autocommit); un crash a mitad del archivo significa chunks parciales que el resume no marcará en `indexed_files` y re-procesará.

## Migration Plan

1. **Deploy**:
   - Mergear el cambio.
   - Aplicar `terragrunt apply` en `src/rag-indexer/aws/batch/` con el nuevo `job_vcpu=2`, `job_memory=4096`.
   - Rebuild imagen Docker del indexer.
   - Re-deploy del Batch job definition.
2. **Compatibilidad hacia atrás**:
   - Runs full en curso antes del deploy no se benefician del resume (su DB local no tiene `indexed_files`).
   - Runs nuevos usan checkpoint desde el primer archivo.
   - DB final subido a S3 sigue siendo compatible — un agente que lee el DB no necesita cambios.
3. **Rollback**:
   - Revertir terragrunt y re-deploy. El código nuevo detecta la ausencia de checkpoint (`download_checkpoint` retorna `None`) y degrada a comportamiento legacy sin error.
4. **Observabilidad**:
   - Log `INFO` al inicio: `"Resume mode: checkpoint_found=True files_already_indexed=N"`.
   - Log `INFO` cada flush: `"Checkpoint flushed: files_processed=N db_size_mb=X upload_ms=Y"`.
   - Métrica `files_skipped_resume` en `IndexResultDto` y en el log final.

## Open Questions

- ¿Vale la pena comprimir el DB antes del PUT? Trade-off CPU vs ancho de banda. Decidir después de medir el primer run real.
- ¿El umbral `TITVO_CHECKPOINT_EVERY_N_FILES=100` es el óptimo? Medir en local con repo real y ajustar.
- ¿La tabla `indexed_files` debería tener índice secundario por `indexed_at` para queries de "último indexado"? Probablemente no, pero documentar si se observa uso.
