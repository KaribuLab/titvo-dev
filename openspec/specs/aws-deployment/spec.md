# aws-deployment Specification

## Purpose

Pipeline de despliegue continuo a AWS (ECR + Batch + SSM) para el servicio rag-indexer, ejecutado desde GitHub Actions con autenticacion OIDC y Terragrunt.

## Requirements

### Requirement: Deploy pipeline via OIDC
The rag-indexer repository MUST provide a GitHub Actions workflow at
`.github/workflows/deploy-to-aws.yml` that deploys the service to AWS using OIDC authentication
(`aws-actions/configure-aws-credentials@v4` with `role-to-assume`), never static access keys.

#### Scenario: Workflow exists in repository
- **WHEN** inspecting `src/rag-indexer/.github/workflows/`
- **THEN** a `deploy-to-aws.yml` workflow exists

#### Scenario: Authentication uses OIDC
- **WHEN** the workflow configures AWS credentials
- **THEN** it uses `configure-aws-credentials` with a `role-to-assume` secret and the job declares
  `permissions.id-token: write`

### Requirement: Build, push, and deploy
The workflow MUST build the Docker image, push it to ECR, and apply Terragrunt so the AWS resources
in `aws/` reflect the repository state on every push to `main`.

#### Scenario: Full deploy on push to main
- **WHEN** a push reaches the `main` branch
- **THEN** the image is built and pushed to `aws/ecr`'s repository with neither the `:latest` tag nor
  the short-SHA tag missing, and Terragrunt applies over `aws/`

#### Scenario: Image tag matches Batch job definition
- **WHEN** the job definition (`terraform-aws-batch`) is registered
- **THEN** it points to `${ecr_repository_url}:latest` so a `latest` image tag MUST always be pushed
  before apply

### Requirement: Test and lint before deploy
The workflow MUST run the Python quality gates (Ruff lint and pytest) before applying infrastructure.

#### Scenario: Failing quality gates stop the deploy
- **WHEN** lint or tests fail
- **THEN** the workflow fails before any AWS resource is applied

### Requirement: Environment and secrets documented
The repository README MUST document the environment variables and GitHub repository secrets needed
to deploy.

#### Scenario: README lists deploy inputs
- **WHEN** reading `src/rag-indexer/README.md`
- **THEN** it lists the required secrets (`AWS_TITVO_BATCH_ROLE_TO_ASSUME`,
  `AWS_TITVO_ACCOUNT_ID`) and the workflow environment (`AWS_REGION`, `AWS_STAGE`, `ECR_REPOSITORY`,
  `IMAGE_TAG`)
