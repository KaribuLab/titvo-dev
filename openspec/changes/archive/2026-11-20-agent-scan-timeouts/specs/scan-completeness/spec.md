## ADDED Requirements

### Requirement: Every scan has a per-request and a global deadline

`LangchainAgentModelFactory` SHALL build every chat client (`ChatOpenAI`, `ChatAnthropic`,
`ChatGoogleGenerativeAI`) with a request `timeout` of `ai_request_timeout_seconds` (default 180),
so no provider call can block forever. `LangGraphAgent` SHALL bound the whole workflow with
`scan_timeout_seconds` (default 3000); when it elapses the workflow SHALL be cancelled and the scan
SHALL end as `FAILED` with an `error` naming `scan_timeout_seconds` and the `task_id`, which then
skips the report and notifications and exits with code 1. Both values SHALL be read from the
configuration table; a blank value uses the default and a non-positive or non-numeric value SHALL
abort the start of the scan.

#### Scenario: Provider call stalls

- **WHEN** the provider does not answer a batch within `ai_request_timeout_seconds`
- **THEN** the SDK raises a timeout, the expert classifies it as `RETRY` and retries with backoff,
  and the batch is recorded as failed if every attempt times out

#### Scenario: Scan exceeds the global deadline

- **WHEN** the workflow is still running after `scan_timeout_seconds`
- **THEN** the workflow task is cancelled and the result is `status=FAILED`,
  `error="Scan aborted: the workflow exceeded scan_timeout_seconds=<N> (task_id=<id>)"`,
  `coverage.complete=false`

#### Scenario: Deadlines come from the configuration table

- **WHEN** `scan_timeout_seconds` is missing or blank
- **THEN** 3000 is used and logged as the default; a value such as `0` or `abc` raises a
  `ValueError` before the scan starts
