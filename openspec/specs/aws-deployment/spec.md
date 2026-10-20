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

### Requirement: Post-deploy IAM policy verification

The deploy workflow MUST verify, after `terragrunt run-all apply` completes, that the IAM policy
attached to the AWS Batch job role contains the S3 actions declared in the Terragrunt template AND
that the OIDC role assumed by the workflow has the IAM permissions required to update that policy
on future deploys. The verification MUST fail the workflow with a clear error if any check fails.

#### Scenario: IAM policy contains all required S3 actions

- **WHEN** the `Apply Terragrunt` step of `deploy-to-aws.yml` completes successfully
- **THEN** a follow-up step reads the `DefaultVersionId` of the IAM policy attached to
  `tvo-rag-indexer-batch-${stage}_job_role` and verifies that the document includes all of:
  `s3:GetObject`, `s3:PutObject`, `s3:CopyObject`, `s3:ListBucket`, `s3:DeleteObject`
  in at least one Allow statement whose Resource matches the bucket ARN from
  `/tvo/security-scan/${stage}/infra/s3/rag-index/bucket_arn`

#### Scenario: Workflow fails when a required action is missing

- **WHEN** the Terragrunt apply completes but the IAM policy does NOT include one of the required
  actions (for example, `s3:DeleteObject` is absent because a previous deploy silently failed)
- **THEN** the verification step exits with non-zero status, the workflow fails, and the operator
  sees a clear error indicating which action is missing and on which bucket

#### Scenario: Workflow fails when Resource does not match the deployed bucket

- **WHEN** the IAM policy contains all required actions but the Resource ARNs do NOT include the
  bucket lookupped from SSM `/tvo/security-scan/${stage}/infra/s3/rag-index/bucket_arn`
- **THEN** the verification step exits with non-zero status and the workflow fails

#### Scenario: Workflow detects missing OIDC permissions for future IAM updates

- **WHEN** the verification step runs after a successful apply
- **THEN** it MUST also call `aws iam simulate-custom-policy` with the assumed OIDC role
  (`karibulabs-github-actions-batch-role`) as the caller and `iam:CreatePolicyVersion` as the
  action against the IAM policy ARN
- **AND** if the simulation returns `denied`, the workflow fails with a clear message explaining
  that the OIDC role lacks `iam:CreatePolicyVersion` and the fix must be applied in the
  shared-infrastructure repository that defines the role

#### Scenario: Verification step is non-disruptive on a healthy deploy

- **WHEN** the IAM policy is already in sync with the template AND the OIDC role has
  `iam:CreatePolicyVersion` (drift-free state)
- **THEN** the verification step completes in under 15 seconds and the workflow exits successfully
  without affecting downstream steps
