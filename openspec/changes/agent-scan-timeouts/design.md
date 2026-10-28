## Context

Dos capas sin límite: el SDK del proveedor (`Timeout(None)`) y el workflow completo. Batch tampoco tenía `job_timeout`. Cualquiera de las tres habría evitado los 4 días.

## Decisions

### D1. Timeout por request en el factory, no en los nodos

Los tres clientes aceptan `timeout`; ponerlo al construir el modelo cubre expertos, consolidación y reparación JSON sin tocar cada `invoke`. `classify` ya devuelve `RETRY` para excepciones sin status, así que un timeout se reintenta con backoff como un 5xx.

### D2. Deadline global con `asyncio.wait_for` dentro del `try` existente

`ScanTimeoutError` se lanza dentro del `try/except Exception` de `_invoke_wrapped`, que ya produce `FAILED` + `error` + `coverage.errors`. Así la tarea queda `FAILED` con causa, se omiten reporte y notificaciones y el proceso sale con 1. El mensaje incluye `scan_timeout_seconds` y `task_id` porque `str(TimeoutError())` es vacío.

### D3. Valores desde la tabla de configuración

Misma fuente que `ai_*` y `embedding_*`; ajustables sin redeploy. `scan_timeout_seconds` (3000) < `job_timeout` de Batch (3600) para que el agente cierre la tarea antes del kill.

### D4. `max_retries` del SDK intacto

Con `max_retries=0` la consolidación L2 perdería su único retry ante 429/5xx. Peor caso acotado por lote: 3 intentos app × (1 + retries SDK) × 180s, y en cualquier caso por el deadline global.
