## 1. Clasificador de errores y circuit breaker

- [x] 1.1 Crear `src/agent/src/code_analysis/infra/adapters/llm_errors.py` con `ErrorClass` (`RETRY | FAIL_BATCH | FATAL`), `classify(exc) -> ErrorClass`, `describe(exc) -> str` y `ProviderUnavailableError`. Duck typing sobre `status_code`/`body`/mensaje, recorriendo `__cause__`.
- [x] 1.2 Implementar `ProviderCircuitBreaker` (`trip(reason)`, `is_open`, `reason`, `reset()`) en el mismo módulo; `trip` repetido no cambia la causa ni vuelve a loguear.
- [x] 1.3 Verificar con los SDK instalados (`openai`, `anthropic`, `google-genai`) la forma de las excepciones de saldo agotado / 401 / 400 `context_length_exceeded` y ajustar patrones.
- [x] 1.4 Tests `tests/unit/test_llm_errors.py`: parametrizados por proveedor para 429 rate limit (RETRY), 429 `credit_balance_exhausted` (FATAL), 401/403/404/402 (FATAL), 400 `context_length_exceeded` (FAIL_BATCH), timeout (RETRY), excepción envuelta en `__cause__`.

## 2. Expert nodes

- [x] 2.1 Añadir campo perezoso `breaker: ProviderCircuitBreaker` a `ExpertRuntimeConfig` (mismo patrón que `semaphore`).
- [x] 2.2 `_invoke_with_retry`: comprobar `breaker.is_open` antes de cada intento; clasificar en `except`; `FATAL` → `trip` + un único `ERROR` + re-raise sin sleep; `FAIL_BATCH` → re-raise sin sleep; `RETRY` → comportamiento actual.
- [x] 2.3 `_run_batch`/`_BatchOutcome`: marcar `aborted=True` y `error="aborted: <reason>"` cuando salta `ProviderUnavailableError`; sin log por lote.
- [x] 2.4 `__call__`: log resumen `"%s aborted %d of %d batches: %s"`, y emitir `provider_error` en el delta cuando el breaker está abierto; `expert_metadata[expert]["aborted_batches"]`.
- [x] 2.5 `state.py`: clave `provider_error: Annotated[str | None, keep_first]` con reducer `keep_first`; inicializar en `langgraph_agent.py`.
- [x] 2.6 Tests en `tests/unit/test_base_expert_node.py`: sin créditos en lote 0 → un solo intento, resto abortado en `failed_batches`, `provider_error` presente, llamadas al modelo ≤ `max_concurrency`+1; 429 rate limit sigue reintentando 3 veces; `context_length_exceeded` falla solo su lote.
- [x] 2.7 Test de breaker compartido entre dos expertos (el segundo no llama al modelo tras abrirse); vive en `tests/unit/test_base_expert_node.py` con dos nodos y un mismo `ExpertRuntimeConfig`, sin necesidad de compilar el grafo.

## 3. Reset por invocación

- [x] 3.1 `LangGraphAgent._invoke_wrapped`: `self._expert_config.breaker.reset()` antes de `ainvoke`.
- [x] 3.2 Test: dos invocaciones consecutivas; la segunda vuelve a llamar al proveedor (`tests/unit/test_langgraph_agent.py`).

## 4. Merge node

- [x] 4.1 `MergeFindingsNode.__call__`: leer `provider_error`; si está, `status="FAILED"`, `error="Proveedor LLM no disponible: <reason>"`, mantener `incomplete`.
- [x] 4.2 Omitir L2 cuando `provider_error` está presente; registrar `metrics["l2_skipped_reason"]`.
- [x] 4.3 Tests en `tests/unit/test_merge_findings_node.py`: FAILED + error con `provider_error`; L2 no invoca el modelo y conserva L1; sin `provider_error` el flujo WARNING/COMPLETED no cambia.

## 5. RAG embeddings

- [x] 5.1 `S3SqliteRagContextAdapter._embed`: si `classify(exc) == FATAL`, guardar `_embedding_disabled_reason`, loguear un `WARNING` y devolver `None` en llamadas posteriores sin llamar al proveedor; `configure()` limpia el flag.
- [x] 5.2 Tests `tests/unit/test_s3_sqlite_rag_context_adapter.py`: 10 búsquedas tras `insufficient_quota` → una sola llamada a `embed_documents`; timeout no deshabilita.

## 6. Verificación y docs

- [x] 6.1 `uv run pytest` y `ruff check` en `src/agent` en verde.
- [x] 6.2 Actualizar `docs/architecture.md` (sección expertos/merge) con la clasificación de errores, el breaker y el estado `FAILED` por proveedor no disponible.
- [x] 6.3 Prueba manual con clave inválida: scan termina en segundos, `status=FAILED`, `error` con causa, `incomplete` con todos los archivos. Verificado 2026-10-09 con `ChatOpenAI` real (401 `invalid_api_key`) sobre 120 archivos / 32 lotes: 0.7 s, 4 llamadas al proveedor (= `max_concurrency`), 28 lotes abortados, `FAILED` + `error="Proveedor LLM no disponible: 401 invalid_api_key: …"`, `incomplete` con 120 archivos. LocalStack no estaba levantado; el E2E por API/Batch queda para el despliegue.
