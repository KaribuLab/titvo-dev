## ADDED Requirements

### Requirement: Estado del grafo incluye indicador de modo delta

El estado del grafo LangGraph SHALL incluir los campos:

- `is_delta: boolean` — indica que el commit analizado fue indexado como delta.
- `delta_paths: string[]` — lista de paths `added` y `modified` del diff del commit (no incluye `deleted`).

Estos campos SHALL ser poblados antes de que el grafo comience su ejecución.

#### Scenario: Análisis delta activa indicador

- **WHEN** el agente es invocado con un commit que fue indexado en modo delta
- **THEN** `state.is_delta` es `true` y `state.delta_paths` contiene los paths modificados/añadidos del commit

#### Scenario: Análisis full no activa indicador

- **WHEN** el agente es invocado con un commit que fue indexado en modo full
- **THEN** `state.is_delta` es `false` y `state.delta_paths` es un array vacío

### Requirement: Los archivos del MCP tienen precedencia sobre el RAG para delta_paths

Cuando `state.is_delta` es `true`, los nodos experto SHALL tratar los archivos presentes en `state.files` (obtenidos desde MCP `git.commit-files`) como la fuente de verdad canónica para los paths listados en `state.delta_paths`.

Si el vector store RAG devuelve resultados para algún path listado en `delta_paths`, esos resultados SHALL ser descartados en favor del contenido de `state.files`.

#### Scenario: Archivo en delta_paths presente en state.files

- **WHEN** `is_delta` es `true` y un path está en `delta_paths` y en `state.files`
- **THEN** el nodo experto usa el contenido de `state.files` para ese path, ignorando cualquier resultado del vector store RAG

#### Scenario: Archivo en delta_paths ausente en state.files

- **WHEN** `is_delta` es `true` y un path está en `delta_paths` pero NO en `state.files` (ej. fallo de MCP para ese archivo)
- **THEN** el nodo experto puede usar el resultado del RAG como fallback, con advertencia en logs

#### Scenario: Archivo fuera de delta_paths en modo delta

- **WHEN** `is_delta` es `true` y un path NO está en `delta_paths`
- **THEN** el nodo experto usa el RAG normalmente para ese path (es contexto base, no archivo modificado)
