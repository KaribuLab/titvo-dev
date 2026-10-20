# scan-completeness Specification

## Purpose

Reporte explícito de análisis incompletos: cuando algún lote de expertos falla, el resultado final, el `ResultDto`, el resultado persistido de la tarea y el reporte HTML declaran qué archivos no fueron analizados completamente y el estado nunca se reporta como `COMPLETED`.
## Requirements
### Requirement: A scan with failed batches reports itself as incomplete

When `state.failed_batches` is non-empty, the `merge` node SHALL add to `final_output` an
`incomplete` object with `failed_batches` (each with `expert`, `batch_index`, `paths`, `error`),
`files_not_fully_analyzed` (sorted unique paths) and a Spanish `message` of the form
"Análisis incompleto: X de Y lotes fallaron; N archivos sin analizar completamente". The `status`
MUST NOT be `COMPLETED` when `incomplete` is present.

When `state.provider_error` is set, `final_output.status` SHALL be `FAILED` and
`final_output.error` SHALL be `"Proveedor LLM no disponible: <provider_error>"`, regardless of the
issues found. In that case the `merge` node SHALL NOT call the model for L2 consolidation and SHALL
keep the L1 findings.

#### Scenario: Incomplete scan without issues becomes WARNING

- **WHEN** no issues were found, one batch failed and `provider_error` is not set
- **THEN** `final_output.status` is `WARNING` and `final_output.incomplete.files_not_fully_analyzed`
  lists that batch's paths

#### Scenario: Incomplete scan with HIGH issues stays FAILED

- **WHEN** a HIGH issue was found and one batch failed
- **THEN** `final_output.status` is `FAILED` and `final_output.incomplete` is present

#### Scenario: Complete scan has no incomplete field

- **WHEN** every batch succeeded
- **THEN** `final_output` has no `incomplete` key

#### Scenario: Provider unavailable is FAILED with explicit error

- **WHEN** `provider_error` is `"429 insufficient_quota: You have no credits remaining"` and no
  issues were found
- **THEN** `final_output.status` is `FAILED`, `final_output.error` starts with
  `"Proveedor LLM no disponible:"` and `final_output.incomplete` lists every aborted batch's paths

#### Scenario: Provider unavailable skips L2 consolidation

- **WHEN** `provider_error` is set and two experts reported findings on the same file before the
  breaker opened
- **THEN** the model is not invoked by `merge` and both L1 findings are present in `final_output`

### Requirement: ResultDto tolerates error and incomplete fields

`ResultDto` SHALL declare optional fields `error: str | None` and `incomplete: dict | None` with
default `None`, so `AnalyseCodeUseCase` can build it from any `final_output` produced by `merge`,
including the MCP failure case that emits `error`.

#### Scenario: MCP failure result is persisted instead of crashing

- **WHEN** `final_output` is `{"status": "FAILED", "scaned_files": 0, "issues": [],
  "error": "No files in commit"}`
- **THEN** the use case builds `ResultDto` without raising and marks the task `FAILED` with that
  result

### Requirement: The HTML report shows an incomplete-analysis banner

`LambdaReportRepository.create_report` SHALL include `incomplete` in the payload when present. The
`issue-report` lambda SHALL accept an optional `incomplete` field and, when present, SHALL render a
banner at the top of the report with `incomplete.message` and the list of
`files_not_fully_analyzed`. Without the field the report SHALL render exactly as today.

#### Scenario: Banner rendered

- **WHEN** the report lambda receives `incomplete` with 2 paths
- **THEN** the HTML contains the message and both paths before the findings table

#### Scenario: No banner for complete scans

- **WHEN** the report lambda receives a payload without `incomplete`
- **THEN** the HTML has no incomplete banner

### Requirement: Task result keeps the incomplete details

The task result persisted by `AnalyseCodeUseCase` SHALL keep the `incomplete` object as returned
by the agent so it is visible through the task status API.

#### Scenario: Incomplete stored in task result

- **WHEN** the agent returns `incomplete`
- **THEN** `task.result["incomplete"]` equals the agent's `incomplete` object


### Requirement: A FAILED scan caused by an infrastructure error produces no report or notification

When `ResultDto.error` is set (the `merge` node emitted `error` because of `provider_error`,
`mcp_error` or zero scanned files), `NotificationService.send_notifications` SHALL NOT call the
report repository nor publish Bitbucket Code Insights or a GitHub issue, SHALL return an empty
result (no `report_url`), and SHALL log an `ERROR` with the cause and the number of
`files_not_fully_analyzed`. A `FAILED` result without `error` (CRITICAL/HIGH findings) SHALL keep
generating the HTML report and notifications as today.

`AnalyseCodeUseCase` SHALL log, when marking the task `FAILED`, the `error` cause, the
`incomplete.message` with its files, and each entry of `coverage.errors`.

The agent process SHALL exit with code 1 when the persisted task is `ERROR` or `FAILED` with
`result.error`, and with code 0 otherwise. The exit code SHALL be computed after the task has been
persisted, so the status API (which only consults AWS Batch while the task is `PENDING` or
`IN_PROGRESS`) observes the same `FAILED` status and `result` regardless of the job's exit code.

#### Scenario: Provider unavailable skips the report

- **WHEN** `send_notifications` receives `status=FAILED`,
  `error="Proveedor LLM no disponible: 429 credit_balance_exhausted"` and `incomplete` with 2 files
- **THEN** `create_report` is not called, no Code Insights or GitHub issue is published, the result
  is `{}` and an `ERROR` log contains the cause and `files_not_fully_analyzed=2`

#### Scenario: FAILED by findings still reports

- **WHEN** `send_notifications` receives `status=FAILED` with no `error`
- **THEN** the HTML report is created and the source notification is published as today

#### Scenario: Infrastructure failure exits with code 1

- **WHEN** the persisted task is `FAILED` with `result.error` set, or `ERROR`
- **THEN** `exit_code_for_task` returns 1 and `main` exits with that code after logging the cause

#### Scenario: Scan with findings exits with code 0

- **WHEN** the persisted task is `FAILED` because of CRITICAL/HIGH findings (no `result.error`),
  `WARNING` or `COMPLETED`
- **THEN** `exit_code_for_task` returns 0
