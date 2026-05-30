## ADDED Requirements

### Requirement: El agente recupera chunks RAG relevantes antes del análisis de expertos
El sistema SHALL ejecutar un nodo `rag_retrieve` en el grafo LangGraph después de `mcp_retrieve` y antes de los nodos experto. Este nodo SHALL descargar `latest/index.db` desde S3 y realizar búsqueda vectorial para cada archivo del commit, almacenando los chunks recuperados en el campo `rag_chunks` del estado del grafo.

#### Scenario: Recuperación exitosa de chunks RAG
- **WHEN** el nodo `rag_retrieve` se ejecuta y el índice `latest/index.db` existe en S3
- **THEN** el nodo descarga el índice, ejecuta búsqueda vectorial con query `"{path}\n{content[:400]}"` para cada archivo del commit, y escribe en `state.rag_chunks` una lista deduplicada de hasta 30 chunks con campos `file_path`, `chunk_text` y `distance`

#### Scenario: Degradación graceful cuando el índice no está disponible
- **WHEN** el nodo `rag_retrieve` no puede descargar `latest/index.db` de S3 (índice ausente, error de red o error de embedding)
- **THEN** el nodo escribe `state.rag_chunks = []`, registra un WARNING en el log y permite que el flujo continúe hacia los nodos experto sin interrumpir el análisis

#### Scenario: Degradación graceful cuando mcp_retrieve falló
- **WHEN** `state.mcp_error` está presente y el routing ya direccionó hacia `merge`
- **THEN** el nodo `rag_retrieve` no se ejecuta

### Requirement: Los expertos reciben chunks RAG como contexto adicional en el human message
Cada nodo experto SHALL incluir los chunks de `state.rag_chunks` en el human message como un bloque `=== RAG CONTEXT (codebase background) ===`, separado y después del bloque de archivos del commit. Si `rag_chunks` está vacío, el bloque SHALL omitirse del human message.

#### Scenario: Experto recibe contexto RAG no vacío
- **WHEN** `state.rag_chunks` contiene al menos un chunk
- **THEN** el human message del experto incluye primero los archivos del commit (formato `=== FILE: {path} ===`) seguido del bloque `=== RAG CONTEXT (codebase background) ===` con los chunks formateados como `--- {file_path} ---\n{chunk_text}`

#### Scenario: Experto no recibe contexto RAG vacío
- **WHEN** `state.rag_chunks` está vacío o ausente en el estado
- **THEN** el human message del experto contiene únicamente los archivos del commit, sin sección `=== RAG CONTEXT ===`

### Requirement: Los prompts de los expertos definen cómo interpretar el contexto RAG
Cada prompt de experto (`experts/*.md`) SHALL incluir una sección que instruya al LLM a:
- Usar el bloque `=== RAG CONTEXT ===` solo como contexto de fondo del codebase de la rama, no como archivos del commit.
- Escalar la severidad un nivel cuando una vulnerabilidad en los archivos del commit es amplificada por cómo ese código es llamado o expuesto en el contexto RAG.
- Reportar hallazgos exclusivamente sobre archivos del commit; no reportar vulnerabilidades cuya única evidencia esté en el contexto RAG.

#### Scenario: Vulnerabilidad amplificada por contexto RAG
- **WHEN** un archivo del commit tiene una vulnerabilidad (ej. función con SQL injection) y el contexto RAG muestra que esa función es llamada desde un endpoint público no autenticado
- **THEN** el experto escala la severidad del hallazgo un nivel (ej. de MEDIUM a HIGH) e incluye en la descripción la evidencia del contexto RAG que justifica el escalado

#### Scenario: Vulnerabilidad solo en contexto RAG (no reportar)
- **WHEN** el contexto RAG contiene código con una vulnerabilidad pero ese código no está en los archivos del commit
- **THEN** el experto no reporta esa vulnerabilidad

### Requirement: El adaptador S3SqliteRagContext encapsula descarga S3 y búsqueda vectorial
El sistema SHALL exponer el puerto `IRagContextPort` con método `search(query: str, k: int) -> list[dict]` en el dominio del agente. El adaptador `S3SqliteRagContextAdapter` SHALL implementar este puerto descargando `index.db` a un archivo temporal, cargando la extensión `sqlite-vec` y ejecutando búsqueda por similitud coseno.

#### Scenario: Búsqueda vectorial exitosa
- **WHEN** `IRagContextPort.search(query, k)` es invocado con un índice disponible
- **THEN** retorna una lista de dicts con `file_path`, `chunk_text` y `distance`, ordenada por distancia coseno ascendente, con longitud máxima `k`

#### Scenario: Búsqueda con índice ausente en S3
- **WHEN** `IRagContextPort.search(query, k)` es invocado y `latest/index.db` no existe en S3
- **THEN** retorna lista vacía `[]` sin lanzar excepción
