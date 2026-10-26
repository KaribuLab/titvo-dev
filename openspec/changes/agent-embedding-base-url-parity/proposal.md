## Why

El rag-indexer resuelve `embedding_base_url` y construye `OpenAIEmbeddings` contra ese endpoint (p. ej. OpenRouter), pero el agente construía `OpenAIEmbeddings` solo con `api_key`, siempre contra api.openai.com. En prod la key de OpenRouter llegaba a OpenAI, respondía `401 invalid_api_key`, el adapter lo clasificaba FATAL y RAG quedaba deshabilitado en todos los scans de forma silenciosa.

## What Changes

- `S3SqliteRagContextAdapter` acepta `embedding_base_url` y construye el cliente igual que `LangChainEmbeddingAdapter` del indexer: `base_url` + `check_embedding_ctx_length=False` cuando hay URL; default de OpenAI cuando no.
- `main.py` lee `embedding_base_url` con `get_value` (no secreto), igual que el indexer, y lo pasa al adapter. El log de habilitación de RAG muestra el endpoint.

## Capabilities

### New Capabilities

- Ninguna.

### Modified Capabilities

- `agent-rag-context`: el agente embebe la consulta con las mismas claves de configuración y el mismo endpoint que el indexer.

## Impact

- `src/agent/src/code_analysis/infra/adapters/s3_sqlite_rag_context_adapter.py`, `src/agent/src/main.py`, tests unitarios.
- Sin cambios en rag-indexer, MCP ni API. Sin nuevas claves de configuración: `embedding_base_url` ya existe para el indexer.

## Non-goals

- No agregar proveedores de embeddings distintos de `openai`-compatible (misma restricción que el indexer).
- No corregir aquí el cuelgue por falta de timeout en las llamadas al modelo de chat; va en un change aparte.
