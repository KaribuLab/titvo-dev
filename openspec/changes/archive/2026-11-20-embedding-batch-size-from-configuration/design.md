## Decisions

### D1. Resolución perezosa en el adapter, no en `main`

`_get_embeddings_client` ya resuelve provider/model/base_url/key desde `IConfigurationProvider` en el primer uso. `batch_size` sigue el mismo patrón (propiedad cacheada por instancia), así `main` no necesita conocer la clave y los tests de `main` no tocan DynamoDB.

### D2. Fallar rápido ante valor inválido

Un `embedding_batch_size` no numérico o ≤ 0 lanza `ValueError` en el primer `embed`, igual que hacía `_parse_positive_int` con la variable de entorno. Un lote silenciosamente distinto cambiaría costo y comportamiento sin aviso.

### D3. Override explícito

`LangChainEmbeddingAdapter(provider, batch_size=N)` sigue aceptado y no consulta la tabla. Lo usan los tests existentes y la integración con LocalStack.
