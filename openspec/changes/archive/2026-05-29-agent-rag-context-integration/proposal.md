## Why

El agente construye y mantiene un índice vectorial del codebase de la rama (SQLite-vec en S3), pero los expertos LangGraph nunca lo consultan: analizan solo los archivos del commit vía MCP. Esto limita la capacidad de detectar vulnerabilidades que dependen de cómo el código modificado es usado en el resto del proyecto (por ejemplo, una función vulnerable del commit expuesta por un endpoint público no modificado).

## What Changes

- **Nuevo nodo LangGraph `rag_retrieve`**: se ejecuta después de `mcp_retrieve` y antes de los expertos; descarga `latest/index.db` de S3 y hace búsqueda vectorial por cada archivo del commit.
- **Nuevo campo `rag_chunks` en `AgentState`**: lista de chunks semánticamente relacionados del codebase de la rama.
- **Nuevo puerto de dominio `IRagContextPort`** en el agente con su adaptador `S3SqliteRagContextAdapter` (descarga S3 + búsqueda sqlite-vec).
- **`BaseExpertNode` incluye los chunks RAG** en el human message como bloque `=== RAG CONTEXT ===`, separado de los archivos del commit.
- **Prompts de los 5 expertos** reciben sección nueva que explica cómo interpretar el contexto RAG y cuándo escalar severidad.
- **`workflow.py`** agrega el nodo `rag_retrieve` entre `mcp_retrieve` y `expert_prompt_hardening`.
- **`main.py`** instancia y cablea el nuevo adaptador; lee `embedding_model` y `embedding_api_key` de DynamoDB.
- **`pyproject.toml`** del agente agrega dependencia `sqlite-vec`.
- Degradación graceful: si el índice no está disponible o la búsqueda falla, `rag_chunks = []` y el análisis continúa con el comportamiento actual.

## Capabilities

### New Capabilities

- `rag-context-expert-enrichment`: Nodo LangGraph, puerto de dominio y adaptador que permiten a los expertos recibir chunks semánticamente relacionados del codebase completo de la rama como contexto adicional durante el análisis.

### Modified Capabilities

- `agent-rag-context`: Los requisitos cambian: el índice RAG pasa de ser solo "fondo arquitectónico" a ser contexto activamente consultado y entregado a los expertos durante el análisis. Se modifica el escenario "Agente no mezcla fuentes de archivos" para permitir que el índice sea consultado como enriquecimiento, manteniendo la separación de que MCP sigue siendo la fuente de los archivos del commit.

## Non-goals

- Reemplazar MCP como fuente de los archivos del commit; MCP sigue siendo la única fuente de verdad para los archivos a analizar.
- Agregar herramientas MCP de búsqueda vectorial (la búsqueda ocurre internamente en el nodo, no a través del protocolo MCP).
- Cambiar la lógica de indexación del rag-indexer.
- Construir un índice local nuevo; se reutiliza el `index.db` generado por el rag-indexer existente.

## Impact

- `src/agent/`: nuevo nodo, nuevo puerto, nuevo adaptador, cambios en `AgentState`, `BaseExpertNode`, `workflow.py`, `main.py`, `pyproject.toml`, 5 archivos de prompts.
- `openspec/specs/agent-rag-context/spec.md`: delta de requisitos.
- Sin cambios en `src/rag-indexer/`, `src/mcp/`, `src/api/`.
