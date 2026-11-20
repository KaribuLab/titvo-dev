# Proposal

## Why
Un binario enviado por la CLI provoca UnicodeDecodeError y aborta todo el scan. El agente debe aplicar una defensa por archivo sin debilitar la integridad del snapshot.

## What Changes
- Excluir contenido binario (bytes NUL) y no UTF-8 después de validar integridad, registrando ruta y motivo.
- Continuar con los textos válidos de todos los paquetes; fallar claramente si el batch no contiene ninguno.
- Mantener detección de duplicados incluso entre archivos excluidos.

## Capabilities
### New Capabilities
Ninguna.
### Modified Capabilities
- `cli-snapshot-analysis`: recuperación tolerante a archivos no analizables con integridad estricta.

## Impact
Adaptador de snapshots del agente, pruebas y documentación. Sin nuevas dependencias ni cambios de API.

## Non-goals
Modificar la CLI, transcodificar archivos o ignorar errores de integridad.
