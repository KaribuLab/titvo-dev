# Design

## Context
Ver proposal.md. La decodificación actual aborta la recuperación completa; el repositorio agrega varios paquetes.

## Goals / Non-Goals
Separar integridad, selección de texto y validación de batch. No alterar contenido ni ampliar codificaciones admitidas.

## Decisions
- Separar lectura validada de bytes y conversión a archivos analizables; conservar read_snapshot como fachada.
- Validar rutas, límites y manifiesto antes de filtrar. Detectar duplicados entre paquetes usando todas las rutas originales.
- Excluir bytes NUL (heurística binaria) y UnicodeDecodeError, con WARNING de ruta y motivo sin contenido. No usar errors=ignore/replacement ni extensiones como criterio.
- Un paquete no vacío con solo exclusiones devuelve lista vacía; el repositorio falla si la unión completa no aporta texto. Paquetes realmente vacíos siguen siendo inválidos.

## Risks / Trade-offs
- Texto UTF-16 y texto UTF-8 con NUL se excluyen → motivo explícito en logs; contrato UTF-8.
- Binarios válidos como UTF-8 sin NUL pueden pasar → heurística acotada, sin prometer detección universal.

## Migration Plan
Pruebas y lint locales; commit y push del agente; desplegar por el workflow de main y comprobar su resultado. Rollback revirtiendo el commit.
