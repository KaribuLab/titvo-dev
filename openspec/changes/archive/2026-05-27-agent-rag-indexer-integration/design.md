## Context

El agente ejecuta su análisis de seguridad sobre los archivos del commit actual (obtenidos via MCP). El rag-indexer ya puede indexar un repositorio completo por rama o solo el delta de un commit. Sin embargo, no existe ningún puente entre ambos: el agente no sabe si hay un índice disponible para la rama que está analizando, y el trigger API no propaga el campo `branch` que el rag-indexer necesita.

El `batch.service.ts` de TypeScript ya resuelve el problema de lanzar jobs en AWS Batch y en entorno local (via HTTP al batch-runner). El agente en Python necesita la misma capacidad para invocar el rag-indexer.

## Goals / Non-Goals

**Goals:**
- Propagar `branch` desde el trigger API hasta el agente.
- Guardar `branch` como campo de primer nivel en la tabla DynamoDB de scans.
- Implementar `BatchService` en Python para el agente con soporte local y AWS Batch.
- En el agente, antes del grafo: verificar índice, hacer indexación full bloqueante si falta.
- En el agente, después del grafo: disparar indexación delta fire-and-forget.
- Instruir al agente para usar el índice vectorial como contexto de fondo.

**Non-Goals:**
- No se modifica la lógica interna del rag-indexer (chunking, embedding, delta).
- No se agrega autenticación nueva para el vector store.
- No se crea endpoint de consulta del índice RAG en la API pública.
- No se hace rollback del índice ante fallos de indexación.

## Decisions

### D1 — `branch` viaja como campo de `args` en el batch job y como campo top-level en DynamoDB

**Alternativas:**
- (A) Solo dentro de `args` del task entity — sencillo, sin migración de esquema.
- (B) Campo top-level `branch` en DynamoDB + en `task.entity.ts` / `Task` Python — más explícito, fácil de consultar.

**Decisión: B.** El campo `branch` es un atributo de primer orden del scan (similar a `source` o `status`), no un detalle del SCM. Facilita su consumo en el agente sin parsear `args`. DynamoDB no requiere migración de esquema por ser schemaless; solo se actualiza el TS entity, el adaptador DynamoDB y el Python task entity.

### D2 — Variables dinámicas vs variables de infraestructura en el batch job del agente

El trigger pasa al batch job **únicamente variables dinámicas** (valores que cambian por invocación):
- `TITVO_SCAN_TASK_ID` — ID único del scan.
- `TITVO_BRANCH` — rama a analizar (sigue el mismo patrón).

Las variables de infraestructura (valores estáticos que vienen de la configuración del entorno) son **parte de la definición del job Batch** en Terraform, NO se pasan en la invocación **en AWS**:
- `TITVO_RAG_INDEXER_JOB_DEFINITION`, `TITVO_RAG_INDEXER_JOB_QUEUE`, `TITVO_RAG_INDEXER_BUCKET` → declarados en `job_environment` de `src/agent/aws/batch/terragrunt.hcl`, leyendo sus valores desde SSM Parameter Store (lookup).

**Excepción localstack (aplica en ambos saltos: trigger → agente y agente → rag-indexer):** El batch-runner local inicia contenedores Docker directamente y no implementa el concepto de job definition de Terraform. Por lo tanto, en modo `localstack`:
- El **trigger** pasa explícitamente al agente: `TITVO_RAG_INDEXER_BUCKET` y `TITVO_BATCH_RUNNER_URL` (bloque `if AWS_STAGE === 'localstack'`). `TITVO_RAG_INDEXER_JOB_QUEUE` y `TITVO_RAG_INDEXER_JOB_DEFINITION` **no se pasan en localstack** porque el batch-runner no los usa (inicia el contenedor directamente sin job definitions).
- El **agente** pasa explícitamente al rag-indexer las vars de infraestructura: `TITVO_DYNAMO_CONFIGURATION_TABLE_NAME`, `TITVO_ENCRYPTION_KEY_NAME`, `TITVO_LOG_LEVEL`, `AWS_STAGE`, `AWS_ENDPOINT` (bloque `if aws_stage == 'localstack'` en `_build_environment()`).

Para que el trigger disponga de estas vars en localstack, el CDK del trigger (`cdklocal/lib/app-stack.ts`) declara en el `environment` de la Lambda: `TITVO_RAG_INDEXER_BUCKET` (desde SSM `s3/rag-code/bucket_name`) y `TITVO_BATCH_RUNNER_URL` (desde `process.env.BATCH_RUNNER_URL`, default `http://rag-indexer:3002`). Las vars de job (`TITVO_RAG_INDEXER_JOB_QUEUE`, `TITVO_RAG_INDEXER_JOB_DEFINITION`) **no se necesitan en localstack** y solo se validan en `create_rag_indexer_batch_trigger()` cuando `aws_stage != 'localstack'`.

**Topología de batch-runners en localstack:** El docker-compose define dos servicios batch-runner separados:
- `agent` (puerto 3001) — usado por el **trigger** para iniciar el contenedor del **agente**.
- `rag-indexer` (puerto 3002) — usado por el **agente** para iniciar el contenedor del **rag-indexer**.

Por lo tanto:
- El trigger usa `http://agent:3001` para lanzar el agente.
- El trigger pasa al agente `TITVO_BATCH_RUNNER_URL=http://rag-indexer:3002` para que el agente pueda lanzar el rag-indexer.

**Red Docker:** Todos los servicios (incluyendo `agent`, `rag-indexer`) deben estar en la misma red Docker (`titvo-dev_localstack` — Docker Compose agrega el prefijo del directorio) para que el DNS funcione correctamente entre contenedores. El `batch.service.ts` usa `networkMode: 'titvo-dev_localstack'` al lanzar el contenedor del agente.

En AWS, cada servicio solo pasa vars dinámicas al siguiente; las de infraestructura provienen del job definition de Terraform.

El agente lee `TITVO_BRANCH` del entorno y también desde el campo `branch` del task entity en DynamoDB (consistencia doble).

Cada strategy añade el campo `branch` al `TaskArgs` retornado:
- `GithubStrategy`: leer `github_branch` del payload.
- `BitbucketStrategy`: leer `bitbucket_branch` del payload.
- `CliStrategy`: leer `branch` del payload (obligatorio).

### D3 — `BatchService` Python en `src/agent/src/rag_indexer_trigger/`

Se crea un módulo `rag_indexer_trigger` con:
- `batch_service.py`: clase `BatchService` con métodos `submit_job` y `get_job_status`.
  - Modo local: HTTP POST al batch-runner (igual que TS, contenedor `titvo-rag-indexer-local`, imagen `titvo/rag-indexer`).
  - Modo AWS: `boto3.client('batch').submit_job` + `describe_jobs`.
- `rag_indexer_batch_trigger.py`: servicio de alto nivel con `trigger_full(repo_url, branch)` y `trigger_delta(repo_url, branch, commit_sha)`.
  - Variables de entorno: `TITVO_RAG_INDEXER_JOB_QUEUE`, `TITVO_RAG_INDEXER_JOB_DEFINITION`, `TITVO_BATCH_RUNNER_URL` (solo local).

Factory `create_batch_service(aws_stage: str, batch_runner_url: str | None) -> BatchService` detecta el modo igual que el TS.

### D4 — Verificación del índice en el agente via nuevo port `IRagIndexStatusPort`

El agente necesita saber si existe un índice S3 para `(repo_url, branch)`. 

**Alternativas:**
- (A) Importar `S3ArtifactStoreAdapter` del rag-indexer directamente — acoplamiento entre subproyectos.
- (B) Replicar la lógica S3 con un boto3 call directo en el adaptador del agente — más simple, sin dependencia.
- (C) Nuevo port `IRagIndexStatusPort` con adaptador que usa boto3 S3 — sigue el patrón hexagonal del proyecto.

**Decisión: C.** Puerto `IRagIndexStatusPort` con métodos `is_indexed(repo_url, branch) -> bool` (pre-scan) e `is_commit_indexed(repo_url, branch, commit_sha) -> bool` (post-scan delta idempotente). Adaptador `S3RagIndexStatusAdapter` lee los mismos paths que usa el rag-indexer. El bucket se lee desde `TITVO_RAG_INDEXER_BUCKET`.

### D5 — Pre-scan bloqueante fuera del grafo LangGraph

La lógica de pre-indexación no es agéntica (es determinista y no requiere LLM). Se implementa en `analyse_code_use_case.py` ANTES de invocar `self.agent.invoke()`:

```
1. validar que task.branch no es None → raise si falta
2. check_rag_index(repo_url, branch)
3. si no indexado → batch_service.submit_full_index(repo_url, branch) → poll hasta SUCCEEDED/FAILED
4. si falla o timeout → raise (el scan falla con error)
5. invocar grafo LangGraph (sin cambios internos)
6. post-analysis → si NOT is_commit_indexed(repo_url, branch, commit_sha) → batch_service.trigger_delta_index(...) [fire-and-forget]; si ya indexado → skip con log
```

El polling usa `asyncio.sleep` con backoff fijo (10 segundos, máximo 60 intentos = 10 min). Si supera el timeout o el job falla, se lanza una excepción que propaga el error del scan.

### D6 — Instrucción al agente sobre contexto RAG

Se añade una sección en el `system_prompt.md` del agente indicando que debe considerar el contexto del código base indexado (disponible via herramienta MCP de búsqueda vectorial) como fondo, y que los archivos del commit actual se obtienen via MCP git. Esta sección se activa solo si el índice está disponible (se inyecta dinámicamente en el prompt).

**Nota:** La herramienta MCP de búsqueda vectorial no existe aún en `src/mcp`. En esta integración, el contexto RAG se usa de forma implícita: el agente recibe en el prompt una instrucción de que "el código base está indexado para la rama X" sin exponer una herramienta de búsqueda directa. La búsqueda vectorial activa queda como trabajo futuro.

### D8 — Idempotencia del delta: verificación en el agente antes de disparar el job

**Problema:** Re-ejecutar un scan sobre el mismo commit dispara un job batch delta innecesario, aunque el rag-indexer ya tenga idempotencia interna (`_execute_delta` compara `latest/meta.json` commit_sha con el commit recibido).

**Decisión:** El agente verifica idempotencia **antes** de llamar `trigger_delta`, usando `IRagIndexStatusPort.is_commit_indexed(repo_url, branch, commit_sha)`. El criterio es la existencia de `{repo_slug}/branches/{branch}/{commit_sha}/meta.json` en S3 — el mismo artefacto que escribe el rag-indexer al completar cualquier indexación (full o delta).

**Capas de defensa:**
```
┌─────────────────────────────────────────────────────────┐
│  Agente (pre-trigger)                                   │
│  is_commit_indexed? → skip trigger_delta, log info      │
└──────────────────────────┬──────────────────────────────┘
                           │ solo si False
                           ▼
┌─────────────────────────────────────────────────────────┐
│  rag-indexer (_execute_delta)                           │
│  latest commit_sha == commit_sha? → skip, return 0      │
└─────────────────────────────────────────────────────────┘
```

**Fail-safe:** Si `is_commit_indexed` falla (S3 error), el agente NO dispara el delta y loguea el error. Preferimos no indexar antes que duplicar jobs ante incertidumbre.

**Alternativa descartada:** Confiar solo en la idempotencia del rag-indexer — funciona pero desperdicia recursos (batch job + contenedor) en cada re-scan.

### D7 — ARNs en políticas IAM obtenidos desde SSM Parameter Store, sin wildcards

Todas las políticas IAM deben referenciar ARNs exactos. No se permiten wildcards como `"arn:aws:s3:::*"` o `"arn:aws:secretsmanager:*:*:secret:*"`.

**Regla general:** los ARNs se obtienen de `dependency.parameters` (SSM lookup), igual que el resto de los recursos.

**Bucket S3 del rag-indexer — leído desde SSM Parameter Store (ambos módulos):** El nombre y ARN del bucket RAG se leen desde SSM en los módulos `rag-indexer/aws/batch` y `agent/aws/batch`, bajo los paths `{base_path}/infra/s3/rag-code/bucket_name` y `{base_path}/infra/s3/rag-code/bucket_arn`. Estos parámetros son publicados por un módulo S3 dedicado (externo a este change). El `ssm/upsert` del rag-indexer **no publica** estos parámetros. El `ecs` del rag-indexer fue eliminado; el único modo de despliegue es Batch.

**Secrets Manager:** El ARN del secret manager está disponible en SSM lookup como `{base_path}/infra/secret/manager/arn` y debe usarse en ambos módulos (`rag-indexer/aws/batch` y `agent/aws/batch`).

## Risks / Trade-offs

- **[Timeout de indexación full]** Una rama con repositorio grande puede superar el timeout de polling → Mitigación: timeout generoso (10 min); si se supera, el scan falla con error explícito (no hay modo degradado).
- **[Credenciales S3 en el agente]** El agente necesita leer un objeto S3 para verificar el índice → Mitigación: los permisos IAM se gestionan explícitamente en `src/agent/aws/batch/terragrunt.hcl` (tareas 9.3 y 9.4); no depende de herencia de roles.
- **[branch no siempre disponible]** La CLI no siempre pasa branch → Mitigación: `branch` es obligatorio en los tres strategies; si el agente recibe un task sin `branch`, falla con error explícito.
- **[Acoplamiento de nombres de imagen Docker local]** El nombre `titvo/rag-indexer` está hardcodeado → Riesgo asumido; el entorno de desarrollo es de un solo desarrollador y la colisión de contenedores es improbable.

## Migration Plan

1. Desplegar `src/api/task/trigger` con el campo `branch` en `args` y en la tabla DynamoDB.
2. Desplegar `src/agent` con el nuevo módulo `rag_indexer_trigger` y la verificación pre/post scan.
3. No hay datos existentes que migrar: los scans en curso que no tengan `branch` simplemente saltan la verificación RAG (campo opcional al leer).

## Open Questions

_Sin preguntas abiertas._
