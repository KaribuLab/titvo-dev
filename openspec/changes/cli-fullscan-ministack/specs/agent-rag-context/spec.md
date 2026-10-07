## MODIFIED Requirements
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
