## ADDED Requirements
### Requirement: Fuente CLI alternativa
The workflow SHALL accept a CLI retrieval node producing the same files envelope as MCP retrieval. CLI scans SHALL use uploaded files without Git or branch RAG.
#### Scenario: CLI fullscan
- **WHEN** a CLI source is supplied
- **THEN** experts receive verified uploaded content and no Git tool is invoked
### Requirement: Contexto estable por lote
Experts SHALL partition formatted files into bounded messages without reducing a file budget due to scan size. Parse and invocation failures SHALL preserve other batch findings and report incomplete coverage.
#### Scenario: Lote falla
- **WHEN** one batch fails
- **THEN** successful findings remain and the scan cannot be COMPLETED
### Requirement: Consolidación conservadora con trazabilidad
Consolidation SHALL operate within one file in bounded groups and account for every input ID. Missing inputs SHALL be retained; invalid outputs SHALL fall back to originals.
#### Scenario: Hallazgo omitido
- **WHEN** a model output does not represent one input
- **THEN** that input remains in the final report
### Requirement: Recuperación acotada de hallazgos inválidos
Experts SHALL normalize unambiguous relative-path and numeric-line representations. Rejected finding objects SHALL receive at most one correction request per batch, within a bounded input and context budget. Already-valid findings SHALL remain unchanged. Every corrected finding SHALL account for its original source ID; unresolved, omitted or unsupported records SHALL keep coverage incomplete.
#### Scenario: Campo faltante corregido
- **WHEN** a model returns one valid finding and one finding with missing required fields
- **THEN** the agent retains the valid finding and attempts correction of the rejected record only
#### Scenario: Corrección incompleta
- **WHEN** a correction omits a rejected source ID or changes existing evidence
- **THEN** the batch remains incomplete and other valid findings remain in the report
### Requirement: Diagnóstico de validación por lote
Coverage metadata SHALL record 1-based batch numbers, rejection reasons and repair outcome without persisting rejected raw response text.
#### Scenario: Rechazo persistente
- **WHEN** a finding cannot be repaired
- **THEN** the report explains its validation reason instead of showing only an invalid-finding count
