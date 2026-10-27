## Why

`IndexRepositoryUseCase._process_files` pasaba el mismo generador de chunks a `embed_iter` y a `zip`. `zip` sacaba el chunk 0; `embed_iter` consumía el resto del generador para armar su lote y devolvía el vector del chunk 1; al pedir el siguiente chunk el generador ya estaba agotado. Resultado reproducido: por archivo se insertaba un solo chunk (el 0) con el embedding del chunk 1, el chunk 0 nunca se embebía y los chunks 2..N se embebían (se pagaban) y se descartaban. Los tests unitarios no lo detectaban porque mockeaban `embed_iter` con un iterador independiente. Todo índice generado desde el pipeline streaming tiene ~1 chunk por archivo con vectores desalineados.

## What Changes

- `IEmbeddingProvider.embed_iter(texts) -> Iterator[tuple[str, list[float]]]` se declara en el port y emite pares `(texto, embedding)`; alineación por construcción.
- `LangChainEmbeddingAdapter.embed_iter` emite pares y falla con `RuntimeError` si el proveedor devuelve una cantidad de vectores distinta a la del lote.
- `_process_files` itera los pares del provider e inserta cada uno; se elimina `_zip_chunks_with_embeddings`.
- Tests: adapter con generador compartido y límite de lote; use case con adapter real y cliente falso verificando N inserts alineados.

## Capabilities

### New Capabilities

- Ninguna.

### Modified Capabilities

- `rag-indexer-resume`: el pipeline streaming consume pares `(chunk, embedding)` del provider; el use case no vuelve a leer el iterador de chunks.

## Impact

- `src/rag-indexer`: `domain/ports/embedding_provider.py`, `infra/adapters/langchain_embedding_adapter.py`, `application/index_repository_use_case.py`, tests.
- Operación: los índices existentes en S3 están corruptos en contenido (no en formato). Hay que relanzar un full index por rama tras el deploy; el delta no los repara.

## Non-goals

- No cambiar el tamaño de lote ni el chunking.
- No agregar un comando de re-indexación masiva; se dispara por rama con el trigger existente.
