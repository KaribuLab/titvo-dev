## ADDED Requirements

### Requirement: BatchService Python soporta submit y status de jobs
El módulo `rag_indexer_trigger.batch_service` SHALL exponer una clase `BatchService` con métodos `submit_job` y `get_job_status`.

#### Scenario: Submit job en modo localstack via HTTP
- **WHEN** `AWS_STAGE == "localstack"` y se llama `submit_job` con las variables de entorno requeridas
- **THEN** se hace un POST HTTP al batch-runner con `imageName: "titvo/rag-indexer"` y se retorna el `jobId`

#### Scenario: Submit job en modo AWS Batch
- **WHEN** `AWS_STAGE != "localstack"` y se llama `submit_job`
- **THEN** se invoca `boto3.client("batch").submit_job` con el job definition y queue configurados y se retorna el `jobId`

#### Scenario: Get job status en modo localstack
- **WHEN** `AWS_STAGE == "localstack"` y se llama `get_job_status(job_id)`
- **THEN** se hace un POST HTTP al batch-runner en `/get-job-status` y se retorna el status del job

#### Scenario: Get job status en modo AWS Batch
- **WHEN** `AWS_STAGE != "localstack"` y se llama `get_job_status(job_id)`
- **THEN** se invoca `boto3.client("batch").describe_jobs` y se retorna el status del job

### Requirement: Factory function crea BatchService según el entorno
La función `create_batch_service(aws_stage, batch_runner_url)` SHALL retornar un `BatchService` configurado según el entorno.

#### Scenario: Factory en localstack
- **WHEN** `aws_stage == "localstack"`
- **THEN** retorna `BatchService` configurado para usar el batch-runner HTTP en `batch_runner_url` o `http://batch-runner:3001`

#### Scenario: Factory en AWS
- **WHEN** `aws_stage != "localstack"`
- **THEN** retorna `BatchService` configurado con cliente boto3 de AWS Batch

### Requirement: RagIndexerBatchTrigger expone trigger_full y trigger_delta
El servicio `RagIndexerBatchTrigger` SHALL exponer:
- `trigger_full(repo_url, branch) -> str` — dispara indexación completa y retorna jobId.
- `trigger_delta(repo_url, branch, commit_sha) -> str` — dispara indexación delta y retorna jobId.

Las variables de entorno del job SHALL incluir `TITVO_REPO_URL`, `TITVO_BRANCH` y opcionalmente `TITVO_COMMIT_SHA` (solo en delta).

#### Scenario: trigger_full lanza job sin commit_sha
- **WHEN** se llama `trigger_full("https://github.com/org/repo", "main")`
- **THEN** el job se lanza con `TITVO_REPO_URL` y `TITVO_BRANCH` pero SIN `TITVO_COMMIT_SHA`

#### Scenario: trigger_delta lanza job con commit_sha
- **WHEN** se llama `trigger_delta("https://github.com/org/repo", "main", "abc123")`
- **THEN** el job se lanza con `TITVO_REPO_URL`, `TITVO_BRANCH` y `TITVO_COMMIT_SHA=abc123`
