## Context

`src/rag-indexer/` está listo a nivel de infraestructura: `aws/` contiene ECR, Batch, y SSM
lookup/upsert, con un `serverless.hcl` que define región, stage, cuenta, tags y nombre de servicio.
El Dockerfile produce una imagen Python 3.13 (uv) con `git` y `openssh-client`. Sin embargo, no
existe ningún pipeline: no hay `.github/workflows/`, por lo que nada desplegable llega a AWS.

El patrón de referencia es `src/mcp/git-commit-files/.github/workflows/deploy-to-aws.yml`:
autenticación por OIDC con `configure-aws-credentials` y `role-to-assume`, `terragrunt apply` sobre
`aws/ecr`, login/build/push de la imagen con tag `:${IMAGE_TAG}` (short SHA), y
`terragrunt run-all apply` sobre `aws/`. Los demás servicios usan credenciales estáticas
(`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`), patrón que se descarta en favor de OIDC.

## Goals / Non-Goals

**Goals:**
- Pipeline automático e idéntico en espíritu al de git-commit-files: OIDC + build ECR + terragrunt.
- Adaptado a Python/uv y a AWS Batch (no Lambda).
- Documentar en el README las variables de entorno y secretos requeridos.

**Non-Goals:**
- No migrar Batch a Lambda.
- No modificar la capa `aws/` (ya operativa).
- No tocar pipelines de otros subproyectos.

## Decisions

### 1. Autenticación por OIDC con rol assumable
Se usa `aws-actions/configure-aws-credentials@v4` con `role-to-assume:
${{ secrets.AWS_TITVO_BATCH_ROLE_TO_ASSUME }}` y `permissions.id-token: write`, igual que
git-commit-files.

**Por qué**: elimina credenciales de larga duración (el patrón estático de `task/trigger`), rota por
push, y centraliza permisos en un rol IAM dedicado.
**Alternativas**: credenciales estáticas como secrets (rechazadas: riesgo de vencimiento/fuga).

### 2. Tag de imagen: `:latest` + `:${IMAGE_TAG}`
El módulo `terraform-aws-batch` (v0.3.0) registra la job definition con
`image = "${var.ecr_repository_url}:latest"`. Por lo tanto el workflow DEBE push de `latest` además
del tag por SHA.

**Por qué**: sin `latest`, un apply posterior del job definition resolvería la imagen por tag
`latest` inexistente. El tag por SHA da trazabilidad y permite rollback apuntando el job definition a
un SHA específico.
**Alternativa**: hacer que el módulo batch parametrice el tag (fuera de alcance: es módulo compartido).

### 3. Orden de steps
1. Checkout (con credenciales OIDC del repo) → 2. `uv sync --frozen` con `astral-sh/setup-uv` →
3. Ruff → 4. pytest → 5. `terragrunt apply` sobre `aws/ecr` → 6. login ECR → 7. build
   (`titvo-rag-indexer` imagen, `main.py` como CMD) → 8. push `:${IMAGE_TAG}` y `:latest` →
   9. `terragrunt run-all apply` sobre `aws/`.

**Por qué**: los quality gates corren antes de tocar AWS; ECR existe antes de que el build lo necesite;
el `run-all` final despliega batch y SSM con la imagen ya subida.
**Alternativa**: aplicar todo antes del push (rechazada: la job definition quedaría apuntando a una
imagen inexistente en el primer deploy).

### 4. Variables de despliegue
| Variable | Origen | Valor |
|---|---|---|
| `AWS_REGION` | env del workflow | `us-east-2` |
| `AWS_STAGE` | env del workflow | `prod` |
| `ECR_REPOSITORY` | env del workflow | `tvo-rag-indexer-ecr-prod` |
| `IMAGE_TAG` | env del workflow | `${{ github.sha }}` |
| `AWS_TITVO_BATCH_ROLE_TO_ASSUME` | secret del repo | ARN del rol OIDC |
| `AWS_TITVO_ACCOUNT_ID` | secret del repo | cuenta (895649849416) |

`serverless.hcl` ya lee `AWS_REGION`, `AWS_STAGE` y `AWS_ACCOUNT_ID`, así que el apply de terragrunt
no requiere variables adicionales.

### 5. Lint y tests
`uv run ruff check .` y `uv run pytest` (config en `pyproject.toml`, `pythonpath = ["src"]`).

**Por qué**: replican los gates que git-commit-files corre con `npm test`.

## Risks / Trade-offs

- [Rol OIDC inexistente o sin permisos de deploy (ECR/Batch/SSM/IAM)] → Verificar antes del primer
  run que `AWS_TITVO_BATCH_ROLE_TO_ASSUME` tenga policy para `aws/*`; documentar el permiso
  mínimo en el README.
- [Secretos no creados en el repo `KaribuLab/titvo-rag-indexer`] → Listarlos en README; el workflow
  fallará con error claro si faltan.
- [Primer deploy con job definition apuntando a `latest` inexistente] → El step de push de `latest`
  ocurre antes del `run-all apply`, eliminando la ventana de imagen ausente.
- [Tag `latest` sobreescribe versiones] → Se conserva también el tag por SHA para trazabilidad y rollback.
- [Workflow del submódulo no se ejecuta] → Los repos de servicios son repos propios con su
  `.github/workflows`; el pipeline corre en `KaribuLab/titvo-rag-indexer`, no en el monorepo.