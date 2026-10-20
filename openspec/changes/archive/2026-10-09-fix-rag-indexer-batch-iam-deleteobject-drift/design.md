## Context

El `rag-indexer` (`src/rag-indexer`) corre como AWS Batch job sobre Fargate. El IAM role del job (`tvo-rag-indexer-batch-prod_job_role`) se genera dinámicamente por el módulo `terraform-aws-batch` v0.3.0 usando la `job_policy` definida en `src/rag-indexer/aws/batch/terragrunt.hcl:74-110`. Esa policy declara las acciones S3 que el job necesita:

```hcl
job_policy = jsonencode({
  ...
  "Statement" : [
    ...
    {
      "Effect" : "Allow",
      "Action" : [
        "s3:GetObject", "s3:PutObject", "s3:CopyObject",
        "s3:ListBucket", "s3:DeleteObject"
      ],
      "Resource" : [
        parameters["${base_path}/infra/s3/rag-index/bucket_arn"],
        "${parameters["${base_path}/infra/s3/rag-index/bucket_arn"]}/*"
      ]
    }
  ]
})
```

El Resource se lookuppea en cada `terragrunt apply` desde SSM `/tvo/security-scan/prod/infra/s3/rag-index/bucket_arn`, que hoy resuelve a `arn:aws:s3:::tvo-security-scan-rag-index-prod-895649849416`.

### Historia del incidente (timeline verificado contra GitHub Actions)

```
2026-06-11  IAM policy v1 creada (última versión desplegada hasta hoy)
            Acciones: Get/Put/Copy/List (no había lock feature)

2026-08-10  Workflow deploy-to-aws.yml agregado (commit f38340f)
            Runs Aug 10 02-05 (varios bumps de ssm/upsert): todos FAILURE
            Run Aug 10 02:55 (c64a6ee "re-run deploy post state cleanup"): SUCCESS
            → Algo se arregló en el cleanup; el siguiente run iba a fallar

2026-08-12  Merge del lock feature (commit 4bfe146)
            GitHub Actions run 31577944944
            08:21:15  Start
            08:21:18  Set up job
            08:21:23  Lint
            08:21:28  Test
            08:21:43  Configure AWS credentials
            08:21:44  Apply ECR
            08:22:08  Log in to ECR
            08:22:09  Build image
            08:22:22  Push image
            08:22:34  Apply Terragrunt  ← falla aquí
              08:22:59  Plan: 0 to add, 3 to change, 0 to destroy
              08:22:59  aws_iam_policy.batch: Modifying...
              08:23:00  aws_batch_job_definition: Modifications complete
              08:23:01  aws_batch_compute_environment: Modifications complete
              08:23:01  Error: iam:CreatePolicyVersion AccessDenied
                          User: karibulabs-github-actions-batch-role
                          Resource: tvo-rag-indexer-batch-prod-job-policy
              08:23:01  ssm/upsert cascade failure (depende de batch)
            08:23:04  Post-job cleanup
            Conclusion: FAILURE

2026-09-15  Hoy. IAM policy sigue en v1.
            Fullscan falla con AccessDenied en release_lock.
```

### Causa raíz

El rol OIDC `karibulabs-github-actions-batch-role` (que el workflow asume via `configure-aws-credentials@v4`) **no tiene el permiso `iam:CreatePolicyVersion`**. Sin ese permiso:

- Cambios a recursos **NO IAM** (compute environment, job definition, ECR) aplican OK — eso es lo que muestran los logs antes del error.
- Cambios a recursos **IAM** (cualquier modificación al `aws_iam_policy.batch` que requiera nueva `PolicyVersion`) fallan con 403 AccessDenied.

El `aws_iam_policy.batch` se crea con la `job_policy` del template. Cuando Terragrunt detecta un diff en el documento JSON de la policy (como agregar `s3:DeleteObject`), Terraform crea una nueva `PolicyVersion` y la marca como default — esa operación requiere `iam:CreatePolicyVersion`.

**Por qué no se detectó antes**: el `aws_iam_policy` resource de Terraform se creó originalmente en junio 2026 (v1) con permisos suficientes en ese entonces. Desde entonces, los bumps al módulo `parameter upsert` (cambios en `aws/ssm/upsert/terragrunt.hcl` que solo cambiaban el ref del módulo) no tocaban la IAM policy, así que el workflow pasaba. El primer cambio que sí tocó la `job_policy` fue el del lock feature en agosto, y ahí reventó.

**Por qué quedó silencioso durante un mes**:
1. GitHub Actions no notificó por email/Slack (la config del repo no tiene notificaciones para workflow failures, o el equipo no las había activado).
2. La imagen Docker del indexer SÍ se deploy-eaba — los pasos "Apply ECR", "Build", "Push" son los primeros del pipeline, todos pasaron. Lo único que no se aplicó fue la IAM policy.
3. El síntoma (AccessDenied en runtime al hacer `release_lock`) solo se manifiesta cuando un job real intenta usar el lock. En modo dev/local no aparece.
4. No hay test de humo post-deploy que ejecute `s3:DeleteObject` desde el Batch job para detectar el drift.

## Goals / Non-Goals

**Goals:**
- Agregar `iam:CreatePolicyVersion` al rol OIDC `karibulabs-github-actions-batch-role` (en el repo de infra compartida).
- Re-correr el workflow de deploy después del fix OIDC, para que la IAM policy del rag-indexer incluya `s3:DeleteObject`.
- Agregar verificación post-deploy al workflow que detecte el mismo patrón de fallo silencioso en el futuro: (a) IAM policy del role de Batch tiene las acciones esperadas, (b) el rol OIDC tiene `iam:CreatePolicyVersion`.
- Documentar el incidente.

**Non-Goals:**
- Aplicar `aws iam create-policy-version` local (workaround, no solución).
- Cambiar el módulo `terraform-aws-batch` upstream.
- Migrar el workflow a otra CI.
- Reemplazar el rol OIDC por uno con permisos de admin (rompe principio de least privilege).
- Re-arquitectura del sistema de permisos.
- Agregar SCPs.

## Decisions

### D1. Fix OIDC en el repo de infra compartida, no en este repo

**Decisión**: El permiso `iam:CreatePolicyVersion` se agrega en el módulo Terraform que define `karibulabs-github-actions-batch-role`. Ese módulo vive en otro repo (seguridad-scan / titvo-infra-aws). El fix se hace ahí.

**Por qué**:
- El rol OIDC es infra compartida — pertenece a donde está el módulo que lo define.
- Aplicar el permiso desde acá sería editar un IAM role que no nos pertenece via IaC, lo que deja el state de AWS desincronizado del repo de origen.
- Mantener la fuente de verdad (el módulo del rol OIDC) en un solo lugar evita drift futuro.

**Alternativas consideradas**:
- Agregar `iam:CreatePolicyVersion` como inline policy al role desde un módulo local: anti-patrón, duplica permisos entre Terraform state files.
- Asumir un rol con más permisos (AdministratorAccess) desde el workflow: ya existe en la cuenta (`AWSReservedSSO_AdministratorAccess_c1e3a728cd85abf0`) pero está reservado para humanos, no para CI. Lo correcto es least privilege.
- Usar un usuario IAM con `iam:CreatePolicyVersion` desde el workflow: descarta el patrón OIDC sin secretos estáticos.

### D2. Push trivial al workflow de este repo, JUSTIFICADO esta vez

**Decisión**: Después de que el permiso OIDC esté agregado (D1), push-eamos un commit trivial a `main` en el repo `KaribuLab/titvo-rag-indexer` para re-disparar el workflow de deploy. El commit puede ser un cambio de typo en un docstring o un bump de versión.

**Por qué esta vez SÍ es correcto**:
- El permiso OIDC es lo que cambió; el código de la app ya está bien.
- El push trivial no es "fake" — es la señal que el workflow necesita para propagar el cambio de permisos al siguiente run.
- Alternativa sería `workflow_dispatch` manual (más limpio, menos ruido en el log de GitHub), pero el workflow actual NO tiene `workflow_dispatch` habilitado. Agregarlo es un cambio extra al `.yml`.

**Alternativas consideradas**:
- Agregar `workflow_dispatch` al workflow + invocarlo manualmente desde GitHub UI: más limpio, pero requiere un cambio al workflow que NO está relacionado con el fix OIDC. Lo dejamos como follow-up.
- Re-correr el run anterior con `gh run rerun`: posible, pero el estado de Terragrunt podría no estar limpio. El push trivial es más predecible.

### D3. Verificación post-deploy con dos checks

**Decisión**: El step nuevo en `deploy-to-aws.yml` hace DOS checks:

**Check A — IAM policy del role de Batch**:
```
aws iam get-policy-version \
  --policy-arn arn:aws:iam::895649849416:policy/tvo-rag-indexer-batch-prod-job-policy \
  --version-id $(aws iam get-policy --policy-arn ... --query 'DefaultVersionId' --output text)

→ Validar que las acciones esperadas están presentes:
  s3:GetObject, s3:PutObject, s3:CopyObject, s3:ListBucket, s3:DeleteObject
→ Validar que el Resource matchea el bucket lookuppeado de SSM
```

**Check B — Capacidad del rol OIDC**:
```
aws iam simulate-custom-policy \
  --policy-arn-list arn:aws:iam::aws:policy/AWSLambdaBasicExecutionRole \
                    arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly \
  --action-names iam:CreatePolicyVersion \
  --resource-arns arn:aws:iam::895649849416:policy/tvo-rag-indexer-batch-prod-job-policy

→ Verificar que el caller (que es karibulabs-github-actions-batch-role)
  puede ejecutar iam:CreatePolicyVersion sobre la policy.
```

El check B es preventivo: aún cuando el IAM policy del role de Batch está bien deployado, queremos detectar si el rol OIDC tiene los permisos necesarios para futuros cambios. Si el check B falla, el workflow falla con mensaje claro.

**Por qué dos checks**:
- A solo detecta el síntoma actual (policy incompleta).
- B detecta la causa raíz futura (OIDC sin permiso).
- Juntos cubren el escenario completo.

**Alternativas consideradas**:
- Un solo check (A): suficiente para hoy, pero el mismo fallo silencioso puede pasar con otra policy IAM.
- `terraform plan -detailed-exitcode` en un step previo al apply: más robusto pero requiere un segundo pass del plan. Lo dejamos como follow-up.
- `driftctl`: dependencia pesada, fuera de scope.

### D4. Documentar el incidente como postmortem interno

**Decisión**: Agregar entrada en `docs/troubleshooting.md` con:
- Síntoma: AccessDenied en runtime cuando se intenta `s3:DeleteObject` desde el Batch job, mientras Get/Put/List funcionan.
- Diagnóstico: comparar template vs IAM policy desplegado, revisar GitHub Actions runs del último merge a main.
- Causa raíz típica: deploy silenciosamente fallido por permiso OIDC faltante (`iam:CreatePolicyVersion` o similar).
- Remedio: agregar el permiso al rol OIDC en el módulo de infra compartida, re-disparar workflow.
- Workaround: `aws iam create-policy-version` local, SOLO para desbloquear.

**Por qué**: el próximo fallo del mismo tipo puede pasar con cualquier IAM policy modificada por cualquier servicio. El runbook es valioso.

### D5. NO modificar el template de Terragrunt

**Decisión**: Este change NO toca `src/rag-indexer/aws/batch/terragrunt.hcl`. El template ya es correcto.

**Por qué**: el template declara `s3:DeleteObject` desde el commit `4bfe146`. Modificar el template para "forzar" un re-deploy sería trabajo doble — Terragrunt detecta drift en su propio state y re-aplica cuando hay un cambio. El problema fue que el apply falló por permisos OIDC, no por el template.

## Risks / Trade-offs

- [El fix OIDC vive en otro repo y puede tomar tiempo coordinarse] → Mitigación: la entrada en troubleshooting describe el workaround `aws iam create-policy-version` local para desbloquear YA, mientras el fix estructural se tramita en el otro repo. El fix estructural es la prioridad.
- [El push trivial genera ruido en el log de GitHub Actions] → Mitigación: usar un commit que tenga valor (ej. agregar el step de verificación post-deploy, o un fix de typo). Así el push no es fake.
- [El step de verificación agrega ~10s al workflow] → aceptable, es un solo `get-policy-version` + un `simulate-custom-policy`.
- [`iam:simulate-custom-policy` puede tener costos si se ejecuta muchas veces] → AWS lo cuenta como una llamada normal de IAM, no hay cargo extra. OK.
- [El check B no detecta TODOS los permisos faltantes — solo `iam:CreatePolicyVersion`] → alcance intencional. Si en el futuro se necesitan otros permisos (ej. `iam:DeletePolicyVersion`), se extienden los checks. No hacer over-engineering hoy.
