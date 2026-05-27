## Context

El `rag-indexer` persiste índices RAG en S3 bajo el prefijo `{repo}/latest/`, un único slot global. Cuando se indexa `main`, ese slot apunta al HEAD de `main`. Si un commit de una PR todavía no fue mergeada se analiza con delta-index, el índice base (sobre el que se aplica el diff) proviene de `main` y puede no incluir archivos específicos de la rama.

Problema secundario: el agente LangGraph ejecuta `mcp_retrieve` y luego busca en el índice RAG, pero cuando se opera en modo delta, los archivos recuperados desde MCP representan el estado exacto del commit y son más confiables que el vector store para esos paths.

Componentes afectados: `src/rag-indexer` (indexer Python) y `src/agent` (agente LangGraph TypeScript).

## Goals / Non-Goals

**Goals:**
- Segmentar el índice S3 por rama para evitar colisiones entre `main` y ramas de PR.
- Detectar automáticamente la ausencia de índice para una rama y forzar un full-index previo al análisis delta.
- Propagar al agente un indicador de que opera sobre un delta, para que los archivos del MCP tengan precedencia sobre el índice RAG para los paths modificados.

**Non-Goals:**
- No se implementará merge o consolidación de índices entre ramas.
- No se cambia la lógica de embeddings, chunking, ni proveedores de modelos.
- No se modifica el protocolo MCP ni los contratos de la API Gateway.
- No se añade soporte para branches que no sean de Git (tags, SHAs flotantes, etc.).

## Decisions

### D1: Prefijo S3 siempre por rama, sin fallback legacy

**Decisión:** El prefijo es siempre `{repo}/branches/{branch}/latest/`. `TITVO_BRANCH` es obligatorio en todos los modos. Si no se provee, el sistema falla con error explícito.

**Comportamiento por combinación de variables:**
| Variables presentes | Modo | Comportamiento |
|---------------------|------|----------------|
| `TITVO_BRANCH` solo | Full | Resuelve HEAD de la rama, indexa completo |
| `TITVO_BRANCH` + `TITVO_COMMIT_SHA` | Delta | SHA es el commit objetivo, branch determina el prefijo S3 |
| Solo `TITVO_COMMIT_SHA` | — | **Error explícito**: branch es requerido |
| Ninguna | — | Error (comportamiento actual) |

**Rationale:** Sin fallback se evita ambigüedad sobre qué índice se está leyendo/escribiendo. Los índices bajo `{repo}/latest/` quedan huérfanos en S3 (inofensivos); no se migran.

**Alternativa descartada:** Mantener `{repo}/latest/` como fallback para compatibilidad con índices existentes — descartado por preferencia explícita del equipo de no mantener código legacy.

### D2: Verificación de índice faltante — diferido a segunda iteración

**Decisión:** La lógica de "verificar si existe índice para la rama y forzar full-index si no" se implementa en una segunda iteración junto con el flujo `src/api → agent`.

**En esta iteración:** el rag-indexer recibe explícitamente el modo correcto desde el exterior (el caller es responsable de elegir full vs delta). El fallback interno de delta→full cuando no hay `latest/meta.json` se **elimina** — si no hay índice base, el modo delta falla con error explícito.

**Rationale:** Mantener el fallback interno significaría que el indexer toma decisiones sobre la rama que no le corresponden. Al eliminarlo, el contrato es claro: delta requiere un índice previo para la rama.

### D3: Indicador `is_delta` en el estado del grafo LangGraph

**Decisión:** El estado del grafo incluirá el campo `is_delta: boolean` y `delta_paths: string[]` (paths modificados en el commit). Los nodos de análisis experto leerán este campo para saber que los archivos en `state.files` son la fuente de verdad y no deben ser reemplazados por búsquedas en el vector store para esos paths.

**Rationale:** Es explícito, testeable y no altera el contrato de `mcp_retrieve`. Alternativa descartada: que el nodo de fusión infiriera el modo delta por la ausencia de ciertos campos — frágil y no documentable en specs.

## Risks / Trade-offs

- **[Riesgo] Prefijo S3 cambia → índices existentes quedan huérfanos** → Mitigación: los índices bajo `{repo}/latest/` se ignorarán naturalmente; el primer análisis de `main` regenerará el índice. No hay pérdida de funcionalidad, solo re-indexación.
- **[Riesgo] El caller necesita permisos S3 para verificar `meta.json`** → Mitigación: la lectura de `meta.json` ya ocurre dentro del rag-indexer; se expone como endpoint de estado o se reutiliza el adaptador S3 existente desde el servicio de análisis.
- **[Trade-off] La verificación pre-análisis agrega latencia** → El full-index de una rama nueva puede tardar varios minutos. Se acepta como comportamiento de primera ejecución; las ejecuciones subsiguientes serán delta y rápidas.

## Migration Plan

### Iteración 1 (esta): solo rag-indexer

1. Actualizar `S3ArtifactStoreAdapter`: prefijo siempre `{repo}/branches/{branch}/latest/`; `branch` es requerido.
2. Actualizar el puerto `ArtifactStorePort` para incluir `branch: str` (obligatorio) en los métodos afectados.
3. Actualizar `IndexRepositoryUseCase`: recibir y propagar `branch`; eliminar fallback delta→full.
4. Actualizar `main.py`: `TITVO_BRANCH` obligatorio; `TITVO_BRANCH` + `TITVO_COMMIT_SHA` → delta; solo `TITVO_BRANCH` → full; solo `TITVO_COMMIT_SHA` → error.
5. Actualizar tests unitarios.
6. Ejecutar ruff y corregir errores.
7. Actualizar `docs/rag-indexer.md` con diagramas de secuencia del nuevo flujo.

### Iteración 2 (diferida): orquestador + agente

- Verificación S3 + full-index automático desde `src/api`.
- `is_delta` + `delta_paths` en estado LangGraph.
- Precedencia MCP sobre RAG en nodos experto.

Rollback: revertir los cambios de prefijo S3 restaura el comportamiento previo. Los índices bajo el nuevo prefijo quedan en S3 pero son inofensivos.

## Open Questions

- ¿`delta_paths` (iteración 2) debe incluir solo los paths `modified+added` o también `deleted`? Los archivos eliminados no tienen contenido en MCP, por lo que probablemente se excluyan de `delta_paths`. **Resolver antes de iniciar iteración 2.**
