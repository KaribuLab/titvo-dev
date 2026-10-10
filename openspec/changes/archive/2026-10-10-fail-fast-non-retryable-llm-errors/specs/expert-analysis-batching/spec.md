## MODIFIED Requirements

### Requirement: Batches run concurrently under a bounded semaphore with retries

Batches SHALL run concurrently under a shared concurrency limit (default 4,
`TITVO_EXPERT_MAX_CONCURRENCY`). Provider errors SHALL be classified before retrying:

- **Retryable** (rate limit 429 without quota/billing cause, 5xx, timeouts, connection errors,
  unknown errors): retried up to 3 times with exponential backoff.
- **Batch-fatal** (400 whose body indicates `context_length_exceeded` or a content filter): the
  batch fails immediately without retry and without affecting other batches.
- **Provider-fatal** (401, 402, 403, 404, any other 400, or 429 whose body or message indicates
  `insufficient_quota`, `credit_balance_exhausted`, billing or exhausted credit balance): the batch
  fails immediately without retry and opens the shared circuit breaker.

Results SHALL be assembled in batch index order regardless of completion order.

#### Scenario: Completion order does not affect output

- **WHEN** batch 2 completes before batch 0
- **THEN** the expert's issue list is ordered by batch index, then by the order returned within each
  batch

#### Scenario: Rate limit is retried

- **WHEN** a batch receives a 429 whose body has no quota or billing code
- **THEN** the batch is retried with backoff up to 3 attempts

#### Scenario: Exhausted credits are not retried

- **WHEN** a batch receives a 429 with `code: credit_balance_exhausted`
- **THEN** the batch fails after exactly one attempt and no backoff sleep occurs

#### Scenario: Context length error fails only its batch

- **WHEN** a batch receives a 400 with `code: context_length_exceeded`
- **THEN** that batch is recorded as failed after one attempt and the other batches of the same
  expert still run

## ADDED Requirements

### Requirement: A provider-fatal error opens a scan-wide circuit breaker

All expert nodes of a workflow SHALL share one circuit breaker. When any batch of any expert hits a
provider-fatal error, the breaker SHALL open with that error as its reason, and exactly one `ERROR`
log line SHALL be emitted. While the breaker is open, every batch that has not yet called the
provider SHALL be aborted without calling it: it SHALL be recorded in `failed_batches` with its
`paths` and `error = "aborted: <reason>"`, and SHALL NOT produce a per-batch warning log. Each
expert SHALL log one summary line with the number of aborted batches, and SHALL emit
`provider_error = <reason>` in its state delta. The breaker SHALL be reset at the start of every
workflow invocation.

#### Scenario: Remaining batches are aborted

- **WHEN** an expert has 98 batches and batch 0 fails with `credit_balance_exhausted`
- **THEN** the provider is called at most `max_concurrency` more times, every remaining batch
  appears in `failed_batches` with `error` starting with `aborted:`, and the node returns within
  seconds

#### Scenario: Breaker is shared across experts

- **WHEN** `code_vulnerabilities` opens the breaker
- **THEN** `owasp_web` batches that have not started abort without calling the provider and
  `owasp_web` emits `provider_error` with the same reason

#### Scenario: Breaker does not leak between scans

- **WHEN** a scan opened the breaker and a new workflow invocation starts
- **THEN** the first batch of the new scan calls the provider
