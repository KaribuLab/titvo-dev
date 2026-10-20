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
For Git tasks the agent SHALL retrieve analysis files via MCP. For CLI tasks it SHALL retrieve uploaded snapshot packages using CliRetrievalNode. RAG MUST NOT substitute analysis files and remote branch RAG SHALL be disabled for CLI tasks.

#### Scenario: Archivos del commit obtenidos via MCP
- **WHEN** the source is GitHub or Bitbucket
- **THEN** MCP obtains analysis files using the existing contract

#### Scenario: Snapshot CLI
- **WHEN** the source is CLI
- **THEN** verified uploaded files are analyzed without MCP or remote branch RAG

#### Scenario: Agente no mezcla fuentes de archivos
- **WHEN** the agent has an analysis source and an available RAG index
- **THEN** Git uses MCP as its analysis source with RAG only as background, and CLI uses its uploaded snapshot with remote RAG disabled

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

