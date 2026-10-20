## Why

El `rag-indexer` no permite reanudar un run interrumpido: borra el DB local al inicio (`index_repository_use_case.py:88-90`) y solo sube el DB a S3 al final (`index_repository_use_case.py:103`). Para repos con ~20k archivos donde la indexación tarda entre 50 y 90 minutos, cualquier falla de AWS Batch (OOM, timeout, evict) obliga a re-procesar desde cero, duplicando tiempo y costo de embeddings.

## What Changes

- Checkpointing periódico en `IndexRepositoryUseCase._execute_full`: persiste el DB local a S3 cada N archivos procesados (default N=100).
- Nuevos métodos en `IArtifactStorePort` para subir y descargar checkpoints por `(repository_url, branch, commit_sha)`.
- Detección automática al inicio del run full: si existe un checkpoint, se descarga y se reanuda, omitiendo archivos ya procesados.
- Tabla auxiliar `indexed_files` en el sqlite-vec local para tracking idempotente intra-commit (sobrevive al resume).
- Campo nuevo `files_skipped_resume` en `IndexResultDto` para visibilidad operativa.
- Variables de entorno nuevas: `TITVO_CHECKPOINT_EVERY_N_FILES` (default 100) y `TITVO_CHECKPOINT_KEY` (template S3).
- Snapshot del repo local (`.git`) subido a S3 una sola vez por run como `repo.tar.gz` para evitar re-ejecutar `git fetch` y los `git cat-file blob` en resume.
- Lock distribuido en S3 por `(repository_url, branch)` para impedir runs concurrentes sobre la misma rama. TTL con renovación automática y stale-lock takeover.
- Batching explícito de embeddings en `LangChainEmbeddingAdapter` (configurable vía `TITVO_EMBEDDING_BATCH_SIZE`, default 1000) con loop por batch y logging de progreso, en lugar de delegar el batch size interno de `langchain-openai`.
- Streaming chunk-by-chunk del pipeline split → embed → insert en lugar de acumular todos los chunks y embeddings en memoria. Memoria pico: ~10 KB (un chunk + un embedding) en lugar de ~6 MB por bloque.
- Aumento de capacidad del job AWS Batch: `job_vcpu` de 1 a 2 (paralelizar splitting/inserts), `job_memory` de 2048 a 4096 MB (headroom para tracking de `indexed_files` + buffers de streaming) y `max_vcpus` de 4 a 8 (paralelismo real entre jobs distintos).

## Capabilities

### New Capabilities

- `rag-indexer-resume`: contrato de checkpointing y resume del `rag-indexer`: flush periódico a S3, descarga al inicio, idempotencia intra-commit y métricas de progreso.

### Modified Capabilities

*(sin cambios en capabilities existentes — el comportamiento externo de "indexar commit X" no cambia, solo se hace resilient)*

## Impact

- `src/rag-indexer/src/rag_indexer/application/index_repository_use_case.py`: nueva rama de resume en `_execute_full` y flush en `_process_files`.
- `src/rag-indexer/src/rag_indexer/domain/ports/artifact_store_port.py`: métodos `upload_checkpoint`, `download_checkpoint`, `upload_source_snapshot`, `download_source_snapshot`, `delete_source_snapshot`, `acquire_lock`, `release_lock`, `renew_lock`, `get_lock`.
- `src/rag-indexer/src/rag_indexer/domain/dto/lock_dto.py` (nuevo): DTO `LockInfo` con campos `owner`, `acquired_at`, `expires_at`, `commit_sha`.
- `src/rag-indexer/src/rag_indexer/domain/ports/repository_provider.py`: nuevo método `restore_from_snapshot(snapshot_path, commit_sha)` y soporte para `exclude_paths` en `get_files`.
- `src/rag-indexer/src/rag_indexer/infra/adapters/s3_artifact_store_adapter.py`: implementar los nuevos métodos de checkpoint + snapshot.
- `src/rag-indexer/src/rag_indexer/infra/adapters/langchain_embedding_adapter.py`: reemplazar `client.embed_documents(texts)` por un loop de batching explícito con `TITVO_EMBEDDING_BATCH_SIZE`, logging por batch y retry per-batch.
- `src/rag-indexer/src/rag_indexer/application/index_repository_use_case.py`: refactor `_process_files` para procesar archivos en bloques de N (con `IndexRepositoryUseCase` actualizando el split → embed → insert → mark indexed → flush checkpoint entre bloques).
- `src/rag-indexer/src/rag_indexer/infra/adapters/sqlite_vec_store_adapter.py`: crear tabla `indexed_files` y exponer `is_file_indexed` / `mark_file_indexed`.
- `src/rag-indexer/src/rag_indexer/domain/dto/index_result_dto.py`: agregar campo `files_skipped_resume`.
- `src/rag-indexer/README.md`: documentar las nuevas variables de entorno.
- `src/rag-indexer/aws/batch/terragrunt.hcl`: subir `job_vcpu` a 2 y `job_memory` a 4096.
- **Documentación cross-repo**: agregar nota en `docs/rag-indexer.md` para el futuro implementer de `src/agent` sobre cómo usar el lock S3 para evitar gatillar jobs duplicados (`get_active_lock` antes de `trigger_full`/`trigger_delta`).
- No afecta otros servicios en este change (la integración en `src/agent` queda como follow-up).

## Non-goals

- Cambiar el formato de almacenamiento (sigue siendo sqlite-vec).
- Resume cross-commit (eso ya lo cubre `_execute_delta`).
- Optimizar rate-limit de OpenAI o paralelismo de embeddings (cambio aparte).
- Cambiar el orquestador (sigue siendo AWS Batch).
- Persistir estado más allá del run actual (el checkpoint se borra al terminar el index full exitoso).
- Reemplazar el lock por un mecanismo basado en DynamoDB o servicio externo (sigue S3 con conditional write).
- Forzar espera activa cuando un lock ajeno está activo: el sistema falla rápido en lugar de bloquear.
