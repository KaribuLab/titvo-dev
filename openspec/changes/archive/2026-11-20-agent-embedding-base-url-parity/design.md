## Context

Indexer y agente deben producir vectores comparables: mismo modelo y mismo endpoint. El indexer ya resolvía `embedding_base_url`; el agente no.

## Decisions

### D1. Replicar la construcción del indexer, no compartirla

`LangChainEmbeddingAdapter` vive en `src/rag-indexer` (otro submódulo, otro deploy). Se replica la construcción (`base_url`, `check_embedding_ctx_length=False`) en `_build_embeddings` del adapter del agente, con un test que fija esos kwargs.

### D2. Misma fuente de configuración

`embedding_base_url` se lee con `get_value` desde la tabla de configuración, igual que el indexer. Vacío o ausente → endpoint default de OpenAI.
