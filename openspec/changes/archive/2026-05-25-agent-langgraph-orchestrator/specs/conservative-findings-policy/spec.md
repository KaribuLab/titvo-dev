## ADDED Requirements

### Requirement: Findings merger service en dominio conserva política ante conflictos

El servicio **`FindingsMerger`** en **`domain/services/findings_merger.py`** deduplica por **`(path, line, category)`** y ante la misma clave desde distintos expertos debe conservar la **severidad menor** (política conservadora).

#### Scenario: Conflict de severidad en el servicio de dominio

- **WHEN** se agrega un segundo **`ExpertResult`** con la misma clave deduplicadora y una severidad distinta
- **THEN** la entrada almacenada refleja la severidad menor según orden CRITICAL > HIGH > MEDIUM > LOW

_Nota_: el **nodo** **`merge`** del grafo puede deduplicar por primera aparición sin invocar aún ese merge por severidad; la alineación con esta política queda como mejora futura opcional.

### Requirement: CRITICAL and HIGH severity require explicit evidence

All experts SHALL classify findings as CRITICAL or HIGH only when the vulnerability is confirmed, exploitable with the code as written, and backed by concrete evidence visible in the retrieved file contents.

#### Scenario: Variable name is not a vulnerability

- **WHEN** code contains a variable named `apiKey` or `password` without an actual secret value
- **THEN** no expert reports it as CRITICAL or HIGH

#### Scenario: Environment variable reference is not a leak

- **WHEN** code references `os.environ["SECRET_KEY"]` or `process.env.API_KEY`
- **THEN** no expert reports it as CRITICAL or HIGH

#### Scenario: Confirmed hardcoded secret

- **WHEN** code contains a visible hardcoded API key or password value
- **THEN** the relevant expert reports it as CRITICAL with the evidence snippet

### Requirement: Uncertain findings are downgraded

When an expert lacks sufficient context to confirm exploitability, it SHALL classify the finding as MEDIUM or LOW. It MUST NOT escalate uncertain findings to CRITICAL or HIGH.

#### Scenario: Missing external configuration context

- **WHEN** a potential vulnerability depends on external configuration not visible in the code
- **THEN** the expert classifies it as MEDIUM at most

### Requirement: Findings are deduplicated conservatively on merge

The merge pathway SHALL deduplicate issues by `(path, line, category)`. Prefer retaining the lower severity when the same logical issue is aggregated from multiple experts (see domain `FindingsMerger` intent).

#### Scenario: Distinct findings at same location

- **WHEN** two experts report different categories at the same path and line
- **THEN** both issues SHOULD be retained in the merged result

### Requirement: Descriptions are written in neutral Spanish

All issue descriptions, summaries, and recommendations SHALL be written in neutral Spanish.

#### Scenario: Issue text language

- **WHEN** any expert reports a finding
- **THEN** the `description`, `summary`, and `recommendation` fields are in neutral Spanish

### Requirement: False positive exclusion rules are enforced

Experts SHALL NOT flag the following as vulnerabilities: HTTPS/TLS usage, generic crypto usage without specific misuse, storage configuration without confirmed exposed secrets, and outdated dependencies without known CVE evidence in the code.

#### Scenario: HTTPS not flagged

- **WHEN** code uses HTTPS for data transmission
- **THEN** no expert reports it as a vulnerability

#### Scenario: Generic hashing not flagged

- **WHEN** code uses standard hashing or encoding without misuse
- **THEN** no expert reports it as CRITICAL or HIGH
