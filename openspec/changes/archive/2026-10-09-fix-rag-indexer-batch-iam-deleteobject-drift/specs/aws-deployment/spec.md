## ADDED Requirements

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
