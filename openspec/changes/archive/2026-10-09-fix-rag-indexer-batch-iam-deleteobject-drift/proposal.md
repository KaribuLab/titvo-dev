## Why

El IAM role `tvo-rag-indexer-batch-prod_job_role` desplegado en AWS **no incluye `s3:DeleteObject`** en su policy, aunque el template de Terragrunt (`src/rag-indexer/aws/batch/terragrunt.hcl:74-110`) sí lo declara. El síntoma es `AccessDenied` durante `release_lock` en el `finally` de `IndexRepositoryUseCase.execute()`, dejando locks huérfanos en S3 (`locks/{branch}.json`).

**No es drift de Terragrunt** — es un **despliegue silenciosamente fallido**. El workflow `deploy-to-aws.yml` SÍ corrió para el merge del lock feature (commit `4bfe146`, run `31577944944`, 2026-08-12T08:21:12Z), pero falló en el step "Apply Terragrunt" con:

```
Error: updating IAM Policy (.../tvo-rag-indexer-batch-prod-job-policy):
  operation error IAM: CreatePolicyVersion, StatusCode: 403
  User: arn:aws:sts::895649849416:assumed-role/
        karibulabs-github-actions-batch-role/GitHubActions
  is not authorized to perform: iam:CreatePolicyVersion
  on resource: policy .../tvo-rag-indexer-batch-prod-job-policy
```

El rol OIDC `karibulabs-github-actions-batch-role` (que el workflow usa para autenticarse) **no tiene el permiso `iam:CreatePolicyVersion`**. Terraform detectó el diff (3 cambios en `batch`, incluyendo la IAM policy), empezó a aplicar, y AWS rechazó la operación a nivel del rol OIDC. Como `ssm/upsert` depende de `batch`, todo el run-all falló en cascada.

El run quedó en estado `failure` en GitHub Actions durante **un mes entero** sin que nadie lo revisara, porque (1) no había notificaciones configuradas, (2) el código del indexer seguía deploy-eándose como imagen Docker, así que los síntomas aparecieron solo cuando alguien disparó un fullscan y el lock cleanup empezó a fallar en runtime.

Diagnóstico verificado contra AWS real (2026-09-15, region `us-east-2`):

```
SSM /tvo/security-scan/prod/infra/s3/rag-index/bucket_arn
  = arn:aws:s3:::tvo-security-scan-rag-index-prod-895649849416   ✓ correcto

DynamoDB rag_index_bucket
  = tvo-security-scan-rag-index-prod-895649849416                 ✓ coincide con SSM

IAM policy v1 (DefaultVersion, last modified 2026-06-11)
  Actions: s3:GetObject, s3:PutObject, s3:CopyObject, s3:ListBucket
  ✗ s3:DeleteObject AUSENTE

GitHub Actions run 31577944944 (commit 4bfe146, Aug 12)
  conclusion: failure
  Failing step: Apply Terragrunt
  Root cause: karibulabs-github-actions-batch-role lacks iam:CreatePolicyVersion
```

## What Changes

- **Fix estructural (fuera de este repo)**: agregar `iam:CreatePolicyVersion` al rol OIDC `karibulabs-github-actions-batch-role` en el módulo Terraform que define ese rol (vive en otro repo de infra compartida). Sin este permiso, **cualquier futuro cambio al `job_policy` del rag-indexer va a fallar de la misma forma silenciosa**.
- **Re-correr el workflow de deploy** desde este repo después de que el permiso OIDC esté en su lugar. Aplica la nueva versión de la IAM policy con `s3:DeleteObject`.
- **Agregar verificación post-deploy** al workflow `deploy-to-aws.yml` que falle si (a) el IAM policy desplegado no incluye las acciones S3 esperadas, o (b) el rol OIDC no tiene `iam:CreatePolicyVersion`. Esto previene que el mismo fallo silencioso se repita.
- **Documentar el incidente** en `docs/troubleshooting.md` con la causa raíz (permiso OIDC faltante), cómo detectarlo, y cómo remediarlo.

## Capabilities

### Modified Capabilities

- `aws-deployment`: agregar requirement de verificación post-deploy que detecte (a) drift entre el template de Terragrunt y el IAM policy del role del Batch job, y (b) que el rol OIDC tenga `iam:CreatePolicyVersion`.

## Impact

- `src/rag-indexer/.github/workflows/deploy-to-aws.yml`: agregar step post-deploy con dos validaciones (IAM policy del role de Batch + capacidad del rol OIDC para `CreatePolicyVersion`).
- `src/rag-indexer/aws/batch/terragrunt.hcl`: SIN CAMBIOS — el template ya es correcto.
- `openspec/specs/aws-deployment/spec.md`: nuevos scenarios sobre verificación post-deploy.
- `docs/troubleshooting.md`: entrada "Deploy silenciosamente fallido por permiso OIDC faltante".
- **Cross-repo** (no commiteable desde acá): módulo de seguridad-scan / titvo-infra-aws que define `karibulabs-github-actions-batch-role`. Necesita `iam:CreatePolicyVersion` agregado al assume role policy o a una policy attachada.

## Non-goals

- Reemplazar el rol OIDC por uno con `AdministratorAccess` (ya hay un rol con esos permisos en la cuenta, pero está reservado para admins; el workflow debería usar el mínimo necesario).
- Cambiar el módulo `terraform-aws-batch` upstream.
- Migrar a otro orquestador CI.
- Aplicar el fix con `aws iam create-policy-version` manual (queda como workaround documentado en troubleshooting, NO como solución IaC).
- Re-arquitectura del sistema de permisos.
- Agregar SCPs.
