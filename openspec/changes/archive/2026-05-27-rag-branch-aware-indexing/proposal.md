## Why

El rag-indexer actualmente indexa el HEAD de una rama (ej. `main`) sin considerar si el commit analizado existe en esa rama. Cuando el agente analiza un commit de una PR que aún no fue mergeada, el índice RAG apunta al estado de `main` y no refleja los archivos de la rama en curso. Además, cuando se hace un delta-index del commit a analizar, el agente desconoce que los archivos recuperados via MCP son la fuente de verdad para ese commit y podrían solaparse con datos del índice base.

## What Changes

- **Indexación full automática por rama**: Si al iniciar un análisis no existe un índice en S3 para la rama del commit en análisis, el sistema dispara un full-index del estado del repositorio hasta ese commit antes de continuar.
- **Clave S3 por rama**: El prefijo en S3 incorpora la rama (`{repo}/{branch}/latest/`) en lugar de un único `latest/` global, evitando colisiones entre ramas.
- **Señalización de archivos delta en el agente**: Cuando el commit a analizar fue indexado vía delta, el agente recibe una indicación explícita de que los archivos obtenidos desde el MCP `git.commit-files` representan el estado canónico de ese commit y tienen precedencia sobre el índice RAG para esos paths.

## Capabilities

### New Capabilities

- `rag-branch-scoped-index`: Gestión de índices RAG separados por rama en S3 (prefijo `{repo}/{branch}/`), con detección automática de índice faltante y fallback a full-index antes del análisis.
- `agent-delta-file-priority`: Mecanismo por el cual el agente identifica que está operando sobre un delta y que los archivos del MCP son la fuente de verdad para los paths modificados.

### Modified Capabilities

- `langgraph-orchestration`: El flujo del agente incorpora la señal de "archivos delta son canónicos" al construir el contexto de análisis.

## Impact

- `src/rag-indexer`: Cambios en `S3ArtifactStoreAdapter` (prefijo de clave), `IndexRepositoryUseCase` (detección de índice por rama), y `main.py` (recepción de rama en modo delta).
- `src/agent`: `MCPRetrievalNode` y el estado del grafo reciben indicador de delta; los nodos de análisis priorizan archivos MCP sobre RAG para paths en el diff.
- Sin cambios en APIs externas ni contratos de red.

## Non-goals

- No se implementa soporte multi-rama simultáneo en el mismo índice (no merge de índices).
- No se modifica la lógica de embeddings ni de chunking.
- No se cambia el proveedor de MCP ni su protocolo.
