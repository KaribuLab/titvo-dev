## Decisions

### D1. El provider emite pares, no se duplica el iterador

Alternativas: `itertools.tee` en el use case (buffer oculto de hasta `batch_size` chunks y fácil de volver a romper) o materializar la lista de chunks por archivo (pierde el streaming). Emitir `(texto, embedding)` desde `embed_iter` hace imposible desalinear: el consumidor no tiene acceso al iterador fuente.

### D2. Validar cardinalidad del lote

Si el proveedor devuelve menos o más vectores que textos, `zip` truncaría en silencio. Se lanza `RuntimeError` y el run aborta; el resume retoma desde el archivo siguiente al último completo.

### D3. Regresión con adapter real

El test del use case usa `LangChainEmbeddingAdapter` real con `embed_documents` falso y un generador real del splitter, para que el patrón "mismo generador consumido dos veces" quede cubierto.
