## MODIFIED Requirements

### Requirement: El agente usa los archivos del commit exclusivamente via MCP
For Git tasks the agent SHALL retrieve analysis files via MCP. For CLI tasks it SHALL retrieve uploaded snapshot packages using CliRetrievalNode and SHALL limit analysis focus to `focus_files` from `scan-manifest.json` when that list is non-empty; when `focus_files` is empty the agent SHALL analyze the analyzable paths from the snapshot inventory. RAG MUST NOT substitute analysis files. Remote branch RAG (`branches/`) SHALL remain disabled for CLI; CLI MAY use the repo CLI index under `cli/latest/` as background context only.

#### Scenario: Archivos del commit obtenidos via MCP
- **WHEN** the source is GitHub or Bitbucket
- **THEN** MCP obtains analysis files using the existing contract

#### Scenario: Snapshot CLI
- **WHEN** the source is CLI
- **THEN** verified uploaded files are analyzed without MCP; remote branch RAG stays disabled; CLI repo RAG under `cli/latest/` MAY be used as background only

#### Scenario: Snapshot CLI con focus
- **WHEN** the source is CLI and `focus_files` is non-empty
- **THEN** the agent analyzes those focus paths from the verified snapshot (deletions may lack file content) without MCP and without remote branch RAG

#### Scenario: Snapshot CLI scope full
- **WHEN** the source is CLI and `focus_files` is empty
- **THEN** the agent analyzes analyzable snapshot paths and MAY use `cli/latest/` RAG as background only

#### Scenario: Agente no mezcla fuentes de archivos
- **WHEN** the agent has an analysis source and an available RAG index
- **THEN** Git uses MCP as analysis source with branch RAG as background; CLI uses the uploaded snapshot/`focus_files` as analysis source with CLI repo RAG as background only

## ADDED Requirements

### Requirement: Prompt CLI distingue focus e índice cli/latest
Para tasks CLI el prompt SHALL indicar que el foco de análisis viene del snapshot/`focus_files` y que el índice vectorial, si existe, representa el corpus CLI del repositorio en `cli/latest/`, no una rama Git remota.

#### Scenario: Prompt CLI con índice
- **WHEN** existe `cli/latest/` para el repo de la task CLI
- **THEN** el mensaje de usuario menciona contexto RAG del índice CLI del repositorio

#### Scenario: Prompt CLI sin índice
- **WHEN** no hay índice CLI disponible
- **THEN** el análisis procede solo con el snapshot/focus sin sección de contexto RAG de rama remota
