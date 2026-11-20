## MODIFIED Requirements

### Requirement: Batching explícito de embeddings con tamaño configurable
`LangChainEmbeddingAdapter.embed(texts)` SHALL particionar la lista de entrada en bloques de `embedding_batch_size` chunks y enviar cada bloque con un `embed_documents` independiente. El tamaño SHALL resolverse una vez por instancia desde `IConfigurationProvider.get_value("embedding_batch_size")` (tabla DynamoDB de configuración): ausente o vacío → 1000; entero ≤ 0 o no numérico → `ValueError` en el primer uso. Un `batch_size` explícito en el constructor SHALL tener prioridad y no consultar la tabla. El adapter SHALL loguear `INFO Embedded batch i/N chunks=N duration_ms=Y` por bloque, SHALL reintentar cada bloque hasta 3 veces ante error transitorio, y SHALL retornar la concatenación de los embeddings en el orden original.

#### Scenario: Batching funcionado con tamaño por defecto
- **WHEN** `embed(texts)` recibe 3500 chunks y `embedding_batch_size` no existe en la tabla (default 1000)
- **THEN** el adapter hace 4 llamadas al provider (1000 + 1000 + 1000 + 500) y retorna 3500 embeddings

#### Scenario: Batching con tamaño custom
- **WHEN** la tabla tiene `embedding_batch_size=500` y `embed` recibe 1200 chunks
- **THEN** el adapter hace 3 llamadas (500 + 500 + 200) y retorna 1200 embeddings

#### Scenario: Tamaño inválido aborta el job
- **WHEN** la tabla tiene `embedding_batch_size` igual a `0`, `-5` o `abc`
- **THEN** el primer `embed` lanza `ValueError` con `embedding_batch_size must be a positive integer` y no se llama al provider

#### Scenario: Batch vacío o lista vacía
- **WHEN** `embed` recibe una lista vacía o un solo batch que resulta en 0 chunks
- **THEN** el adapter retorna `[]` sin llamar al provider

#### Scenario: Reintento per-batch ante error transitorio
- **WHEN** el provider retorna error 429 o 5xx en el batch N
- **THEN** el adapter reintenta el mismo batch hasta 3 veces con backoff exponencial (1s, 2s, 4s), loguea `WARNING Retry batch N attempt=X error=...` y continúa si recupera, o aborta si supera el máximo
