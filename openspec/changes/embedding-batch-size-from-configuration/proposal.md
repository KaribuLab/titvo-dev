## Why

El tamaño de lote de embeddings del rag-indexer se leía de la variable de entorno `TITVO_EMBEDDING_BATCH_SIZE`, fijada en la job definition de Batch. Cambiarlo exigía redeploy de infraestructura. El resto de la configuración de embeddings (`embedding_provider`, `embedding_model`, `embedding_api_key`, `embedding_base_url`) ya vive en la tabla DynamoDB de configuración vía `IConfigurationProvider`; el lote debe resolverse por el mismo mecanismo.

## What Changes

- `LangChainEmbeddingAdapter` resuelve `batch_size` perezosamente con `get_value("embedding_batch_size")`: ausente o vacío → 1000 (valor actual); entero ≤ 0 o no numérico → `ValueError`. Un `batch_size` explícito en el constructor sigue teniendo prioridad (tests, runs locales).
- `main.py` deja de leer `TITVO_EMBEDDING_BATCH_SIZE`; `CheckpointConfig` pierde `embedding_batch_size`.
- README del indexer: nueva tabla "Configuración de embeddings" con los cinco `parameter_id`.

## Capabilities

### New Capabilities

- Ninguna.

### Modified Capabilities

- `rag-indexer-resume`: el tamaño de lote se configura con `embedding_batch_size` en la tabla de configuración, no con variable de entorno.

## Impact

- `src/rag-indexer/src/rag_indexer/infra/adapters/langchain_embedding_adapter.py`, `src/main.py`, `checkpoint_config_dto.py`, tests unitarios.
- Job definition de Batch: `TITVO_EMBEDDING_BATCH_SIZE` queda ignorada si estaba definida; puede eliminarse.

## Non-goals

- No mover al mismo mecanismo `TITVO_CHUNK_SIZE`, `TITVO_CHUNK_OVERLAP` ni las variables de checkpoint/lock.
- No corregir aquí el bug del `zip` compartido en `_process_files` (1 chunk por archivo con embedding desalineado); va en un change aparte.
