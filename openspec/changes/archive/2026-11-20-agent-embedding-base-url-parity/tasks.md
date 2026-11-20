## 1. Adapter y wiring

- [x] 1.1 `S3SqliteRagContextAdapter.__init__`: parámetro `embedding_base_url: str | None = None`, strip.
- [x] 1.2 `_build_embeddings`: `base_url` + `check_embedding_ctx_length=False` cuando hay URL; log del endpoint.
- [x] 1.3 `main.py`: leer `embedding_base_url` y pasarlo al adapter; log de RAG habilitado con endpoint.
- [x] 1.4 Tests: kwargs exactos con y sin `embedding_base_url`.

## 2. Verificación

- [x] 2.1 `uv run ruff check` y `uv run pytest tests/unit` (393 passed).
- [ ] 2.2 Post-deploy: scan en prod loguea `Using openai embeddings ... base_url=https://openrouter.ai/...` y `Retrieved N unique RAG chunks` con N > 0.

## 3. Documentation

- [x] 3.1 `docs/architecture.md`: paridad de claves de embeddings entre agente e indexer.
- [x] 3.2 `docs/rag-indexer.md`: nota de que el agente lee el mismo `embedding_base_url`.
