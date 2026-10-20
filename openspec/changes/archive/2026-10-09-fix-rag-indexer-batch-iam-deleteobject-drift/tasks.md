## 1. Diagnóstico (verificado contra GitHub Actions)

- [x] 1.1 Listar runs del workflow `deploy-to-aws.yml` en `KaribuLab/titvo-rag-indexer` con `gh run list --workflow deploy-to-aws.yml --limit 15 --json databaseId,conclusion,createdAt,headSha`.
- [x] 1.2 Identificar el run que corresponde al commit `4bfe146` (lock feature): run `31577944944`, conclusion `failure`, 2026-08-12T08:21:12Z.
- [x] 1.3 Leer logs del run con `gh run view 31577944944 --log` y aislar el step "Apply Terragrunt".
- [x] 1.4 Confirmar el error específico: `iam:CreatePolicyVersion AccessDenied` por el rol OIDC `karibulabs-github-actions-batch-role`.
- [x] 1.5 Verificar que todos los demás runs desde 2026-08-10 también son `failure`, excepto `c64a6ee "ci: re-run deploy post state cleanup"` que pasó. Patrón: deploys fallan silenciosamente desde que se agregó el workflow.
- [x] 1.6 Documentar el timeline del incidente para el change (con timestamps UTC y referencias a run IDs).

## 2. Fix OIDC en el repo de infra compartida

- [x] 2.1 Localizar el módulo Terraform que define `karibulabs-github-actions-batch-role` (probablemente en el repo de seguridad-scan / titvo-infra-aws, fuera de este repo).
- [x] 2.2 Agregar `iam:CreatePolicyVersion` al rol: ya sea como statement adicional en el assume role policy, o como una policy attachada separada.
- [x] 2.3 Considerar agregar también `iam:DeletePolicyVersion` y `iam:SetDefaultPolicyVersion` si Terragrunt los usa (Terraform cleanup de versiones viejas). Verificar con `terraform plan` después de la próxima apply.
- [x] 2.4 Hacer el PR, esperar review, mergear, y validar que el apply de ese repo pasa.
- [x] 2.5 Validar el fix corriendo `aws iam simulate-custom-policy --action-names iam:CreatePolicyVersion --policy-arn-list <arn-de-las-policies-del-role>` con el rol OIDC como caller. Debe retornar `allowed`.

## 3. Re-aplicar el workflow de este repo

- [x] 3.1 Después de que el fix OIDC esté mergeado y aplicado, push trivial a `main` en `KaribuLab/titvo-rag-indexer`. El push trivial debe ser un cambio real con valor (ej. el step de verificación post-deploy del task 4, o un fix de typo).
- [x] 3.2 Monitorear el run en GitHub Actions. Esta vez el step "Apply Terragrunt" debe completar sin el error de `iam:CreatePolicyVersion`.
- [x] 3.3 Validar post-apply con `aws iam get-policy --policy-arn arn:aws:iam::895649849416:policy/tvo-rag-indexer-batch-prod-job-policy --region us-east-2` que `DefaultVersionId` ahora es `v2` (o superior).
- [x] 3.4 Validar `v2` con `aws iam get-policy-version` que ahora incluye `s3:DeleteObject` en las Actions.
- [x] 3.5 Disparar un fullscan de prueba y confirmar que `release_lock` retorna 200 sin `AccessDenied`.

## 4. Agregar verificación post-deploy al workflow

- [x] 4.1 Editar `src/rag-indexer/.github/workflows/deploy-to-aws.yml` para agregar un step nuevo después de "Apply Terragrunt".
- [x] 4.2 Implementar Check A (validación del IAM policy del role de Batch):
  - Obtener el ARN del role y el ARN de la policy attachada.
  - Leer la `DefaultVersionId`.
  - Parsear el documento JSON.
  - Validar presencia de `s3:GetObject`, `s3:PutObject`, `s3:CopyObject`, `s3:ListBucket`, `s3:DeleteObject` en statements Allow.
  - Validar que el Resource matchea el bucket lookuppeado de SSM `/tvo/security-scan/${stage}/infra/s3/rag-index/bucket_arn`.
- [x] 4.3 Implementar Check B (capacidad del rol OIDC):
  - Usar `aws iam simulate-custom-policy` para verificar que el caller del workflow puede ejecutar `iam:CreatePolicyVersion` sobre la IAM policy del role de Batch.
  - Si la simulación retorna `denied`, el workflow falla con mensaje claro: "El rol OIDC karibulabs-github-actions-batch-role no tiene iam:CreatePolicyVersion. Aplicar fix en el repo de infra compartida antes de mergear."
- [x] 4.4 Hacer que el step falle con exit code != 0 si alguno de los dos checks falla.

## 5. Actualizar el spec `aws-deployment`

- [x] 5.1 Agregar al archivo `openspec/specs/aws-deployment/spec.md` un nuevo requirement "Post-deploy IAM policy verification" con scenarios que cubran:
  - El workflow valida el IAM policy del role del Batch job después del apply.
  - El workflow valida que el rol OIDC puede ejecutar `iam:CreatePolicyVersion` sobre la policy.
  - El workflow falla si falta alguna acción S3 crítica (Get/Put/Copy/List/Delete).
  - El workflow falla si el Resource del Allow no incluye el bucket lookuppeado de SSM.
  - El workflow falla con mensaje claro si el rol OIDC no tiene permisos suficientes para futuras actualizaciones de IAM policies.

## 6. Documentación

- [ ] 6.1 Agregar entrada en `docs/troubleshooting.md` titulada "Deploy silenciosamente fallido por permiso OIDC faltante" con:
  - Síntoma: AccessDenied en runtime sobre una acción IAM específica (ej. `s3:DeleteObject`) mientras el resto funciona.
  - Diagnóstico: comparar el template de Terragrunt contra `aws iam get-policy-version`, revisar GitHub Actions runs del último merge.
  - Causa raíz típica: workflow corrió pero falló en el apply de IAM, sin notificación.
  - Cómo verificar el rol OIDC: `aws iam simulate-custom-policy --action-names iam:CreatePolicyVersion`.
  - Remedio: agregar el permiso al rol OIDC en el repo de infra compartida, re-disparar workflow.
  - Workaround manual: `aws iam create-policy-version` con el JSON correcto (SOLO para desbloquear, no para quedarse).
- [ ] 6.2 Considerar agregar notificaciones de GitHub Actions para workflow failures (Slack, email, etc.) si el repo no las tiene. Esto es un follow-up de proceso, no parte del fix.

## 7. Cleanup

- [ ] 7.1 Si se usó `aws iam create-policy-version` manual como workaround temporal, eliminar esa policy version manual después de que el apply de Terragrunt cree su propia versión. Mantener solo las versiones managed-by-Terragrunt.
- [x] 7.2 Confirmar que el workflow de deploy se ejecuta limpio en el próximo push a `main` sin necesidad de workaround.
- [x] 7.3 Confirmar que el check A y el check B pasan en un deploy limpio.
