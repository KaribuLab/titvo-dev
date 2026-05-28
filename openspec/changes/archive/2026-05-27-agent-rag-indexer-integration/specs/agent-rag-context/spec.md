## ADDED Requirements

### Requirement: El prompt del agente distingue contexto RAG del contexto del commit
El system prompt del agente SHALL instruir explícitamente que:
- Los archivos del commit actual se obtienen via herramienta MCP (`git.commit-files` u equivalente).
- El índice vectorial representa el estado del código base para la rama y NO debe confundirse con el commit en análisis.

#### Scenario: Prompt con índice disponible
- **WHEN** el índice RAG está disponible para la rama
- **THEN** el mensaje de usuario incluye una sección indicando que el código base de la rama está indexado

#### Scenario: Prompt sin índice disponible
- **WHEN** el índice RAG no está disponible (indexación falló o branch ausente)
- **THEN** el mensaje de usuario NO incluye la sección de contexto RAG y el análisis procede solo con los archivos del commit vía MCP

### Requirement: El agente usa los archivos del commit exclusivamente via MCP
El agente SHALL obtener los archivos del commit a analizar únicamente a través del nodo MCP (`mcp_retrieve`). El índice vectorial NO debe usarse como fuente de los archivos del commit.

#### Scenario: Archivos del commit obtenidos via MCP
- **WHEN** el grafo LangGraph ejecuta el nodo `mcp_retrieve`
- **THEN** los archivos del commit se obtienen via la herramienta MCP correspondiente al SCM (GitHub/Bitbucket/CLI)

#### Scenario: Agente no mezcla fuentes de archivos
- **WHEN** el agente tiene acceso tanto al índice RAG como a los archivos via MCP
- **THEN** usa MCP para los archivos del commit y el índice RAG solo como contexto de fondo (arquitectura general del proyecto)
