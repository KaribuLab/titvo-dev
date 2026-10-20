## ADDED Requirements

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
`TITVO_EXPERT_MAX_CONCURRENCY`). Provider errors SHALL be retried up to 3 times with exponential
backoff. Results SHALL be assembled in batch index order regardless of completion order.

#### Scenario: Completion order does not affect output

- **WHEN** batch 2 completes before batch 0
- **THEN** the expert's issue list is ordered by batch index, then by the order returned within each
  batch

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
