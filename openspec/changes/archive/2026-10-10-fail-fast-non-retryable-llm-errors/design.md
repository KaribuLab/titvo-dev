## Context

`BaseExpertNode._invoke_with_retry` reintenta cualquier excepción `max_attempts` veces (3) con backoff 1s/2s. El SDK de OpenAI añade 2 reintentos propios por intento. Los 6 expertos corren en paralelo bajo un semáforo compartido (`ExpertRuntimeConfig.semaphore`, concurrencia 4). Con ~393 lotes y un proveedor sin créditos, cada lote paga 9 llamadas HTTP más 3s de backoff antes de fallar: ~25 minutos para no analizar nada.

Además:

- `RagRetrievalNode` llama `_embed` hasta 10 veces (una por archivo); cada una falla con el mismo 429.
- `MergeFindingsNode` haría una llamada L2 por grupo de hallazgos si algún lote hubiera alcanzado a terminar antes de agotarse los créditos.
- `merge` cierra con `WARNING` si no hay issues pero hay `failed_batches`; el usuario no ve que el proveedor estaba caído.

Los expertos corren en el mismo superstep de LangGraph, así que no pueden verse entre sí vía `AgentState`. Ya comparten un objeto en memoria (`ExpertRuntimeConfig`), que es el lugar natural para el breaker.

## Goals / Non-Goals

**Goals**

- Un error no retryable aborta el análisis en segundos, no en minutos.
- El resultado dice explícitamente que el proveedor no estaba disponible (`FAILED` + `error`).
- Los archivos no analizados quedan listados en `incomplete` como hoy.
- Clasificación agnóstica del proveedor (OpenAI, OpenRouter, Anthropic, Google).

**Non-Goals**

- Ver proposal: no tocar `max_retries` del SDK, no healthcheck previo, no investigar el conteo de archivos.

## Decisions

### D1. Clasificador de errores en módulo propio: `code_analysis/infra/adapters/llm_errors.py`

`is_non_retryable(exc) -> bool` y `describe(exc) -> str`. Reglas, en orden:

1. `status_code` (atributo de `openai.APIStatusError`, `anthropic.APIStatusError`; `code` en `google.api_core` ) en `{400, 401, 403, 404}` → no retryable.
2. `status_code == 429` y el cuerpo (`exc.body`/`exc.response.json()`) o el mensaje contiene `insufficient_quota`, `credit_balance_exhausted`, `billing` o `credit balance is too low` → no retryable.
3. Cualquier otro 429, 5xx, `APITimeoutError`, `APIConnectionError`, excepciones genéricas → retryable.

Se inspecciona `exc` y su cadena `__cause__` para cubrir wrappers de LangChain. No se importa `openai`/`anthropic` en el módulo: se usa duck typing sobre `status_code` y `body` para no acoplar a un SDK (Google no expone `status_code`).

*Alternativa descartada*: lista blanca de clases por SDK. Más precisa pero se rompe con cada proveedor nuevo y no cubre OpenRouter (que devuelve 402 para créditos; se añade `402` al set del punto 1).

### D2. `ProviderCircuitBreaker` compartido en `ExpertRuntimeConfig`

Dataclass pequeña con `trip(reason: str)`, `is_open`, `reason`, `reset()`. Se instancia perezosamente en `ExpertRuntimeConfig` igual que el semáforo. `_invoke_with_retry`:

- Antes de cada intento: si `breaker.is_open` → lanza `ProviderUnavailableError(reason)`.
- En `except`: si `is_non_retryable(exc)` → `breaker.trip(describe(exc))`, log `ERROR` una sola vez (el breaker ignora `trip` repetidos), re-raise sin dormir.
- Si es retryable: comportamiento actual.

`_run_batch` distingue `ProviderUnavailableError` del resto: el `_BatchOutcome` lleva `error="aborted: <reason>"` y `aborted=True`, sin log por lote. `__call__` loguea un resumen: `"%s aborted %d of %d batches: %s"`.

Los lotes abortados sí entran en `failed_batches` (con `paths`) para que `incomplete.files_not_fully_analyzed` siga siendo completo.

*Alternativa descartada*: cancelar las tasks de `asyncio.gather` al primer fallo. Más agresivo, pero pierde los lotes que ya estaban a mitad de respuesta y complica el orden determinista de resultados.

### D3. Propagación al `merge` vía nueva clave de estado `provider_error`

Cada experto que vea el breaker abierto emite `provider_error: <reason>`. Reducer `keep_first` (el primero no vacío gana) en `state.py`. `merge`:

- Si `provider_error` → `status = "FAILED"`, `error = "Proveedor LLM no disponible: <reason>"`. `incomplete` se construye como hoy.
- Si `provider_error` → omite L2 (`_consolidate_by_file` devuelve L1 sin llamar al modelo) y lo registra en `metrics["l2_skipped_reason"]`.

`MergeFindingsNode` no necesita el breaker: lee el estado. Esto mantiene `merge` puro respecto al estado y testeable sin el objeto compartido.

*Alternativa descartada*: inferir "proveedor caído" de `failed_batches` (todos fallidos). Ambiguo cuando algunos lotes terminaron antes de agotarse los créditos.

### D4. Reset por invocación en `LangGraphAgent._invoke_wrapped`

El workflow se compila una vez por instancia de agente (`_initialize`). En Batch hay un proceso por tarea, pero para no depender de eso, `_invoke_wrapped` llama `self._expert_config.breaker.reset()` antes de `ainvoke`.

### D5. RAG: fallo fatal recordado por scan en el adapter

`S3SqliteRagContextAdapter._embed`: si `is_non_retryable(exc)`, guarda `self._embedding_disabled_reason` y `WARNING` una vez; llamadas posteriores devuelven `None` sin tocar el proveedor. `configure()` limpia el flag (se llama una vez por scan en `RagRetrievalNode`). No se comparte breaker con los expertos: el embedding puede usar otra clave/proveedor, y un RAG caído no invalida el análisis (spec `agent-rag-context`).

## Risks / Trade-offs

- [Un 400 por prompt demasiado largo o contenido rechazado por el proveedor abriría el breaker y abortaría todo el scan] → Hoy ese lote fallaría igual tras 3 intentos; el riesgo real es abortar los demás lotes. Mitigación: el 400 solo abre el breaker si el cuerpo no indica `context_length_exceeded` / `content_filter`; esos códigos se tratan como fallo del lote sin breaker (no retryable, no fatal). El clasificador devuelve un enum `RETRY | FAIL_BATCH | FATAL`.
- [Proveedores con mensajes no estructurados para "sin créditos"] → Quedan como retryable (comportamiento actual). Se añaden patrones conforme aparezcan; tests parametrizados por proveedor.
- [Reintentos del SDK siguen ocurriendo en los lotes en vuelo al abrirse el breaker] → Acotado a `max_concurrency` lotes × ~2s. Aceptable.
- [Cambio de `WARNING` a `FAILED` para scans ya en curso] → Solo cuando hay `provider_error`; los demás flujos de `scan-completeness` no cambian.

## Migration Plan

Despliegue normal de la imagen del agente. Sin cambios de esquema ni de contrato con API/MCP: `error` e `incomplete` ya existen en `ResultDto` y en el reporte. Rollback: imagen anterior.

## Open Questions

- Códigos exactos de Anthropic y Google para saldo agotado; se confirman durante la implementación con los SDK instalados y se cubren con tests.
