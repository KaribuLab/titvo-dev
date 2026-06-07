## MODIFIED Requirements

### Requirement: El prompt del agente distingue contexto RAG del contexto del commit
El system prompt del agente SHALL instruir explícitamente que:
- Los archivos seleccionados para el análisis actual se obtienen via herramienta MCP (`git.commit-files` u equivalente), ya sea en modo commit o full scan.
- El índice vectorial representa el estado del código base para la rama y NO debe confundirse con los archivos seleccionados para el análisis actual.

#### Scenario: Prompt con índice disponible
- **WHEN** el índice RAG está disponible para la rama
- **THEN** el mensaje de usuario incluye una sección indicando que el código base de la rama está indexado como contexto de fondo

#### Scenario: Prompt sin índice disponible
- **WHEN** el índice RAG no está disponible (indexación falló o branch ausente)
- **THEN** el mensaje de usuario NO incluye la sección de contexto RAG y el análisis procede solo con los archivos seleccionados vía MCP

#### Scenario: Prompt en full scan
- **WHEN** el scan se ejecuta en modo `full`
- **THEN** el mensaje distingue que los archivos de análisis vienen del snapshot full obtenido por MCP y que RAG sigue siendo solo contexto de fondo

### Requirement: El agente usa los archivos del commit exclusivamente via MCP
El agente SHALL obtener los archivos seleccionados para analizar únicamente a través del nodo MCP (`mcp_retrieve`). En modo `commit`, esos archivos corresponden al commit. En modo `full`, esos archivos corresponden al snapshot de la rama/ref seleccionada. El índice vectorial NO debe usarse como fuente primaria de archivos para analizar.

#### Scenario: Archivos del commit obtenidos via MCP
- **WHEN** el grafo LangGraph ejecuta el nodo `mcp_retrieve` en modo `commit`
- **THEN** los archivos del commit se obtienen via la herramienta MCP correspondiente al SCM (GitHub/Bitbucket/CLI)

#### Scenario: Archivos full scan obtenidos via MCP
- **WHEN** el grafo LangGraph ejecuta el nodo `mcp_retrieve` en modo `full`
- **THEN** los archivos de la rama/ref seleccionada se obtienen via la herramienta MCP correspondiente al SCM (GitHub/Bitbucket/CLI)

#### Scenario: Agente no mezcla fuentes de archivos
- **WHEN** el agente tiene acceso tanto al índice RAG como a los archivos via MCP
- **THEN** usa MCP para los archivos seleccionados del análisis y el índice RAG solo como contexto de fondo (arquitectura general del proyecto)
