## MODIFIED Requirements

### Requirement: Streaming del pipeline split → embed → insert
El flujo de indexación SHALL procesar archivos en bloques y, dentro de cada bloque, consumir chunks como `Iterator` (no como `List`). El `ICodeSplitter` SHALL exponer `iter_chunks(file) -> Iterator[str]` y el `IEmbeddingProvider` SHALL exponer `embed_iter(texts_iter: Iterable[str]) -> Iterator[tuple[str, list[float]]]` que agrupa automáticamente en lotes de `embedding_batch_size` y emite pares `(chunk, embedding)` uno a uno, en el orden de entrada. El use case SHALL insertar cada par con `vector_store.insert_one(...)` y SHALL NOT volver a leer el iterador de chunks una vez entregado al provider. Si el proveedor devuelve una cantidad de vectores distinta a la de textos del lote, `embed_iter` SHALL lanzar `RuntimeError`.

#### Scenario: Cada chunk se inserta con su propio vector
- **WHEN** un archivo produce los chunks `a`, `bb`, `ccc` con `batch_size=2`
- **THEN** se insertan 3 filas `(a, v(a))`, `(bb, v(bb))`, `(ccc, v(ccc))` y el proveedor recibe dos lotes `[a, bb]` y `[ccc]`

#### Scenario: Cardinalidad inválida aborta el run
- **WHEN** el proveedor devuelve 1 vector para un lote de 2 textos
- **THEN** `embed_iter` lanza `RuntimeError` y no se inserta ninguna fila de ese lote

#### Scenario: Memoria pico del bloque es ~1 lote
- **WHEN** el use case procesa un bloque de 50 archivos con 1000 chunks totales
- **THEN** la memoria pico es un lote de `embedding_batch_size` chunks con sus vectores, no los 1000 chunks acumulados

#### Scenario: Pipeline streaming con batch interno
- **WHEN** `embed_iter` recibe un iterador de 5000 chunks y `embedding_batch_size=1000`
- **THEN** el adapter hace 5 llamadas al SDK (cada una con 1000 chunks) y emite 5000 pares uno a uno

#### Scenario: Failure mid-stream no pierde chunks ya commiteados
- **WHEN** un chunk N falla en insert después de haber commiteado N-1 exitosamente
- **THEN** el run aborta y los N-1 chunks ya están en el DB + `indexed_files` para los archivos completos; el resume retoma desde el siguiente archivo

#### Scenario: ICodeSplitter.iter_chunks como iterator lazy
- **WHEN** se llama `iter_chunks(file)` sobre un archivo de 10k líneas
- **THEN** retorna un `Iterator[str]` que produce chunks on-demand al ser consumido, sin construir la lista completa upfront
