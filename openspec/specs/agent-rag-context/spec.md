# agent-rag-context Specification

## Purpose

Separación explícita entre contexto RAG (índice vectorial de la rama) y archivos del commit en análisis: el prompt y el grafo LangGraph usan MCP para el commit y RAG solo como fondo arquitectónico.
## Requirements
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

### Requirement: Un fallo no recuperable del proveedor de embeddings no se repite durante el scan

Cuando la generación del embedding de consulta falla con un error no recuperable (sin créditos o
cuota, 401, 403, 404, 400), el adapter RAG SHALL registrar un único `WARNING` con la causa y SHALL
responder sin contexto RAG a todas las consultas restantes del mismo scan sin volver a llamar al
proveedor de embeddings. El análisis SHALL continuar sin RAG. `configure()` SHALL limpiar ese
estado para el siguiente scan.

#### Scenario: Sin créditos en el primer embedding

- **WHEN** el primer `search` del scan falla con `429 insufficient_quota` y el nodo RAG consulta 10
  archivos
- **THEN** el proveedor de embeddings se llama exactamente una vez, `rag_chunks` es `[]` y los
  expertos se ejecutan

#### Scenario: Error transitorio no deshabilita el RAG

- **WHEN** un `search` falla con timeout
- **THEN** el siguiente `search` del mismo scan vuelve a llamar al proveedor de embeddings

