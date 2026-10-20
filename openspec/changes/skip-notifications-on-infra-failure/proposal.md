## Why

Un scan sin créditos en el proveedor LLM terminó `FAILED` con `error="Proveedor LLM no disponible: 429 credit_balance_exhausted"`, cero hallazgos y los dos archivos sin analizar, pero igual generó un reporte HTML en S3 (`reportURL`) y el proceso salió con exit code 0. `NotificationService` solo omite notificaciones cuando el status es `COMPLETED`; `FAILED` está sobrecargado (hallazgos CRITICAL/HIGH vs. falla de infraestructura) y el servicio no distingue ambos casos. Además los logs no explican por qué falló la tarea más allá del dump del resultado.

## What Changes

- `NotificationService.send_notifications` omite el reporte HTML y toda notificación (Code Insights, issue de GitHub) cuando `result_dto.error` está seteado, y loguea un `ERROR` con la causa y la cantidad de archivos sin analizar. `FAILED` por hallazgos (sin `error`) sigue generando reporte.
- `AnalyseCodeUseCase` loguea al marcar `FAILED`: causa (`error`), `incomplete.message` con los archivos, y cada error de `coverage.errors`.
- `main.py` termina con exit code 1 cuando la tarea persistida quedó `FAILED` con `error` o `ERROR` (nueva función `exit_code_for_task`). `FAILED` por hallazgos y `COMPLETED`/`WARNING` salen con 0.

## Capabilities

### New Capabilities

- Ninguna.

### Modified Capabilities

- `scan-completeness`: un `FAILED` con `error` no genera reporte ni notificaciones, deja la causa en los logs y el job termina con exit code 1.

## Impact

- `src/agent/src/code_analysis/domain/notification_service.py`: short-circuit por `error`.
- `src/agent/src/code_analysis/application/analyse_code_use_case.py`: `_log_failure` y `exit_code_for_task`.
- `src/agent/src/main.py`: `main()` retorna exit code; `sys.exit(asyncio.run(main()))`.
- Tests en `src/agent/tests/unit/test_notification_service.py` y `test_analyse_code_use_case.py`.
- Polling del API de estado (`GetTaskStatusUseCase`): sin cambios. Solo consulta AWS Batch cuando la tabla está `PENDING`/`IN_PROGRESS`; la tabla ya queda `FAILED` antes del exit, así que el resultado del polling es el mismo.
- Riesgo operativo: si la job definition de Batch tiene `retryStrategy.attempts > 1`, el exit code 1 relanzaría el scan. Verificar en infra que sea 1 (default).

## Non-goals

- No introducir un status `ERROR` en `AnalysisStatus` ni cambiar el contrato del `final_output` del `merge`.
- No cambiar el API de estado ni la lógica de polling de pipelines.
- No cambiar el exit code para `FAILED` por hallazgos.
