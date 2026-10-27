## 1. Código

- [x] 1.1 `IEmbeddingProvider.embed_iter` en el port con retorno `Iterator[tuple[str, list[float]]]`.
- [x] 1.2 `LangChainEmbeddingAdapter.embed_iter` emite pares vía `_embed_batch_pairs`; `RuntimeError` si `len(vectores) != len(lote)`.
- [x] 1.3 `_process_files` itera pares; eliminar `_zip_chunks_with_embeddings`.
- [x] 1.4 Tests: pares alineados con `batch_size=2` sobre generador compartido; mismatch de cardinalidad; regresión en use case con adapter real (3 inserts alineados, 2 llamadas al proveedor). Fakes existentes de `embed_iter` actualizados a pares.

## 2. Verificación

- [x] 2.1 `ruff check`, `pytest tests/unit` (96 passed) y `tests/integration/test_s3_artifact_store_integration.py` (10 passed).
- [ ] 2.2 Post-deploy: full index de una rama y comprobar en `index.db` que `count(*)` de chunks por archivo > 1 para archivos grandes.
- [ ] 2.3 Relanzar full index en todas las ramas indexadas en prod.

## 3. Documentation

- [x] 3.1 `docs/rag-indexer.md`: `embed_iter` emite pares; nota del bug y de la re-indexación.
