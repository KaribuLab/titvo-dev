# Proposal

## Why

El RAG indexer permite configurar el modelo y la credencial de embeddings, pero no la URL base del servicio. Esto impide dirigir sus solicitudes a otros proveedores compatibles con la API de OpenAI mediante la configuración del componente.

## What Changes

- Incorporar el parámetro opcional `embedding_base_url`, obtenido con `IConfigurationProvider.get_value`, igual que `embedding_model`.
- Utilizar esa URL al construir el cliente de embeddings para `embedding_provider=openai`, incluyendo endpoints compatibles.
- Conservar el comportamiento actual cuando el parámetro esté ausente o vacío.
- Cubrir configuración, compatibilidad y reutilización del cliente con pruebas unitarias y documentar la operación.

## Capabilities

### New Capabilities
- `rag-embedding-configuration`: Resolución de la configuración del cliente de embeddings del RAG indexer, incluyendo su endpoint compatible con OpenAI.

### Modified Capabilities
Ninguna.

## Impact

- `src/rag-indexer/src/rag_indexer/infra/adapters/langchain_embedding_adapter.py` y sus pruebas unitarias.
- Tabla DynamoDB de configuración existente: nuevo registro opcional `embedding_base_url`, sin cambios de esquema ni permisos.
- Documentación del componente y `docs/architecture.md`.
- Se reutilizan las dependencias y el puerto de configuración existentes.

## Non-goals

- Añadir SDKs o protocolos de proveedores no compatibles con OpenAI.
- Cambiar la configuración de embeddings del agente consumidor, dimensiones vectoriales, modelos por defecto, batching o checkpoints.
- Introducir una variable de entorno como fuente directa alternativa para el indexer.
