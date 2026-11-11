# Tasks

## 1. Implementación
- [x] 1.1 Separar validación y selección UTF-8, preservar duplicados y validar batch completo; verificar tests de regresión.
- [x] 1.2 Generar pruebas unitarias para binarios, UTF-8, manifiestos y batches múltiples; ejecutar pytest.
- [x] 1.3 Validar documentación de bytes.decode con find-docs (CPython 3.13.9, Unicode HOWTO).
- [x] 1.4 Ejecutar suite completa, ruff y openspec validate --strict (501 passed, 1 skipped).

## 2. Documentation
- [x] 2.1 Actualizar README del agente con exclusiones y error sin texto; revisar contrato descrito.
- [x] 2.2 Actualizar docs/architecture.md y generar diagrama de secuencia para mantenimiento; revisar flujo de integridad antes de selección.

## Workflow follow-up
- Commit y push; verificar GitHub Action del commit desplegado antes de avisar al usuario.
