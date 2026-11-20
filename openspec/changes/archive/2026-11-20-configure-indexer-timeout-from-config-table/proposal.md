# Proposal

## Why

El agente interrumpe la espera del indexador tras 60 intentos de 10 segundos aunque el job siga RUNNING, como ocurrió el 27 de octubre de 2026. Operación necesita ajustar ese plazo desde la tabla de configuración sin recompilar ni cambiar variables de entorno.

## What Changes

- Leer `rag_indexing_timeout_seconds` de la tabla existente mediante el proveedor de configuración del agente e inyectarlo al caso de uso.
- Sustituir el máximo fijo de intentos por un presupuesto temporal por job para la indexación full inicial y el delta bloqueante de un full scan.
- Validar un número finito positivo de segundos y registrar plazo y tiempo transcurrido junto al job ID.
- Si falta el parámetro o está vacío, usar 600 segundos para compatibilidad con configuraciones antiguas. Valores no vacíos inválidos producen error explícito; no hay override por entorno. Los scans CLI no lo requieren.
- Preparar bootstrap local y procedimiento de ajuste en ambientes existentes, preservando valores personalizados.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `rag-pre-scan-full-indexing`: espera bloqueante con timeout configurable por tabla, validación y aplicación a cada job esperado.

## Impact

`src/agent/src/main.py`, `AnalyseCodeUseCase`, pruebas unitarias del agente, `localstack/app/setup.ts` y documentación operativa. Se reutiliza `AwsConfigurationAdapter`; no se agregan dependencias ni permisos. La tabla almacena `parameter_id=rag_indexing_timeout_seconds` y `value` como string.

## Non-goals

Calcular el timeout según volumen de datos (otro change posterior), cambiar el intervalo normal de polling, cancelar jobs Batch, cambiar deadlines de infraestructura/LLM/análisis, o modificar el delta fire-and-forget de scans por commit.
