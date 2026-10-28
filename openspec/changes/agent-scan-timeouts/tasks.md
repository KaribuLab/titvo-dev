## 1. Timeouts en el agente

- [x] 1.1 `LangchainAgentModelFactory`: parámetro `request_timeout_seconds` (default 180, `> 0`) pasado como `timeout` a los tres clientes; log del valor.
- [x] 1.2 `LangGraphAgent`: parámetro `scan_timeout_seconds` (default 3000, `> 0`), `asyncio.wait_for` y `ScanTimeoutError` con `task_id`.
- [x] 1.3 `main.py`: `read_timeout_seconds` para `ai_request_timeout_seconds` y `scan_timeout_seconds`; wiring hasta factory y agente.
- [x] 1.4 Tests: timeout efectivo en clientes sync/async de cada proveedor; scan vencido → `FAILED` + `error` + cancelación del workflow; parsing de configuración.

## 2. Infraestructura y verificación

- [x] 2.1 `aws/batch/terragrunt.hcl`: `job_timeout = 3600` (commit `d29a37c`).
- [x] 2.2 `uv run ruff check` y `uv run pytest tests/unit` (415 passed).
- [ ] 2.3 Post-deploy: log `Using provider=... request_timeout=180s` y `Using scan_timeout_seconds=3000s (default)` en un scan de prod.

## 3. Documentation

- [x] 3.1 `src/agent/README.md`: tabla de deadlines en la tabla de configuración.
- [x] 3.2 `docs/architecture.md`: sección "Deadlines".
- [x] 3.3 `docs/troubleshooting.md`: sección "Contenedor que no termina".
