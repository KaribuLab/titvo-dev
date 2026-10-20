## 1. NotificationService

- [x] 1.1 `send_notifications`: retornar `{}` y loguear `ERROR` (causa + `len(files_not_fully_analyzed)`) cuando `result_dto.error` está seteado, antes de `create_report`.
- [x] 1.2 Tests en `tests/unit/test_notification_service.py`: `FAILED` + `error` no llama `create_report`, Code Insights ni issue de GitHub (bitbucket/github/cli); `FAILED` sin `error` sigue generando reporte y Code Insights.

## 2. AnalyseCodeUseCase y exit code

- [x] 2.1 `_log_failure(task_id, result)`: `ERROR` con `error`, `WARNING` con `incomplete.message` + archivos, `WARNING` por cada `coverage.errors`; para `FAILED` sin `error` loguear `issues_count`.
- [x] 2.2 `exit_code_for_task(task) -> int`: 1 para `ERROR` o `FAILED` con `result.error`; 0 en el resto.
- [x] 2.3 `main.py`: `main() -> int`, `sys.exit(asyncio.run(main()))`, log `ERROR` antes de salir con 1.
- [x] 2.4 Tests en `tests/unit/test_analyse_code_use_case.py`: exit code por status/result; `FAILED` con `error` deja causa, `incomplete.message` y errores de expertos en los logs.

## 3. Verificación

- [x] 3.1 `uv run ruff check src tests` y `uv run pytest tests/unit` en `src/agent` (391 passed).
- [x] 3.2 Confirmado: la job definition `security-scan` no define `retryStrategy`; Batch usa `attempts = 1` (default) y el job simplemente falla.
- [ ] 3.3 Prueba manual con clave inválida: sin `reportURL` en logs, tarea `FAILED` con `error`, job Batch `FAILED`, API de estado responde `FAILED` con el mismo `result`.

## 4. Documentation

- [x] 4.1 `docs/architecture.md`: párrafo sobre `FAILED` con `error` aguas abajo (sin reporte, logs, exit code, polling sin cambios).
- [x] 4.2 `docs/troubleshooting.md`: sección "`FAILED` con Proveedor LLM no disponible" con qué esperar en logs, tabla, Batch y la nota de `retryStrategy`.
