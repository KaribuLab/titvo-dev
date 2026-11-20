## 1. Adapter y wiring

- [x] 1.1 `LangChainEmbeddingAdapter`: `batch_size: int | None = None`, propiedad `batch_size` con `_resolve_batch_size()` desde `get_value("embedding_batch_size")`, default 1000, `ValueError` si inválido, log INFO del valor usado.
- [x] 1.2 `main.py`: eliminar lectura de `TITVO_EMBEDDING_BATCH_SIZE` y el campo del log; construir el adapter sin `batch_size`.
- [x] 1.3 `CheckpointConfig`: eliminar `embedding_batch_size`.
- [x] 1.4 Tests: default (None/vacío/espacios → 1000), valor custom, inválidos (`0`, `-5`, `abc`, `1.5`), override explícito no consulta la tabla, resolución una sola vez.

## 2. Verificación

- [x] 2.1 `uv run ruff check` y `pytest tests/unit` en `src/rag-indexer` (93 passed).
- [ ] 2.2 Post-deploy: job de indexación loguea `Using embedding_batch_size=N from configuration` o `embedding_batch_size not configured; using default 1000`.

## 3. Documentation

- [x] 3.1 `src/rag-indexer/README.md`: quitar la fila de `TITVO_EMBEDDING_BATCH_SIZE`; nueva sección "Configuración de embeddings" con los cinco `parameter_id` y ejemplo `put-item`.
- [x] 3.2 `docs/rag-indexer.md`: referencia a `embedding_batch_size` en la sección de endpoint y en el resumen de batching.
