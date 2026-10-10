## Why

Un escaneo tardó 25 minutos con el proveedor LLM sin créditos (`429 insufficient_quota / credit_balance_exhausted`). El agente trató ese error como transitorio: cada uno de los ~393 lotes hizo 3 intentos con backoff (más los 2 reintentos internos del SDK por intento), el RAG reintentó el embedding por archivo, y el `merge` cerró el scan como `WARNING` sin indicar que el proveedor estaba caído. Un error no recuperable debe abortar el análisis en segundos y reportarse como `FAILED` con causa explícita.

## What Changes

- Clasificación de errores del proveedor LLM en **retryable** (429 rate limit, 5xx, timeouts, red) y **no retryable** (sin créditos/cuota, 401, 403, 404, 400). Solo los primeros se reintentan.
- **Circuit breaker compartido por scan**: el primer error no retryable abre el breaker; los lotes pendientes de ese experto y de los demás expertos se abortan sin llamar al proveedor. Se registran en `failed_batches` con `error="aborted: <causa>"`.
- El breaker se reinicia al inicio de cada invocación del workflow.
- `merge` omite la consolidación L2 (llamadas al modelo) cuando el breaker está abierto y conserva los hallazgos L1.
- Cuando el breaker está abierto, `final_output.status` es `FAILED`, `error` describe la causa (`"Proveedor LLM no disponible: <mensaje>"`) e `incomplete` lista todos los archivos no analizados.
- RAG: tras un error no retryable del embedding, el adapter no vuelve a llamar al proveedor de embeddings en el mismo scan. Sigue siendo no fatal (el análisis continúa sin RAG).
- Logs: un único `ERROR` al abrir el breaker; los lotes abortados se registran en un resumen por experto, no uno por lote.

## Capabilities

### New Capabilities

- Ninguna.

### Modified Capabilities

- `expert-analysis-batching`: el requisito de reintentos pasa a distinguir errores retryable de no retryable, y añade el breaker compartido que aborta los lotes pendientes.
- `scan-completeness`: un scan con proveedor LLM no disponible termina `FAILED` con `error` e `incomplete`, no `WARNING`.
- `agent-rag-context`: tras un fallo no retryable de embeddings no se repiten llamadas al proveedor durante el scan.

## Impact

- `src/agent/src/code_analysis/infra/adapters/langgraph/nodes/base_expert_node.py`: clasificación, breaker, abort de lotes.
- Nuevo módulo `src/agent/src/code_analysis/infra/adapters/llm_errors.py` (clasificador + `ProviderCircuitBreaker`).
- `merge_findings_node.py`: status `FAILED` + `error` con breaker abierto; skip L2.
- `langgraph_agent.py` / `workflow.py`: inyección y reset del breaker por invocación.
- `s3_sqlite_rag_context_adapter.py`: memoria de fallo fatal por scan.
- `state.py`: nueva clave `provider_error`.
- Tests unitarios en `src/agent/tests/unit/`.
- Sin cambios en MCP, API ni rag-indexer. El `ResultDto` ya admite `error` e `incomplete`.

## Non-goals

- No cambiar `max_retries` del SDK de OpenAI/Anthropic; con el breaker el costo de esos reintentos queda acotado a los lotes en vuelo (≤ `max_concurrency`).
- No añadir chequeo previo de créditos ni healthcheck del proveedor antes de iniciar el scan.
- No investigar aquí por qué un scan "de un archivo" clasificó 1279 archivos; revisar `scan_mode` de esa tarea por separado.
- No notificar al usuario por un canal distinto del resultado de la tarea y el reporte.
