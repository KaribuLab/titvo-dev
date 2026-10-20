# conservative-findings-policy Specification

## Purpose

Política conservadora de hallazgos: los expertos solo reportan CRITICAL/HIGH con evidencia explícita, degradan lo incierto a sospechas, excluyen falsos positivos conocidos, escriben en español neutro y el merge deduplica sin perder hallazgos ni fusionar archivos distintos.

## Requirements

### Requirement: Findings merger service en dominio conserva política ante conflictos

El servicio **`FindingsMerger`** en **`domain/services/findings_merger.py`** SHALL deduplicar por
**`(path, line, category, code normalizado)`** y ante la misma clave desde distintos expertos SHALL
conservar la **severidad mayor** y registrar los expertos fusionados en `metadata.merged_from`.
Esta es la política L1 usada por el nodo `merge` del grafo.

#### Scenario: Conflict de severidad en el servicio de dominio

- **WHEN** se agrega un segundo **`ExpertResult`** con la misma clave deduplicadora y una severidad
  distinta
- **THEN** la entrada almacenada refleja la severidad mayor según orden CRITICAL > HIGH > MEDIUM > LOW
  y `metadata.merged_from` contiene ambos expertos

#### Scenario: Misma ubicación con evidencia distinta no se fusiona

- **WHEN** dos expertos reportan el mismo `path`, `line` y `category` pero con `code` distinto
- **THEN** ambas entradas se conservan tras L1

### Requirement: CRITICAL and HIGH severity require explicit evidence

All experts SHALL classify findings as CRITICAL or HIGH only when the vulnerability is confirmed,
exploitable with the code as written, and backed by concrete evidence visible in the retrieved file
contents. What counts as "exposed" depends on the file runtime: in `server`, `infra` and `config`
runtimes a reference to an environment variable or CI secret by name is not evidence; in `browser`
and `mobile` runtimes any value present in the code, including environment references resolved at
build time, is exposed.

#### Scenario: Variable name is not a vulnerability

- **WHEN** code contains a variable named `apiKey` or `password` without an actual secret value and
  without an exposed build-time environment reference
- **THEN** no expert reports it as CRITICAL or HIGH

#### Scenario: Environment variable reference in server code is not a leak

- **WHEN** a `server` file references `os.environ["SECRET_KEY"]` or `process.env.API_KEY`
- **THEN** no expert reports it as CRITICAL or HIGH

#### Scenario: Build-time environment reference in browser code is exposed

- **WHEN** a `browser` file sends `import.meta.env.VITE_API_TOKEN` as its only API credential
- **THEN** the relevant expert reports it as a client-side exposed credential

#### Scenario: Confirmed hardcoded secret

- **WHEN** code contains a visible hardcoded signing key, cloud credential or backend API secret
- **THEN** the relevant expert reports it as CRITICAL with the evidence snippet

### Requirement: Uncertain findings are downgraded

When an expert lacks sufficient context to confirm exploitability, it SHALL still report the
finding as a suspicion: title prefixed `Sospecha:`, severity MEDIUM at most (enforced in code),
description ending with `Para confirmar:` and the concrete check. It MUST NOT escalate uncertain
findings to CRITICAL or HIGH and MUST NOT omit them.

#### Scenario: Missing external configuration context

- **WHEN** a potential vulnerability depends on external configuration not visible in the code
- **THEN** the expert reports it as `Sospecha:` with severity MEDIUM at most and names what to verify

#### Scenario: Suspicions are never dropped

- **WHEN** an expert identifies a risk it cannot confirm
- **THEN** the risk appears in the output as a suspicion instead of being omitted

### Requirement: Findings are deduplicated conservatively on merge

The merge pathway SHALL deduplicate in two levels. L1 SHALL be deterministic by
`(path, line, category, normalized code)`, retaining the highest severity. L2 SHALL only merge
findings that describe the same root cause **within the same file**; when in doubt the model MUST
keep findings separate. Findings in different files MUST NOT be merged into one. No input finding
MAY disappear from the output unless it is listed in the `source_ids` of a consolidated issue.

#### Scenario: Distinct findings at same location

- **WHEN** two experts report different categories at the same path and line
- **THEN** both issues are retained after L1 and L2

#### Scenario: Same secret in several files stays per file

- **WHEN** the same hardcoded secret is reported in `a.ts` and `b.ts`
- **THEN** the final output contains one issue for `a.ts` and one for `b.ts`

#### Scenario: Consolidation prompt is conservative and accountable

- **WHEN** the L2 consolidation prompt is rendered
- **THEN** it instructs the model to merge only same-root-cause findings in the same file, to keep
  findings separate when uncertain, to return `source_ids` per issue, and it does not contain the
  instruction to consolidate aggressively

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
