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

Si usas `uv`, sincroniza dependencias según tu `pyproject.toml` (grupo `dev` incluye Ruff).
