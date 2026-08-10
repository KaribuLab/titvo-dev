## 1. Pipeline de despliegue

- [x] 1.1 Crear `src/rag-indexer/.github/workflows/deploy-to-aws.yml` con trigger `push` a `main` y
      `permissions.id-token: write`.
- [x] 1.2 Configurar autenticación OIDC con `aws-actions/configure-aws-credentials@v4`
      (`role-to-assume: ${{ secrets.AWS_TITVO_BATCH_ROLE_TO_ASSUME }}`).
- [x] 1.3 Agregar step de checkout y setup de Python/uv (`astral-sh/setup-uv` + `uv sync --frozen`).
- [x] 1.4 Agregar quality gates: `uv run ruff check .` y `uv run pytest`.

## 2. Build y push a ECR

- [x] 2.1 Aplicar primero `terragrunt apply` sobre `aws/ecr` (con `AWS_ACCOUNT_ID` desde secrets).
- [x] 2.2 Login a ECR con `aws-actions/amazon-ecr-login@v2`.
- [x] 2.3 Build de la imagen (`docker build --tag "${{ env.ECR_REGISTRY }}/${ECR_REPOSITORY}:${IMAGE_TAG}" .`).
- [x] 2.4 Push con tag `:${IMAGE_TAG}` y tag `:latest` (requerido por `terraform-aws-batch`), usando
      `ECR_REGISTRY` del step de login.

## 3. Apply de infraestructura

- [x] 3.1 Ejecutar `terragrunt run-all apply --terragrunt-non-interactive -auto-approve` sobre `aws/`
      con `gruntwork-io/terragrunt-action@v2` (tf 1.9.8, tg 0.69.1).
- [x] 3.2 Verificar que `serverless.hcl` no requiera variables extra (monta `AWS_REGION`, `AWS_STAGE`,
      `AWS_ACCOUNT_ID` automáticamente desde get_env).

## 4. Validación

- [x] 4.1 Ejecutar lint y tests localmente (`uv run ruff check .`, `uv run pytest`) en
      `src/rag-indexer`.
- [x] 4.2 Construir la imagen localmente (`docker build -t titvo/rag-indexer .`) y confirmar que
      `python main.py` es el CMD válido.
- [x] 4.3 Simular el workflow con `act` (si está disponible) o validar dry-run de terragrunt
      (`terragrunt run-all plan` con el rol OIDC mockeado).

## 5. Documentación

- [x] 5.1 Actualizar `src/rag-indexer/README.md` con la sección de despliegue: secretos requeridos
      (`AWS_TITVO_BATCH_ROLE_TO_ASSUME`, `AWS_TITVO_ACCOUNT_ID`) y variables del workflow
      (`AWS_REGION`, `AWS_STAGE`, `ECR_REPOSITORY`, `IMAGE_TAG`).
- [x] 5.2 Actualizar `docs/rag-indexer.md` y/o `docs/dev-env-structure.md` si corresponde, describiendo
      el flujo OIDC de deploy y los prerequisitos del rol IAM.