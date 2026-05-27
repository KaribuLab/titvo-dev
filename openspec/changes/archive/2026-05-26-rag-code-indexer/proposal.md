## Why

El agente de análisis de código (`src/agent`) actualmente procesa los archivos del repositorio en tiempo real en cada ejecución, lo que implica latencia alta y costo elevado por tokens al pasar contexto crudo al LLM. Implementar RAG permite pre-indexar el código del repositorio y recuperar solo los fragmentos relevantes al momento del análisis, mejorando velocidad y reduciendo costos.

## What Changes

- Nuevo servicio `src/rag-indexer` que obtiene archivos de un repositorio vía REST API de GitHub o Bitbucket (con access token), genera embeddings del código y los persiste en una base de datos libSQL (SQLite embebido) almacenada en S3.
- **Dos modos de indexado**: full index (primera vez, por rama) y delta index (commits posteriores, por SHA).
- **Delta indexing**: si ya existe un commit previo indexado, el sistema obtiene solo los archivos modificados/añadidos/eliminados vía la API de comparación y actualiza el índice incrementalmente.
- **Persistencia en S3**: la base de datos libSQL se almacena por commit y con un puntero `latest/` para acceso rápido: `s3://<bucket>/<repo_host>/<owner>/<repo>/<commit_sha>/index.db` y `s3://<bucket>/<repo_host>/<owner>/<repo>/latest/index.db`.
- El indexado se ejecuta como tarea de AWS ECS a demanda: en modo full recibe `TITVO_BRANCH`, en modo delta recibe `TITVO_COMMIT_SHA`.
- Se expone `IVectorStorePort` con operaciones de búsqueda y gestión del índice, listo para ser consumido por `src/agent` en un cambio futuro (`agent-rag-integration`).

## Capabilities

### New Capabilities

- `repository-indexer`: Obtiene archivos de un repositorio via REST API (GitHub/Bitbucket) con access token, soporta modo full (todas las ramas/archivos) y modo delta (diff entre commits via API de comparación).
- `embedding-store`: Genera embeddings con LangChain, los persiste en una base de datos libSQL embebida (SQLite local), y gestiona delta indexing (insertar nuevos, eliminar obsoletos). La DB se sube/baja de S3.
- `s3-artifact-store`: Gestiona la persistencia de los archivos de base de datos libSQL en S3, con estructura por commit SHA y puntero `latest/` con metadatos.

### Modified Capabilities

*(sin cambios en capabilities existentes)*

## Impact

- **Nuevo proyecto**: `src/rag-indexer` (Python 3.13, uv, LangChain, httpx, sqlite-vec)
- **Dependencias nuevas**: `langchain`, `langchain-community`, `langchain-openai` (o equivalente), `sqlite-vec`, `httpx`
- **Infraestructura**: ECR + ECS task en AWS; bucket S3 dedicado para las bases de datos del índice RAG
- **No afecta** `src/agent` ni ningún otro servicio existente en este cambio

## Non-goals

- Integración del RAG en `src/agent` (se hará en el cambio `agent-rag-integration`).
- Trigger post-scan desde el agente para lanzar el rag-indexer (también en `agent-rag-integration`).
- API o endpoint para consultar el índice.
- Reindexado automático ante cambios en el repositorio (webhooks).
- Soporte para proveedores distintos de GitHub y Bitbucket en esta iteración.
- Soporte multi-tenant o multi-repositorio concurrente en una misma ejecución.
