# Design

## Context

Ver `proposal.md` para la motivación. `_wait_for_rag_job` en `src/agent/src/code_analysis/application/analyse_code_use_case.py` comparte constantes de 60 intentos y 10 segundos entre `_ensure_branch_rag_index` y el delta bloqueante de `_ensure_rag_index`. El delta post-scan de modo commit es fire-and-forget.

`main.py` ya construye `AwsConfigurationAdapter`, cuya lectura usa `parameter_id` y `value` de tipo string en DynamoDB. Al aplicar, el checkout actual ya no contiene el helper `read_timeout_seconds` observado durante la propuesta; se agrega un lector estricto dedicado para este parámetro. `localstack/app/setup.ts` tiene un helper de escritura incondicional: no debe utilizarse directamente para resembrar esta clave.

## Goals / Non-Goals

**Goals:** mantener la lectura de configuración en el composition root, inyectar un valor validado al caso de uso y medir el presupuesto con reloj monotónico. Permitir que tests avancen el reloj sin esperas reales.

**Non-Goals:** agregar acceso DynamoDB al dominio, modificar los timeouts LLM existentes, transformar el trigger Batch en un cliente asíncrono o implementar un cálculo por volumen. El timeout es de espera del agente, no de ejecución/cancelación del indexador.

## Decisions

### 1. Parámetro con default compatible leído una vez por scan Git

`main.py` leerá `rag_indexing_timeout_seconds` mediante `get_value`, tras resolver el origen de la tarea y antes de enviar jobs. Si falta o está vacío/solo espacios, usará `DEFAULT_RAG_INDEXING_TIMEOUT_SECONDS=600` y registrará el fallback. Los valores no vacíos deben ser numéricos finitos positivos. Los errores de DynamoDB se propagan. No se usará `get_secret` ni una variable de entorno. El flujo CLI omitirá la lectura.

Inyectar `rag_indexing_timeout_seconds` en `AnalyseCodeUseCase`; para CLI podrá ser `None` explícito. Las esperas Git rechazarán ausencia/valor inválido defensivamente antes de enviar jobs. Actualizar todos los constructores y fixtures sin añadir un default temporal oculto. Validar siempre al iniciar un scan Git, incluso si finalmente reutiliza un índice, ofrece un contrato operativo predecible.

El usuario aprobó el default de 600 segundos para mantener compatibilidad con configuraciones antiguas. El fallback se resuelve solo en el composition root, antes de inyectar el valor; el caso de uso mantiene validación defensiva. Consultar el proveedor en cada poll agregaría IO y permitiría cambiar deadlines en mitad de un scan. Ocultar valores no vacíos inválidos con el default impediría detectar errores de configuración.

### 2. Deadline monotónico por espera

Eliminar `_RAG_MAX_ATTEMPTS`. Al entrar en cada `_wait_for_rag_job`, calcular inicio y deadline con reloj monotónico. Antes de dormir, calcular restante; dormir `min(10, restante)`. Comprobar vencimiento antes de consultar y después de recibir el estado. Si venció, emitir `TimeoutError`; en otro caso aceptar `SUCCEEDED`, propagar `FAILED` como error, o continuar. El deadline es exclusivo: a partir de él no se acepta un resultado tardío. Un timeout de 2.5 segundos puede vencer sin consultar, puesto que conserva el polling diferido actual.

Cada job obtiene presupuesto independiente; cola y ejecución cuentan desde el inicio de su espera. Contabilizar el coste de consultas evita la deriva de `ceil(timeout / 10)` intentos. No cambiar el intervalo nominal ni las condiciones que deciden disparar full/delta.

`get_job_status` es síncrono: una llamada en curso puede demorar la observación del deadline hasta que el SDK retorne. Comprobar nuevamente el reloj impide aceptar éxito tardío, pero no promete cancelación instantánea de IO. Los límites de transporte del SDK y deadlines Batch siguen siendo independientes.

### 3. Diagnóstico y errores

Registrar inicio con job ID y timeout; en cada resultado incluir estado, elapsed y timeout. Sustituir el denominador fijo de intentos por información temporal. `TimeoutError` incluirá job ID, repositorio, etiqueta rama/commit, elapsed y presupuesto configurado. Mantener el comportamiento de propagación de errores existente y no cancelar el job remoto.

### 4. Seed local idempotente y migración explícita

Crear la clave local con string `"600"` solo si falta, mediante escritura condicional; tratar únicamente el conflicto de clave existente como resultado esperado. No cambiar la semántica general del helper de configuración. El seed coincide con el default de compatibilidad del agente. La guía usará 1800 segundos como ejemplo de ajuste operativo.

Alternativas: upsert incondicional sobrescribiría ajustes; un timeout vía `.env` duplicaría la fuente de verdad.

## Risks / Trade-offs

- [Nuevo agente desplegado antes del parámetro] → Default explícito de 600 segundos y log de su origen; configurar un plazo mayor si el job lo necesita.
- [Plazo alto prolonga espera de un job atascado] → Validación finita positiva, logs con elapsed y selección operativa consciente.
- [Job sigue corriendo tras timeout del agente] → Documentar que el cambio no cancela Batch y conservar identificación del job para operación.
- [Timeout externo más corto] → Revisar límites existentes de Batch y distinguirlos del presupuesto RAG; este change no los modifica.
- [IO síncrono rebasa el deadline] → Revalidar al retornar; documentar latencia de detección, sin ampliar el alcance a transporte asíncrono.
- [Código del agente ya modificado en el workspace] → Integrar sobre el estado actual y preservar los cambios ajenos, especialmente helpers de timeouts existentes.

## Migration Plan

1. Implementar seed local condicional y documentar formato de registro (`parameter_id` y `value` strings), unidades y validación.
2. En ambientes existentes la clave es opcional: ausencia o vacío conserva el presupuesto nominal de 600 segundos. Para el incidente, configurar un plazo mayor acorde al job real; conservar valores personalizados y validar los valores no vacíos.
3. Desplegar agente y verificar que los logs muestran el valor de tabla en full y delta bloqueante. Cambios posteriores afectan scans nuevos; scans en curso conservan su snapshot.
4. Validar con tests de reloj controlado y un smoke local de lectura/cambio entre scans, sin esperar diez minutos reales.
5. Rollback: volver a la imagen anterior; el registro puede permanecer y será ignorado por esa versión. Advertir que vuelve el límite fijo anterior.

## Verification

Tests parametrizados de parsing (incluidos NaN, infinito y ausencia), errores del proveedor, bypass CLI y wiring. Tests con reloj monotónico/sleep controlados para éxito/fallo, más de 60 polls, presupuesto fraccional, límite exacto, tiempo de consulta, diagnóstico y presupuesto independiente full/delta. Regresión de delta fire-and-forget y CLI. Verificar que seed repetido conserva valores personalizados y que errores distintos al conflicto se propagan. Ejecutar unit tests/linter del agente y checks TypeScript correspondientes al bootstrap.
