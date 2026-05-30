## MODIFIED Requirements

### Requirement: El agente usa los archivos del commit exclusivamente via MCP
El agente SHALL obtener los archivos del commit a analizar únicamente a través del nodo MCP (`mcp_retrieve`). El índice vectorial NO debe usarse como fuente de los archivos del commit. El índice vectorial MAY ser consultado como enriquecimiento de contexto de codebase para los nodos experto, a través del nodo `rag_retrieve`, siempre que se mantenga separado del contenido del commit en el human message de cada experto.

#### Scenario: Archivos del commit obtenidos via MCP
- **WHEN** el grafo LangGraph ejecuta el nodo `mcp_retrieve`
- **THEN** los archivos del commit se obtienen via la herramienta MCP correspondiente al SCM (GitHub/Bitbucket/CLI)

#### Scenario: Agente mantiene separación entre fuentes de datos
- **WHEN** el agente tiene acceso tanto al índice RAG como a los archivos via MCP
- **THEN** usa MCP para los archivos del commit (bloque `=== FILE: {path} ===`) y el índice RAG como contexto de enriquecimiento de codebase (bloque `=== RAG CONTEXT ===`), manteniendo ambos bloques semánticamente separados en el human message de cada experto
