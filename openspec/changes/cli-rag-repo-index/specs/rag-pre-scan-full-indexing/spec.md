## REMOVED Requirements

### Requirement: CLI no indexa Git
**Reason**: Reemplazado por indexación snapshot-scoped CLI (`cli-rag-indexing`) desde S3, sin Git.
**Migration**: Scans `source=cli` disparan el job CLI del indexer y esperan `cli/latest/` antes del grafo.

## ADDED Requirements

### Requirement: Pre-scan CLI indexa desde snapshot
Para tasks `source=cli`, antes del grafo LangGraph el agente SHALL disparar (si hace falta) un job de indexación CLI con `batch_id` y `repository_url`, y hacer polling bloqueante hasta éxito, fallo o timeout. SHALL NOT enviar `TITVO_REPO_URL` solo como señal de clon Git para ese job.

#### Scenario: CLI sin índice o inventory distinto
- **WHEN** la task es CLI y el índice `cli/latest` falta o el job debe aplicar el manifest del batch
- **THEN** el agente envía un job CLI al indexer y espera su terminación antes de analizar

#### Scenario: CLI no usa Git en el trigger
- **WHEN** el agente dispara indexación para una task CLI
- **THEN** el entorno del job identifica origen CLI y `batch_id` para leer S3 temp, no un full Git por SSH

## MODIFIED Requirements

### Requirement: Timeout RAG configurado exclusivamente en tabla
Para scans Git y CLI, el agente SHALL leer `rag_indexing_timeout_seconds` de la tabla al iniciar el scan y mantener el presupuesto para sus esperas de indexación. Si falta o está vacío/solo espacios, SHALL usar 600 segundos y registrar el default. Un valor no vacío SHALL ser un número finito positivo de segundos, validado antes de enviar jobs. No SHALL existir override por variable de entorno.

#### Scenario: Valor válido
- **WHEN** la tabla contiene `parameter_id=rag_indexing_timeout_seconds` y `value="1800"`
- **THEN** cada espera bloqueante de ese scan utiliza 1800 segundos

#### Scenario: Valor decimal válido
- **WHEN** el valor es `" 2.5 "`
- **THEN** se interpreta como 2.5 segundos

#### Scenario: Parámetro ausente o vacío en configuración antigua
- **WHEN** falta el parámetro o contiene vacío o solo espacios
- **THEN** el scan utiliza 600 segundos por job y registra que usó el default

#### Scenario: Parámetro no vacío inválido
- **WHEN** el parámetro contiene texto no numérico, cero, negativo, NaN o infinito
- **THEN** el scan falla con un error de configuración que identifica la clave antes de enviar cualquier job de indexación

#### Scenario: Error al leer la tabla
- **WHEN** no se puede leer la configuración
- **THEN** el error se propaga sin sustituir el timeout por un valor local

#### Scenario: Cambio operativo sin despliegue
- **WHEN** se modifica el valor en la tabla entre dos scans
- **THEN** el siguiente scan utiliza el nuevo valor sin recompilar ni cambiar el entorno
- **AND** un scan ya iniciado conserva el valor leído

#### Scenario: Variable de entorno no sustituye la tabla
- **WHEN** existe una variable de entorno de timeout RAG con un valor distinto
- **THEN** el agente utiliza únicamente el valor válido de la tabla

#### Scenario: Snapshot CLI no requiere timeout RAG
- **WHEN** se inicia una tarea CLI
- **THEN** el agente lee y valida `rag_indexing_timeout_seconds` igual que en scans Git y aplica ese presupuesto a la espera del job de indexación CLI
