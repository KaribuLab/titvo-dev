## Why

`src/rag-indexer/` no tiene pipeline de despliegue: no existe `.github/workflows/`, por lo que la
infraestructura Terragrunt (`aws/`) y la imagen Docker nunca se despliegan a AWS de forma
automatizada. `src/mcp/git-commit-files/` ya resuelve esto con un workflow de GitHub Actions que
autentica por OIDC, construye y sube la imagen a ECR, y aplica Terragrunt. Se requiere replicar esa
misma lógica de despliegue en rag-indexer para que su rollout sea igual de confiable y seguro.

## What Changes

- Agregar `.github/workflows/deploy-to-aws.yml` en `src/rag-indexer/` inspirado en el de
  `git-commit-files`, adaptado al stack Python (`uv`) y al cómputo AWS Batch:
  - Autenticación por **OIDC** con `aws-actions/configure-aws-credentials@v4`
    (`role-to-assume` + `id-token: write`), reemplazando el uso de credenciales estáticas.
  - Checkout del repo (submódulo), instalación con `uv sync --frozen`, lint con Ruff y test con pytest.
  - `terragrunt apply` sobre `aws/ecr`, login a ECR, build y push de la imagen.
  - Push con tag `:latest` **y** `:${IMAGE_TAG}` porque `terraform-aws-batch` fija la definición de
    job a `${ecr_repository_url}:latest`.
  - `terragrunt run-all apply` sobre `aws/` para el resto de unidades (batch, ssm upsert/lookup).
- Documentar en `src/rag-indexer/README.md` las variables de entorno y secretos requeridos para el
  despliegue.

## Capabilities

### New Capabilities
- `aws-deployment`: Pipeline automatizado de despliegue a AWS por OIDC para rag-indexer (build,
  push a ECR, apply Terragrunt), equivalente al de git-commit-files.

### Modified Capabilities
<!-- Sin cambios de requirements sobre capacidades ya trackeadas en openspec/specs/. -->

## Impact

- `src/rag-indexer/.github/workflows/deploy-to-aws.yml` — nuevo workflow de deploy.
- `src/rag-indexer/README.md` — sección de despliegue con variables/secretos.
- Repositorio GitHub `KaribuLab/titvo-rag-indexer`: requiere crear los secretos de repo
  `AWS_TITVO_BATCH_ROLE_TO_ASSUME` y `AWS_TITVO_ACCOUNT_ID`, y que exista el rol OIDC con
  permisos para `aws/*` (ECR, Batch, SSM, IAM).
- Sin cambios de infraestructura: `aws/` ya está correcta (batch, ecr, ssm lookup/upsert).

## Non-Goals

- NO migrar AWS Batch a AWS Lambda (el cómputo sigue siendo Batch).
- NO crear ni alterar la infraestructura `aws/` existente.
- NO tocar pipelines de otros servicios (git-commit-files, task/trigger, etc.).
- NO implementar CDK/LocalStack para rag-indexer.