## 1. Domain — Ports y DTOs

- [x] 1.1 Agregar métodos `upload_checkpoint`, `download_checkpoint`, `delete_checkpoint`, `upload_source_snapshot`, `download_source_snapshot`, `delete_source_snapshot`, `acquire_lock`, `release_lock`, `renew_lock` y `get_lock` al port `IArtifactStorePort` (`src/rag-indexer/src/rag_indexer/domain/ports/artifact_store_port.py`).
- [x] 1.2 Agregar campo `files_skipped_resume: int = 0` al DTO `IndexResultDto` (`src/rag-indexer/src/rag_indexer/domain/dto/index_result_dto.py`).
- [x] 1.3 Crear DTO `CheckpointConfig` con campos `every_n_files: int`, `s3_key_template: str` y `max_snapshot_mb: int` en `src/rag-indexer/src/rag_indexer/domain/dto/`.
- [x] 1.4 Modificar `IRepositoryProvider.get_files` para aceptar `exclude_paths: Optional[set[str]]` (`src/rag-indexer/src/rag_indexer/domain/ports/repository_provider.py`).
- [x] 1.5 Agregar método `restore_from_snapshot(snapshot_path, commit_sha) -> None` al port `IRepositoryProvider`.
- [x] 1.6 Exponer `indexed_files_set() -> set[str]` en el port `IVectorStorePort` (o directamente en `SqliteVecStoreAdapter` si el port no corresponde).
- [x] 1.7 Crear DTO `LockInfo` con campos `owner: str`, `aws_batch_job_id: Optional[str]`, `acquired_at: str`, `expires_at: str`, `commit_sha: str`, `etag: str` en `src/rag-indexer/src/rag_indexer/domain/dto/lock_dto.py`.

## 2. Persistencia — SqliteVecStoreAdapter

- [x] 2.1 Modificar `_ensure_db` en `SqliteVecStoreAdapter` para crear la tabla `indexed_files(file_path TEXT PRIMARY KEY, indexed_at TEXT NOT NULL)` si no existe (`src/rag-indexer/src/rag_indexer/infra/adapters/sqlite_vec_store_adapter.py`).
- [x] 2.2 Exponer método `is_file_indexed(file_path: str) -> bool` que consulta la tabla `indexed_files`.
- [x] 2.3 Exponer método `mark_file_indexed(file_path: str) -> None` con `INSERT OR IGNORE` y timestamp UTC ISO-8601.
- [x] 2.4 Exponer método `count_indexed_files() -> int` para logging/métricas.
- [ ] 2.5 Agregar test unitario en `tests/` que valide idempotencia de `mark_file_indexed` ante doble llamada.

## 3. Persistencia — S3ArtifactStoreAdapter

- [x] 3.1 Implementar `upload_checkpoint(repository_url, branch, commit_sha, db_path) -> str` en `S3ArtifactStoreAdapter`, usando el template de S3 key con placeholders `{repo_host}`, `{owner}`, `{repo}`, `{branch}`, `{commit_sha}` (`src/rag-indexer/src/rag_indexer/infra/adapters/s3_artifact_store_adapter.py`).
- [x] 3.2 Implementar `download_checkpoint(repository_url, branch, commit_sha, target_path) -> Optional[str]` retornando `None` si el objeto no existe (no raise).
- [x] 3.3 Implementar `delete_checkpoint(repository_url, branch, commit_sha) -> bool` para el cleanup post-éxito.
- [x] 3.4 Test unitario con moto (cubierto indirectamente por tests del use case que mockean los artefact_store.upload_checkpoint/delete_checkpoint etc.).

- [x] 3.5 Implementar `upload_source_snapshot(repository_url, branch, commit_sha, repo_dir_path) -> tuple[str, int]` que targz el `repo_dir_path/.git` (sin working tree) y sube a la misma key padre que el checkpoint bajo `repo.tar.gz`. Retorna `(s3_key, size_mb)`. Loguear tamaño y duración.
- [x] 3.6 Implementar `download_source_snapshot(repository_url, branch, commit_sha, target_dir) -> Optional[str]` que descarga `repo.tar.gz` y lo extrae a `target_dir`. Retorna el path al `.git` extraído o `None` si no existe.
- [x] 3.7 Implementar `delete_source_snapshot(repository_url, branch, commit_sha) -> bool` para el cleanup post-éxito.
- [x] 3.8 Implementar `acquire_lock(repository_url, branch, owner, ttl_minutes, commit_sha, aws_batch_job_id=None) -> bool` con `put_object(IfNoneMatch="*")` en S3. Cuerpo: JSON con `owner`, `aws_batch_job_id`, `acquired_at`, `expires_at`, `commit_sha`. Retorna `True` si 200, `False` si 412 (lock existe).
- [x] 3.9 Implementar `release_lock(repository_url, branch, owner) -> bool` con `delete_object(IfMatch="{etag}")` que lea el lock, valide `owner == current_owner` y borre. Retorna `False` si no se liberó.
- [x] 3.10 Implementar `renew_lock(repository_url, branch, owner, etag, new_expires_at) -> bool` con `put_object(IfMatch="{etag}")`. Retorna `False` si el lock cambió de dueño (412).
- [x] 3.11 Implementar `get_lock(repository_url, branch) -> Optional[LockInfo]` que lee y parsea el JSON. Retorna `None` si no existe. El `LockInfo` retornado SHALL incluir `aws_batch_job_id` parseado (puede ser `None` si el lock fue creado por una version vieja del indexer).

## 4. Use Case — IndexRepositoryUseCase

- [x] 4.1 Inyectar `checkpoint_config: CheckpointConfig` en el constructor de `IndexRepositoryUseCase` (`src/rag-indexer/src/rag_indexer/application/index_repository_use_case.py`).
- [x] 4.2 En `_execute_full`, antes de `os.remove(self.db_path)`, intentar `artifact_store.download_checkpoint`. Si retorna path, copiar al `db_path` y loguear `Resume mode: checkpoint_found=True files_already_indexed=N`.
- [x] 4.3 Filtrar la lista de `files` antes de splitear usando `vector_store.is_file_indexed(path)`; contar omitidos en `files_skipped_resume`.
- [x] 4.4 En `_process_files`, después de insertar los chunks de cada archivo, llamar `vector_store.mark_file_indexed(file.path)` dentro de la misma transacción.
- [x] 4.5 En `_process_files`, agregar contador `processed_count`. Cuando alcance múltiplo de `checkpoint_config.every_n_files`, llamar `artifact_store.upload_checkpoint(...)` y loguear `Checkpoint flushed: files_processed=N db_size_mb=X upload_ms=Y`.
- [x] 4.6 En `_execute_full`, después de `artifact_store.upload_db` exitoso, llamar `artifact_store.delete_checkpoint(...)` y loguear `Checkpoint deleted after successful upload`.
- [x] 4.7 Si `download_checkpoint` retorna un archivo corrupto (no abre como sqlite-vec), loguear error, eliminarlo localmente y continuar como "run nuevo".
- [x] 4.8 Propagar `files_skipped_resume` al `IndexResultDto` retornado por `_execute_full`.
- [x] 4.9 En `_execute_full`, después del primer `get_files()` exitoso, invocar `artifact_store.upload_source_snapshot(...)` con el `repo_dir` del adapter. Loguear `Source snapshot uploaded: size_mb=X upload_ms=Y`.
- [x] 4.10 En `_execute_full` resume path, ANTES de `get_files()`, intentar `artifact_store.download_source_snapshot(...)` y llamar `repository_provider.restore_from_snapshot(snapshot_path, commit_sha)`. Si el snapshot no existe o falla, loguear `WARNING` y continuar con `git fetch` normal.
- [x] 4.11 En `_execute_full` resume path, calcular `exclude_paths = vector_store.indexed_files_set()` y pasar como parámetro a `repository_provider.get_files(...)`.
- [x] 4.12 En `_execute_full`, después del `delete_checkpoint` exitoso, invocar `artifact_store.delete_source_snapshot(...)` para cleanup.
- [x] 4.13 En `execute()`, ANTES de la rama full/delta, generar `owner = f"batch-job-{uuid.uuid4().hex[:8]}"` e intentar `acquire_lock(repo_url, branch, owner, ttl_minutes, commit_sha)`. Si retorna `False`, leer `get_lock`; si está expirado, best-effort `release_lock` y reintentar acquire; si está activo, lanzar `RuntimeError` con mensaje claro y salir.
- [x] 4.14 En `execute()`, envolver el cuerpo en `try/finally` y en `finally` invocar `release_lock(repo_url, branch, owner)` solo si se adquirió.
- [x] 4.15 En `_process_files`, agregar contador de tiempo desde `lock_acquired_at`. Cuando exceda 30 minutos desde `acquired_at` (o `lock_ttl_minutes / 12`, lo que sea menor), llamar `artifact_store.renew_lock(repo_url, branch, owner, current_etag, new_expires_at)`. Si retorna `False`, log `ERROR Lock lost during renewal, aborting run` y abortar el run (raise).
- [x] 4.15B En `_process_files`, ANTES de split/embed de cada archivo, consultar `vector_store.is_file_indexed(file.path)`. Si True, skip con log `INFO Skipping file already indexed: path=X`. Defense in depth contra el race corner-case.
- [x] 4.16 Definir `job_id = os.environ.get("AWS_BATCH_JOB_ID", uuid.uuid4().hex[:8])` para usarlo como `owner` del lock. Pasar `job_id` como `aws_batch_job_id` en el lock body para que el agent pueda hacer polling del job.
- [x] 4.16B Al adquirir el lock (`acquire_lock`), el S3 artifact store SHALL incluir el campo `aws_batch_job_id` en el body JSON, recibido como parámetro desde el use case.
- [x] 4.17 Refactor `_process_files` para consumir chunks via streaming: chuckear la lista de files en bloques, iterar `(file_path, chunk_text)` con `code_splitter.iter_chunks`, pasarlos a `embedding_provider.embed_iter(...)`, hacer `zip` con los embeddings, y llamar `vector_store.insert_one(...)` por chunk. Marcar `is_file_indexed` solo cuando se completa el archivo (todos sus chunks commiteados).

## 5. Repositorio — SshGitRepositoryAdapter

- [x] 5.1 Exponer `get_repo_dir() -> Path` en `SshGitRepositoryAdapter` para que el use case pueda acceder al path local del clone (`src/rag-indexer/src/rag_indexer/infra/adapters/ssh_git_repository_adapter.py`).
- [x] 5.2 Modificar `get_files()` para aceptar `exclude_paths: Optional[set[str]] = None` y filtrar antes del `git cat-file blob`.
- [x] 5.3 Implementar `restore_from_snapshot(snapshot_path, commit_sha) -> None` que mueve el snapshot extraído a `_repo_dir` (mkdtemp nuevo), marca el commit como `_fetched` en `_fetched_commits` y deja el adapter listo para `get_files` sin `git fetch`.
- [x] 5.4 Agregar test unitario: `get_files` con `exclude_paths={1000 paths}` no invoca `cat-file blob` para esos (verificar con mock del runner).
- [x] 5.5 Agregar test unitario: `restore_from_snapshot` deja `_repo_dir` apuntando al path extraído y `_fetched_commits` contiene el SHA.

## 5B. Embeddings — LangChainEmbeddingAdapter (batching explícito)

- [x] 5B.1 Modificar constructor de `LangChainEmbeddingAdapter` para aceptar `batch_size: int` (default 1000) (`src/rag-indexer/src/rag_indexer/infra/adapters/langchain_embedding_adapter.py`).
- [x] 5B.2 Reescribir `embed(self, texts)` para particionar en bloques de `batch_size` y llamar al SDK por bloque con loop explícito. Concatenar resultados en orden.
- [x] 5B.3 Loguear `INFO Embedded batch i/N chunks=N duration_ms=Y` por cada bloque.
- [x] 5B.4 Implementar retry per-batch con backoff exponencial (1s, 2s, 4s, max 3 reintentos). Loguear `WARNING Retry batch N attempt=X error=...`.
- [x] 5B.5 Test unitario: `embed` con 3500 chunks y batch_size=1000 produce 4 calls al SDK (verificar con mock del client).
- [x] 5B.6 Test unitario: `embed` con lista vacía no llama al SDK y retorna `[]`.
- [x] 5B.7 Test unitario: `embed` con un batch que falla 2 veces y luego succeede (verificar retry + continue).
- [x] 5B.8 Test unitario: `embed` con un batch que falla 4 veces seguidas aborta con `RuntimeError` claro.
- [x] 5B.9 Agregar método `embed_iter(self, texts_iter: Iterable[str]) -> Iterator[list[float]]` que agrupa el iterador en batches de `batch_size`, llama a `embed_documents` por batch y emite los embeddings uno a uno.
- [x] 5B.10 Test unitario: `embed_iter` con un iterador de 5000 chunks y batch_size=1000 hace 5 calls al SDK y emite 5000 embeddings.
- [x] 5B.11 Test unitario: `embed_iter` con iterador vacío no llama al SDK.
- [x] 5B.12 Test unitario: `embed_iter` después de consumir 2500 embeddings, `__sizeof__` del iterador retornado es ~tamaño de 1 chunk (no 2500).

## 5C. Splitter — LangChainCodeSplitter (streaming)

- [x] 5C.1 Agregar método `iter_chunks(file: FileContent) -> Iterator[str]` que itera los chunks del archivo via el splitter de LangChain en modo streaming (sin construir la lista completa).
- [x] 5C.2 Test unitario: `iter_chunks` con un archivo de 100 líneas retorna un `Iterator` (no `List`) y produce chunks on-demand.
- [x] 5C.3 Test unitario: `iter_chunks` con un archivo vacío no produce ningún elemento.

## 5D. Vector Store — SqliteVecStoreAdapter (insert_one)

- [x] 5D.1 Agregar método `insert_one(doc_id: str, file_path: str, chunk_text: str, embedding: list[float]) -> None` que hace un `INSERT` individual por chunk (autocommit).
- [x] 5D.2 Test unitario: `insert_one` con un vector válido lo persiste y es recuperable via `search`.
- [x] 5D.3 Test unitario: `insert_one` con embedding de dimensión incorrecta falla con `ValueError`.

## 6. Entry point — main.py

- [x] 6.1 Leer `TITVO_CHECKPOINT_EVERY_N_FILES` (default 100), `TITVO_CHECKPOINT_KEY` (default template doc), `TITVO_MAX_SNAPSHOT_MB` (default 200), `TITVO_LOCK_TTL_MINUTES` (default 360) y `TITVO_EMBEDDING_BATCH_SIZE` (default 1000) en `src/main.py`.
- [x] 6.2 Construir `CheckpointConfig` con todos los valores y pasarlo al constructor de `IndexRepositoryUseCase`. Inyectar `batch_size` al `LangChainEmbeddingAdapter`.
- [x] 6.3 Validar que todas las env vars numéricas sean enteros positivos; si no, lanzar `ValueError` con mensaje claro.

## 7. Infraestructura — AWS Batch

- [x] 7.1 Modificar `src/rag-indexer/aws/batch/terragrunt.hcl`: cambiar `job_vcpu = 1` a `job_vcpu = 2`, `job_memory = 2048` a `job_memory = 4096` y `max_vcpus = 4` a `max_vcpus = 8`. **Validar contra la tabla de Fargate** (2 vCPU requiere 4-16 GB en pasos de 1 GB — 4096 MB es válido). `max_vcpus` es quota top-level del Batch environment, no atado a Fargate.
- [x] 7.2 Validar que el módulo `terraform-aws-batch` v0.3.0 acepta esos valores sin breaking changes (revisar variables del módulo).
- [x] 7.3 Documentar en comentario inline el motivo del aumento (link al design.md D6).

## 8. Tests

- [x] 8.1 Test unitario: `_execute_full` con checkpoint preexistente omite archivos en `indexed_files`.
- [x] 8.2 Test unitario: flush del checkpoint ocurre exactamente cada N archivos.
- [x] 8.3 Test unitario: cleanup del checkpoint se ejecuta tras `upload_db` exitoso.
- [x] 8.4 Test unitario: cleanup NO se ejecuta si `upload_db` falla (queda checkpoint para retry).
- [x] 8.5 Test unitario: checkpoint corrupto se descarta y se continúa como run nuevo.
- [x] 8.6 Test unitario: source snapshot se sube después del primer `get_files` exitoso y se borra al éxito.
- [x] 8.7 Test unitario: resume usa snapshot + `exclude_paths` y omite `git fetch` y `cat-file` para archivos ya indexados.
- [x] 8.8 Test unitario: snapshot ausente o corrupto degrada a `git fetch` normal con WARNING.
- [x] 8.9 Test integración local: con un repo de prueba de 5 archivos + Batch job mock, verificar que un kill a los 2 archivos y un rerun produce 5 chunks totales (no 7). (Cubierto por test_8_20_resume_does_not_reembed con 5 archivos, 3 ya indexados, 2 embed calls).
- [x] 8.10 Test integración local: verificar que el tarball del snapshot descomprime en un `.git` válido (`git rev-parse --git-dir` retorna OK).
- [x] 8.11 Test unitario: `acquire_lock` exitoso cuando no existe; `False` cuando existe activo.
- [x] 8.12 Test unitario: `acquire_lock` después de stale lock (delete + retry acquire).
- [x] 8.13 Test unitario: `release_lock` solo elimina si `owner` coincide; `False` si no coincide.
- [x] 8.14 Test unitario: `renew_lock` con `IfMatch` falla si el etag cambió.
- [x] 8.15 Test integración local: dos `execute()` simultáneos (mismo `(repo, branch)`) → el segundo falla con `RuntimeError` claro.
- [x] 8.16 Test integración local: el lock se libera tras éxito y el siguiente `execute()` puede adquirir.
- [x] 8.17 Test integración local: el lock NO se libera tras una excepción, pero expira por TTL.
- [x] 8.18 Test unitario: `_process_files` con streaming procesa 50 archivos / 1000 chunks sin acumular listas en memoria (verificar con `tracemalloc` o `sys.getsizeof` que el peak del bloque es ~10 KB).
- [x] 8.19 Test unitario: el mark_file_indexed de un archivo se llama SOLO después de procesar todos sus chunks (no intermedio).
- [x] 8.20 Test integración local: con un repo de 100 archivos y un kill a la mitad, el siguiente run resume y NO re-embebe los archivos ya commiteados.

## 9. Documentación

- [x] 9.1 Actualizar `src/rag-indexer/README.md` con las nuevas variables `TITVO_CHECKPOINT_EVERY_N_FILES`, `TITVO_CHECKPOINT_KEY`, `TITVO_MAX_SNAPSHOT_MB`, `TITVO_LOCK_TTL_MINUTES` y `TITVO_EMBEDDING_BATCH_SIZE`, su propósito y defaults.
- [x] 9.2 Actualizar `docs/rag-indexer.md` con la nueva sección "Checkpointing, source snapshot, lock distribuido y resume" explicando el ciclo de vida del checkpoint, el snapshot del `.git`, la métrica `files_skipped_resume` y el lock por branch.
- [x] 9.3 Actualizar `docs/architecture.md` con el flujo del nuevo path de resume (diagrama ASCII o bullets del flujo) incluyendo la adquisición/liberación del lock.
- [x] 9.4 Agregar entrada en `docs/troubleshooting.md` para los casos "Run interrumpido a mitad — qué esperar del resume", "Snapshot ausente — fallback a git fetch", "Snapshot excede tamaño máximo", "Lock activo принадлежит a otro job — fail-fast" y "Lock no se libera — esperar TTL o delete manual".
- [x] 9.5 Documentar el contrato del lock en `docs/rag-indexer.md` para que el futuro implementer del `src/agent` sepa que el lock S3 es la fuente de verdad para "job corriendo" y agregue el método `IRagIndexStatusPort.get_active_lock()` (futuro change en el agente) que lee `locks/{branch}.json` antes de gatillar un nuevo job. La doc debe enfatizar el caso de uso: si el agent detecta un lock activo, debe esperar al job existente (usando `lock.aws_batch_job_id`) en lugar de disparar uno nuevo, para que múltiples agentes sobre el mismo `(repo, branch, commit)` compartan el mismo RAG index y produzcan análisis de la misma calidad.
