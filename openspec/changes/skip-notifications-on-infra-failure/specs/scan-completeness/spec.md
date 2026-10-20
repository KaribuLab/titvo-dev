## ADDED Requirements

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
