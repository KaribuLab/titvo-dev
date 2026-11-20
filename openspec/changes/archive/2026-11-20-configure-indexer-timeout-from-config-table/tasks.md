# Tasks

Cada tarea está acotada a un máximo estimado de dos horas. Implementar sobre el estado actual de los submódulos preservando cambios existentes.

## 1. Configuración e inyección

- [x] 1.1 Usar el skill `find-docs` para verificar las APIs vigentes de reloj monotónico, polling/sleep y escritura condicional DynamoDB utilizadas; verificar con referencias registradas en las notas de implementación.
- [x] 1.2 Leer `rag_indexing_timeout_seconds` desde el proveedor en `src/agent/src/main.py`, con default de 600 segundos si falta o está vacío y sin override por env; omitirla para CLI. Verificar tests de fallback, rechazo de texto/cero/negativos/NaN/infinito, decimal válido y errores de lectura.
- [x] 1.3 Inyectar el valor al caso de uso y actualizar constructores/fixtures, con validación previa a enviar jobs Git y `None` explícito para CLI; verificar tests de wiring, bypass CLI y rechazo sin invocar triggers.

## 2. Espera temporal por job

- [x] 2.1 Sustituir `_RAG_MAX_ATTEMPTS` por deadline monotónico por job, sleep acotado al restante y comprobación antes/después de consultar; documentar el método y verificar tests con reloj controlado para éxito, fallo, timeout, fracciones, deadline exacto y consulta que retorna tarde.
- [x] 2.2 Agregar diagnóstico de job ID, timeout efectivo y elapsed en logs/TimeoutError; verificar con captura de logs y aserciones del error que no aparece el máximo fijo de 60 intentos.
- [x] 2.3 Agregar regresiones full inicial y delta bloqueante con presupuestos independientes y más de 60 polls; verificar además delta commit fire-and-forget y CLI sin espera mediante unit tests sin sleeps reales.

## 3. Bootstrap local

- [x] 3.1 Agregar seed condicional `rag_indexing_timeout_seconds="600"` en `localstack/app/setup.ts`, documentando que es un dato inicial editable; verificar con tests de registro ausente, existente personalizado y errores distintos al conflicto, sin sobrescribir ajustes.

## 4. Verificación integrada

- [x] 4.1 Ejecutar suite unitaria del agente y checks/linter correspondientes a Python y al bootstrap TypeScript; verificar que no existan errores introducidos y registrar comandos/resultados.
- [x] 4.2 Ejecutar un smoke local de lectura real de tabla con estados de job controlados: cambiar el parámetro entre scans, confirmar nuevo plazo, default por clave ausente/vacía, rechazo de inválidos y bypass CLI; verificar logs y registrar evidencia reproducible.

## 5. Documentation

- [x] 5.1 Actualizar `docs/rag-indexer.md` con clave, unidades, formato string, default compatible, validación, ejemplo de ajuste, rollback y límites externos; generar el diagrama de secuencia configuración → agente → Batch → éxito/fallo/timeout. Verificar que cubra full inicial, delta bloqueante y ausencia de cancelación remota.
- [x] 5.2 Actualizar `docs/architecture.md` con lectura en composition root, inyección y deadline por job; verificar coherencia con la implementación y el diagrama de secuencia.
- [x] 5.3 Actualizar `docs/dev-env-structure.md` con seed local idempotente y cambio del dato en la tabla; verificar el procedimiento contra el smoke local y confirmar que no requiere una variable de entorno de timeout.
- [x] 5.4 Generar o actualizar documentación del componente en `src/agent/README.md` con el parámetro opcional y default para Git, bypass CLI y logs de diagnóstico; verificar nombres y ejemplos contra los tests y ejecutar `openspec validate configure-indexer-timeout-from-config-table --strict`.
