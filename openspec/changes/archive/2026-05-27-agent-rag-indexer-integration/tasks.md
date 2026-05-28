## 1. Propagación de branch en trigger API (TypeScript)

- [x] 1.1 Añadir campo `branch` a `TaskArgs` y `TaskEntity` en `trigger/src/core/task/task.entity.ts`
- [x] 1.2 Actualizar `GithubStrategy.handle()` para leer `github_branch` del payload y validarlo como requerido; incluir `branch` en los args retornados
- [x] 1.3 Actualizar `BitbucketStrategy.handle()` para leer `bitbucket_branch` del payload y validarlo como requerido; incluir `branch` en los args retornados
- [x] 1.4 Actualizar `CliStrategy.handle()` para leer `branch` del payload y validarlo como requerido; incluir `branch` en los args retornados
- [x] 1.5 Actualizar `TriggerTaskUseCase.execute()` en `task.service.ts` para agregar `TITVO_BRANCH` a las environment variables del batch job. En AWS, las vars de infraestructura RAG provienen del job definition (Terraform). En **localstack**, el trigger las pasa explícitamente (`TITVO_RAG_INDEXER_BUCKET`, `TITVO_BATCH_RUNNER_URL`) dentro del bloque `if (AWS_STAGE === 'localstack')` porque el batch-runner no implementa job definitions.
- [x] 1.6 Corregir `batch.service.ts` para usar `networkMode: 'titvo-dev_localstack'` (Docker Compose agrega el prefijo del directorio al nombre de la red). Esto asegura que el contenedor del agente esté en la misma red Docker que el servicio `rag-indexer`.
- [x] 1.7 Actualizar `DynamoTaskRepository.save()` en `src/infrastructure/task/task.dynamo.ts` para persistir el campo `branch` como atributo top-level del item
- [x] 1.8 Actualizar `DynamoTaskRepository.getById()` para mapear el campo `branch` del item al `TaskEntity`

## 2. Lectura de branch en el agente (Python)

- [x] 2.1 Añadir propiedad `branch` al dataclass `Task` en `task_entity.py`; leer desde `args['branch']` como campo opcional (retorna `None` si no está presente)
- [x] 2.2 Actualizar `DynamoTaskRepository.get_task()` en `dynamo_task_repository.py` para mapear el campo `branch` del item al `Task` entity
- [x] 2.3 Verificar que el campo `branch` se propaga correctamente en tests unitarios del repositorio _(verificado vía E2E localstack: `branch='main'` en logs de `DynamoTaskRepository`; sin infra pytest en el agente)_

## 3. BatchService Python para rag-indexer

- [x] 3.1 Crear módulo `src/agent/src/rag_indexer_trigger/` con `__init__.py`
- [x] 3.2 Implementar `batch_service.py` con clase `BatchService`, métodos `submit_job(job_name, job_queue, job_definition, environment) -> str` y `get_job_status(job_id) -> JobStatus`; soporte HTTP (localstack) y boto3 (AWS Batch)
- [x] 3.3 Implementar `create_batch_service(aws_stage, batch_runner_url) -> BatchService` factory siguiendo el patrón de `batch.service.ts`; agregar logging del hostname usado al invocar el batch-runner (`LOGGER.info` con la URL y hostname extraído)
- [x] 3.4 Implementar `rag_indexer_batch_trigger.py` con clase `RagIndexerBatchTrigger`, métodos `trigger_full(repo_url, branch) -> str` y `trigger_delta(repo_url, branch, commit_sha) -> str`. Vars dinámicas (`TITVO_REPO_URL`, `TITVO_BRANCH`, `TITVO_COMMIT_SHA`) se pasan siempre. Vars de infraestructura (`TITVO_DYNAMO_CONFIGURATION_TABLE_NAME`, `TITVO_ENCRYPTION_KEY_NAME`, `TITVO_LOG_LEVEL`, `AWS_STAGE`, `AWS_ENDPOINT`) solo cuando `aws_stage == 'localstack'`, ya que en AWS las provee el job definition de Terraform.
- [x] 3.5 Revisar y verificar qué variables de entorno necesita el contenedor del rag-indexer (comparar con las que ya pasa el trigger para el agente) y asegurarse de pasarlas todas en `RagIndexerBatchTrigger`

## 4. Port IRagIndexStatusPort y adaptador S3

- [x] 4.1 Crear port `IRagIndexStatusPort` en `src/agent/src/code_analysis/domain/ports/rag_index_status_port.py` con método abstracto `is_indexed(repository_url: str, branch: str) -> bool`
- [x] 4.2 Implementar adaptador `S3RagIndexStatusAdapter` en `src/agent/src/code_analysis/infra/adapters/s3_rag_index_status_adapter.py` que consulta `{bucket}/{repo_slug}/{branch}/latest/meta.json` en S3 usando boto3
- [x] 4.3 Añadir configuración `rag_indexer_bucket` al `configuration_provider` del agente (leer desde DynamoDB config igual que los otros secrets)
- [x] 4.4 Leer el nombre del bucket RAG desde la variable de entorno `TITVO_RAG_INDEXER_BUCKET`; lanzar excepción al iniciar si no está configurada (ver grupo 9 para el wiring Terraform)

## 5. Pre-scan: verificación e indexación full bloqueante

- [x] 5.1 Añadir `rag_index_status_port: IRagIndexStatusPort` y `rag_indexer_trigger: RagIndexerBatchTrigger` como dependencias al constructor de `AnalyseCodeUseCase`
- [x] 5.2 Implementar método privado `_ensure_rag_index(repo_url, branch)` en `AnalyseCodeUseCase` que: verifica si está indexado, si no dispara indexación full, hace polling con `asyncio.sleep(10)` hasta 60 intentos; lanza excepción si el job falla o se supera el timeout
- [x] 5.3 Al inicio de `execute()`, validar que `task.branch` no es None/vacío (lanzar excepción si falta) y luego llamar `await self._ensure_rag_index(task.repository_url, task.branch)` antes de `self.agent.invoke()`
- [x] 5.4 Actualizar el wiring en `main.py` del agente para inyectar `S3RagIndexStatusAdapter` y `RagIndexerBatchTrigger` en el use case

## 6. Post-scan: trigger delta fire-and-forget

- [x] 6.1 Implementar método privado `_trigger_delta_indexing(repo_url, branch, commit_hash)` en `AnalyseCodeUseCase` que llama `trigger_delta` sin await del resultado del job (fire-and-forget) con manejo de excepciones que solo loguea (error en delta no interrumpe el resultado ya obtenido)
- [x] 6.2 Llamar `self._trigger_delta_indexing(task.repository_url, task.branch, task.commit_hash)` después de que `agent_response` es obtenido (branch siempre disponible en este punto gracias a la validación en 5.3)
- [x] 6.3 Extender `IRagIndexStatusPort` con método `is_commit_indexed(repository_url, branch, commit_sha) -> bool`
- [x] 6.4 Implementar `is_commit_indexed` en `S3RagIndexStatusAdapter`: verificar existencia de `{repo_slug}/branches/{branch}/{commit_sha}/meta.json` via `head_object`
- [x] 6.5 Actualizar `_trigger_delta_indexing` para llamar `is_commit_indexed` antes de `trigger_delta`; si retorna `True`, loguear y omitir el trigger; si `is_commit_indexed` falla, loguear error y omitir el trigger (fail-safe)

## 7. Prompt del agente: contexto RAG

- [x] 7.1 Actualizar `content_template.md` o `system_prompt.md` del agente para incluir una sección opcional sobre el índice de código base: "El código base de la rama `{branch}` está indexado como contexto de fondo. Los archivos del commit a analizar se obtienen via las herramientas MCP disponibles."
- [x] 7.2 Ajustar el `AgentMessage` en `analyse_code_use_case.py` para incluir el campo `branch` y el estado de indexación en el contenido del mensaje cuando corresponda

## 8. Infraestructura AWS — rag-indexer (Batch; ECS eliminado)

- [x] 8.1 Crear `src/rag-indexer/aws/batch/terragrunt.hcl` usando el módulo `terraform-aws-batch`; policy con ARNs exactos (sin wildcards): `dynamodb:GetItem` → ARN desde SSM lookup, `secretsmanager:GetSecretValue` → ARN desde SSM lookup (`{base_path}/infra/secret/manager/arn`), `s3:*` → ARN desde SSM lookup (`{base_path}/infra/s3/rag-index/bucket_arn`; publicado por módulo S3 dedicado)
- [x] 8.2 Actualizar `src/rag-indexer/aws/ssm/upsert/terragrunt.hcl`: dependencia `batch`, paths SSM `batch/rag-indexer/*` (job_definition_arn, job_definition_name, job_queue_arn, job_queue_name, security_group_id). El `ssm/upsert` **no publica** los parámetros del bucket S3 RAG.
- [x] 8.3 El bucket RAG es publicado en SSM por un módulo S3 dedicado (externo a este change). Paths: `{base_path}/infra/s3/rag-code/bucket_arn` y `{base_path}/infra/s3/rag-code/bucket_name`. El `ssm/upsert` del rag-indexer no los publica.
- [x] 8.4 Eliminar `aws/ecs/terragrunt.hcl` del rag-indexer. El único modo de despliegue es Batch.

## 9. Infraestructura AWS — agent (permisos para invocar rag-indexer)

- [x] 9.1 Añadir mock_outputs en `dependency parameters` de `src/agent/aws/batch/terragrunt.hcl` para: `batch/rag-indexer/job_definition_name`, `batch/rag-indexer/job_queue_name`, `batch/rag-indexer/job_definition_arn`, `batch/rag-indexer/job_queue_arn`, `s3/rag-code/bucket_name`, `s3/rag-code/bucket_arn`.
- [x] 9.2 Añadir a `job_environment` en `src/agent/aws/batch/terragrunt.hcl`: `TITVO_RAG_INDEXER_JOB_DEFINITION` (SSM `batch/rag-indexer/job_definition_name`), `TITVO_RAG_INDEXER_JOB_QUEUE` (SSM `batch/rag-indexer/job_queue_name`), `TITVO_RAG_INDEXER_BUCKET` (SSM `s3/rag-code/bucket_name`). No son pasadas por el trigger.
- [x] 9.3 Añadir a `job_policy`: `batch:SubmitJob` → ARNs exactos desde SSM; `batch:DescribeJobs` → `"*"`; `secretsmanager:GetSecretValue` → ARN desde SSM sin wildcards.
- [x] 9.4 Añadir a `job_policy` el permiso `s3:GetObject + s3:ListBucket` sobre el bucket RAG usando el ARN desde SSM lookup (`s3/rag-code/bucket_arn`).

## 10. CDK localstack — trigger API

- [x] 10.1 Agregar `ragIndexerBucket` y `batchRunnerUrl` a `AppStackProps` en `cdklocal/lib/app-stack.ts`. `ragIndexerJobQueue` y `ragIndexerJobDefinition` **no son necesarios en localstack** (el batch-runner no los usa).
- [x] 10.2 Declarar `TITVO_RAG_INDEXER_BUCKET` y `TITVO_BATCH_RUNNER_URL` en el `environment` de la Lambda en `app-stack.ts`.
- [x] 10.3 Pasar los nuevos props en `cdklocal/bin/app.ts`: `ragIndexerBucket` desde SSM (`s3/rag-code/bucket_name`) y `batchRunnerUrl` desde `process.env.BATCH_RUNNER_URL` (default `http://rag-indexer:3002`). **Nota:** El trigger usa `agent:3001` para lanzar el agente; el agente usa `rag-indexer:3002` (recibido vía `TITVO_BATCH_RUNNER_URL`) para lanzar el rag-indexer.
- [x] 10.4 Actualizar `create_rag_indexer_batch_trigger()` en `rag_indexer_batch_trigger.py`: validar `TITVO_RAG_INDEXER_JOB_QUEUE` y `TITVO_RAG_INDEXER_JOB_DEFINITION` solo si `aws_stage != 'localstack'`; en localstack usar strings vacíos (el batch-runner los ignora).

## 11. Documentación y verificación local

- [x] 11.1 Documentar las variables de entorno del agente: `TITVO_BRANCH` (pasada por el trigger), `TITVO_RAG_INDEXER_JOB_QUEUE`, `TITVO_RAG_INDEXER_JOB_DEFINITION`, `TITVO_RAG_INDEXER_BUCKET` (provistas por el job definition Terraform vía SSM lookup en AWS; en localstack el trigger las pasa vía CDK + `task.service.ts`), `TITVO_BATCH_RUNNER_URL` (solo localstack).
- [x] 11.2 Verificar el flujo end-to-end en localstack: trigger con `branch`, scan que dispara full indexing, polling, análisis, delta fire-and-forget _(verificado 2026-05-28: indexación full en `main`, análisis completado, reporte e issue generados)_
- [x] 11.3 Verificar que el `batch-runner` local acepta `imageName: "titvo/rag-indexer"` y que el contenedor `titvo-rag-indexer-local` se lanza correctamente _(verificado 2026-05-28: contenedor rag-indexer indexó 911 chunks y subió artefactos a S3)_
- [x] 11.4 Usar `/find-docs` para verificar la API actualizada de `@aws-sdk/client-batch` y `boto3.client("batch")` antes de implementar el BatchService
