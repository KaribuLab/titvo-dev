## ADDED Requirements

### Requirement: El agente embebe la consulta con la misma configuración que el indexer

`S3SqliteRagContextAdapter` SHALL build its embeddings client from the same four configuration
keys the rag-indexer uses (`embedding_provider`, `embedding_model`, `embedding_api_key`,
`embedding_base_url`). When `embedding_base_url` is set, the client SHALL target that URL with
`check_embedding_ctx_length=False`; when it is empty or missing, the client SHALL use the OpenAI
default endpoint.

#### Scenario: Endpoint compatible con OpenAI

- **WHEN** `embedding_base_url` is `https://openrouter.ai/api/v1`
- **THEN** the agent embeds the scan query against that URL with `check_embedding_ctx_length=False`

#### Scenario: Sin base_url

- **WHEN** `embedding_base_url` is missing
- **THEN** the agent embeds against the OpenAI default endpoint with only `model` and `api_key`
