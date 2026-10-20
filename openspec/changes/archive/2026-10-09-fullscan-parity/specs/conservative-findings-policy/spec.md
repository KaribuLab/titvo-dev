## MODIFIED Requirements

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
