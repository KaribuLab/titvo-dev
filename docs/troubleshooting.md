# Troubleshooting

## Errores comunes

### Solo aparece `mcp.tool.git.commit-files` en Langfuse (sin expertos)

**Causa:** En el gateway MCP, `git.commit-files` es un job **asíncrono**. La primera
invocación solo devuelve `jobId` y `pollToolName`. Sin llamar repetidamente a
`mcp.tool.git.commit-files.poll` hasta `status = SUCCESS`, no hay lista `filesPaths` y el flujo LangGraph salta al nodo `merge` sin ejecutar los expertos.

**Qué esperar:** En Langfuse deberían verse al menos **`mcp.tool.git.commit-files`** y varias invocaciones a **`mcp.tool.git.commit-files.poll`** (una por intento hasta completar), más **`mcp.tool.files`** por cada ruta leída.

**Solución:** El `MCPRetrievalNode` ya implementa ese ciclo en

`src/agent/src/code_analysis/infra/adapters/langgraph/nodes/mcp_retrieval_node.py`.

Si tras desplegar sigue fallando, revisar logs de `mcp-gateway`, colas/lambdas en LocalStack y constantes de timeout en el nodo.

### "No files retrieved from MCP"

**Causa:** El commit no tiene archivos, el job falló, o solo se llamó commit-files sin
polling hasta obtener `filesPaths`.

**Solución:**
```bash
# Verificar que el commit existe
git show <commit_hash>

# Verificar logs de MCP
docker logs mcp-gateway
```

### Expert returns invalid JSON

**Causa:** El LLM no siguió el formato JSON requerido.

**Logs:**
```
WARNING Failed to parse JSON from owasp_api response
```

**Solución:**
- Revisar el prompt del experto (`prompts/experts/owasp_api.md`)
- Asegurar que incluya instrucciones claras de formato JSON
- Verificar que no haya conflictos de instrucciones

### Duplicate key in merge

**Causa normal:** Dos expertos reportan el mismo hallazgo (misma clave de deduplicación).

**Comportamiento:** El nodo **`merge`** elimina duplicados por `get_dedup_key()` (típicamente `path`, `line`, `category`) y se queda con la **primera** aparición en la lista acumulada. El servicio domain **`FindingsMerger`** define además la política **conservadora de severidad** cuando se combinan resultados por experto; si necesitas la misma regla en el grafo, conviene futura refactorización para reutilizar `FindingsMerger` dentro del merge final.

### LangGraph workflow timeout (`recursion_limit`)

**Causa:** El grafó excede el **`recursion_limit`** (por defecto **100** en `LangGraphAgent` al invocar el workflow).

**Solución:** Subir el límite en `src/agent/src/code_analysis/infra/adapters/langgraph_agent.py` en el `config` pasado a `ainvoke` (por ejemplo `200`), o reducir profundidad del flujo si hubiera ciclos anómalos.

### Feature flag no funciona

**Verificación:**
```bash
# Verificar variable de entorno
echo $TITVO_AGENT_MODE

# Valores válidos: langgraph, legacy
```

## Modo Debug

```bash
export LOG_LEVEL=DEBUG
export TITVO_AGENT_MODE=langgraph
cd src/agent
python -m src.main
```

## Rollback a Legacy

```bash
# Cambiar a modo legacy
export TITVO_AGENT_MODE=legacy

# Redeploy si es necesario (ejemplo desde la raíz del monorepo)
docker build -f src/agent/Dockerfile -t titvo-agent:latest src/agent
```

## Verificar prompts cargados

```python
# Python REPL con cwd en src/agent (empaquetado code_analysis)
from code_analysis import prompts

print(prompts.list_experts())
print(prompts.get_expert_prompt("owasp_api")[:200])
```

## Errores de Langfuse / import incorrecto

- El handler debe importarse como **`from langfuse.langchain import CallbackHandler`**. Una ruta **`langfuse.callback`** obsoleta provoca fallo de importación al iniciar.

Si Langfuse no está configurado (sin credenciales), el agente puede ejecutarse sin tracing; es esperable `langfuse_callback_handler = None` en ese caso.

## Conectividad con MCP Gateway

- Revisa logs: `docker compose logs mcp-gateway` (o el nombre del servicio en tu `docker-compose.yaml`).
- La URL del servidor MCP la consume el agente según configuración de despliegue (p. ej. variable de entorno / parámetros); debe ser alcanzable desde el contenedor del agente (Streamable HTTP en el path configurado, típicamente bajo `/mcp`).

## Rebuild después de cambios

```bash
# Desde la raíz del monorepo (contexto de build = src/agent)
docker build -f src/agent/Dockerfile -t titvo-agent:latest src/agent

# Calidad local (con venv en src/agent)
cd src/agent
.venv/bin/ruff check src/
```

## RAG Indexer

### Run interrumpido a mitad — qué esperar del resume

**Síntoma:** El job de AWS Batch murió (timeout, OOM, evict) y querés saber qué se preservó.

**Diagnóstico:** Revisá los CloudWatch logs del job:
- `Checkpoint flushed: files_processed=N db_size_mb=X upload_ms=Y` → cuántos checkpoints alcanzó a subir.
- `Lock acquired owner=...` → desde cuándo corre.
- Si hay logs `Embedded batch i/N chunks=N` → cuántos batches de embeddings completó.

**Recover automático:** El siguiente run del mismo `(TITVO_REPO_URL, TITVO_BRANCH, TITVO_COMMIT_SHA)`:
1. Detecta el checkpoint DB en `branches/{branch}/checkpoints/{commit_sha}/index.db` y lo descarga.
2. Detecta el snapshot `repo.tar.gz` y lo restaura (skip `git fetch`).
3. Lee `indexed_files` y calcula `exclude_paths` para `get_files()`.
4. Procesa solo los archivos restantes.
5. Loguea `Resume mode: checkpoint_found=True files_already_indexed=N`.

**Si no aparece resume:** eliminá cualquier artefacto previo en S3 (`s3 rm <bucket>/branches/{branch}/checkpoints/{commit_sha}/`) para forzar un run fresh.

### Snapshot ausente — fallback a git fetch

**Síntoma:** En logs aparece `WARNING: no source snapshot found, falling back to git fetch`.

**Causa:** El primer checkpoint de un branch/commit no se subió (ej. job murió ANTES del primer `get_files()` exitoso), o se borró manualmente.

**Efecto:** El resume funciona, pero hace `git fetch` + `cat-file blob` × N desde el remote. Más lento (~3 min en 20k archivos) que con snapshot (~5-10 s).

**Workaround:** No aplica — es la degradación esperada. El nuevo run subirá un snapshot fresh después del primer `get_files()` exitoso.

### Snapshot excede tamaño máximo

**Síntoma:** El job falla con `ValueError: Snapshot size X MB exceeds maximum Y MB`.

**Causa:** El `.git` del repo es más grande que `TITVO_MAX_SNAPSHOT_MB` (default 200). Común en repos con muchos tags o branches livianos.

**Solución:** Subí `TITVO_MAX_SNAPSHOT_MB` (ej. 500) o deshabilita el snapshot subiéndolo a 0. Sin snapshot, el resume sigue funcionando, solo más lento.

### Lock activo pertenece a otro job — fail-fast

**Síntoma:** El job falla con `RuntimeError: Lock held by <owner> until <expires_at>, cannot start index for <branch>`.

**Causa:** Otro job del indexer está corriendo para el mismo `(repo, branch)`. El lock es **atómico** vía `IfNoneMatch="*"` en `locks/{branch}.json`.

**Efecto:** El job saliente NO gastó tokens de OpenAI (el lock acquisition es ÚNICO en `execute()`, antes de cualquier llamada a `embed()`).

**Qué hacer:**
1. Si el job activo está progresando: esperá a que termine (monitorea CloudWatch).
2. Si el job activo está colgado: el lock expira en `TITVO_LOCK_TTL_MINUTES` (default 360 min). Después podés reintentar.
3. Para intervención manual: `aws s3 rm s3://<bucket>/<repo>/locks/<branch>.json` (liberar el lock manualmente). Solo hacerlo si estás seguro de que no hay otro job corriendo.

### Lock no se libera — esperar TTL o delete manual

**Síntoma:** El job anterior murió sin pasar por el `finally` (OOM, kill -9). El lock quedó en S3.

**Causa:** El `finally` del use case no se ejecutó. TTL está contando.

**Qué hacer:**
1. Esperá `TITVO_LOCK_TTL_MINUTES` (default 360 min).
2. O forzar: `aws s3 rm s3://<bucket>/<repo>/locks/<branch>.json`.

Si usas `uv`, sincroniza dependencias según tu `pyproject.toml` (grupo `dev` incluye Ruff).
