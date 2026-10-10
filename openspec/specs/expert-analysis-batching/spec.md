# expert-analysis-batching Specification

## Purpose

Envío completo del contenido de los archivos a los expertos sin truncado: división de archivos grandes en chunks solapados, partición determinista en lotes acotados, ejecución concurrente con reintentos, registro de lotes fallidos y trazabilidad del origen de cada hallazgo.
## Requirements
### Requirement: Files are never truncated; large files are split into overlapping chunks

Each file selected by an expert SHALL be sent to the LLM in full. A file whose content is at most
`per_file_cap` characters (default 30 000, `TITVO_EXPERT_FILE_CAP_CHARS`) SHALL be a single chunk.
A larger file SHALL be split at line boundaries into chunks of at most `per_file_cap` characters
with an overlap of `overlap_chars` (default 5 000, `TITVO_EXPERT_CHUNK_OVERLAP_CHARS`) between
consecutive chunks. Every chunk after the first SHALL be prefixed with the structural lines
(imports, function and class signatures) of the whole file, capped at 60 lines; the prefix MUST
NOT shift reported line numbers. The content a file contributes MUST NOT depend on how many other
files are in the scan.

#### Scenario: Same file, same chunks in commit and full scan

- **WHEN** a 12 000-character file is analyzed in a 3-file commit scan and in a 400-file full scan
- **THEN** the chunk content sent to the LLM for that file is byte-identical in both scans

#### Scenario: Large file is fully covered

- **WHEN** a file has 80 000 characters
- **THEN** it produces 3 chunks, every line of the file appears in at least one chunk, and
  consecutive chunks share about 5 000 characters

#### Scenario: Line numbers are mapped back to the file

- **WHEN** the LLM reports `line: 40` for a chunk whose `start_line` is 601
- **THEN** the resulting issue has `line: 640`

### Requirement: Chunks are partitioned into bounded, deterministic batches

Each expert SHALL sort its chunks by `(primary runtime, path, chunk_index)` and partition them
greedily into batches whose summed sizes do not exceed `batch_budget` (default 200 000,
`TITVO_EXPERT_BATCH_BUDGET_CHARS`). A chunk MUST NOT be split across batches. The expert SHALL
perform exactly one LLM call per batch.

#### Scenario: Small commit produces a single batch

- **WHEN** an expert selects 3 files totalling 40 000 characters
- **THEN** it performs exactly one LLM call

#### Scenario: Large full scan produces multiple batches

- **WHEN** an expert selects chunks totalling 1 400 000 characters
- **THEN** it performs 7 LLM calls and every batch is at most 200 000 characters

#### Scenario: Partitioning is deterministic

- **WHEN** the same file list is partitioned twice
- **THEN** the batches have identical membership and order

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

### Requirement: A failed batch is recorded, not swallowed

When a batch exhausts its retries, the expert SHALL keep the issues of the other batches, append
`"<expert>: batch <i> failed: <error>"` to `expert_errors`, and append
`{"expert", "batch_index", "paths", "error"}` to `state.failed_batches`. An unparsable LLM response
for a batch SHALL be treated the same way.

#### Scenario: One failing batch does not drop the others

- **WHEN** one of 5 batches fails after retries
- **THEN** issues from the 4 other batches are returned and `failed_batches` has one entry listing
  that batch's paths

### Requirement: Every issue records its origin

Each `ExpertIssue` SHALL carry `metadata.expert`, `metadata.batch_index` and
`metadata.chunk_index`.

#### Scenario: Issue metadata populated

- **WHEN** `owasp_api` reports an issue from its second batch on a single-chunk file
- **THEN** the issue metadata is `{"expert": "owasp_api", "batch_index": 1, "chunk_index": 0}`

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

