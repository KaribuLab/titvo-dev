## Context

`merge` emite `status=FAILED` en dos situaciones: hallazgos CRITICAL/HIGH (scan exitoso con resultado negativo) y fallas de infraestructura (`provider_error`, `mcp_error`, cero archivos). Solo la segunda trae `error`. `NotificationService` y `main.py` no distinguían.

## Decisions

### D1. Discriminar por `result_dto.error`, no por un nuevo status

`error` ya existe en `ResultDto`, en el resultado persistido y en el contrato de `merge` (spec `scan-completeness`). Un status `ERROR` nuevo obligaría a tocar `merge`, el use case, el API de estado y el reporte. Se usa `error` como señal de "el scan no corrió".

### D2. Short-circuit en `NotificationService`, no en el use case

El use case sigue llamando `send_notifications` para todo status distinto de `COMPLETED`; la decisión de "no hay nada que reportar" vive junto a la decisión de "qué reportar". Retorna `{}` para que el resultado persistido no tenga `report_url`.

### D3. Exit code calculado desde la tarea ya persistida

`exit_code_for_task(task)` se evalúa después de `update_task`, así la tabla ya dice `FAILED` cuando el proceso sale. `GetTaskStatusUseCase` solo consulta Batch con la tarea `PENDING`/`IN_PROGRESS`, por lo que el exit code no altera el polling. Retorna 1 para `ERROR` o `FAILED` con `error`; 0 en el resto.

### D4. Logs explícitos en el use case

`_log_failure` deja: `ERROR` con la causa; `WARNING` con `incomplete.message` y los archivos; un `WARNING` por error de `coverage.errors`. Para `FAILED` por hallazgos loguea la cantidad de hallazgos.

## Risks

- `retryStrategy.attempts > 1` en la job definition de Batch relanzaría el scan ante exit code 1. Verificar en el repo de infraestructura.
