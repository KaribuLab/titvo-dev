## Why

Un scan en prod quedó `RUNNING` casi 4 días: un lote del experto `owasp_web` nunca recibió respuesta del modelo (MiniMax vía endpoint OpenAI-compatible). `ChatOpenAI` se construía sin `timeout`, el SDK arma `httpx` con `Timeout(None)` y no existía deadline global del workflow, así que ni el agente ni Batch cerraban el job.

## What Changes

- `LangchainAgentModelFactory` pasa `timeout` a `ChatOpenAI`, `ChatAnthropic` y `ChatGoogleGenerativeAI` (default 180s). Un request colgado lanza timeout, que `classify` ya trata como `RETRY`.
- `LangGraphAgent` envuelve `workflow.ainvoke` en `asyncio.wait_for` con `scan_timeout_seconds` (default 3000s). Al vencer lanza `ScanTimeoutError`; el scan cierra `FAILED` con `error` explícito, sin reporte y con exit 1 (reusa `skip-notifications-on-infra-failure`).
- `main.py` lee `ai_request_timeout_seconds` y `scan_timeout_seconds` de la tabla de configuración (`read_timeout_seconds`): vacío → default, inválido o `<= 0` → falla al arrancar.
- Infra (ya en la rama): `job_timeout = 3600` en `aws/batch/terragrunt.hcl` como red de seguridad externa.

## Capabilities

### New Capabilities

- Ninguna.

### Modified Capabilities

- `scan-completeness`: todo scan tiene deadline por request y deadline global; vencerlos produce `FAILED` con `error`, no un contenedor colgado.

## Impact

- `src/agent/src/code_analysis/infra/adapters/langchain_agent_adapter.py`, `langgraph_agent.py`, `src/main.py`, tests unitarios.
- Dos `parameter_id` nuevos opcionales en la tabla de configuración; sin cambios en API, MCP ni rag-indexer.

## Non-goals

- No tocar `max_retries` del SDK: la consolidación L2 (`merge_findings_node`) no tiene retry propio y hoy depende de los reintentos del SDK.
- No agregar deadline por nodo (MCP retrieval, RAG): quedan cubiertos por el deadline global.
