## Context

El agente Titvo construye un índice vectorial SQLite-vec del codebase de la rama en S3 (vía `rag-indexer`) y lo mantiene actualizado con deltas post-scan. Sin embargo, el grafo LangGraph actual solo usa ese índice para verificar que existe antes del análisis; los cinco nodos expertos nunca consultan el vector store. El resultado es que los expertos analizan únicamente los archivos del commit, sin visibilidad de cómo ese código interactúa con el resto del proyecto.

El `S3ArtifactStoreAdapter` del rag-indexer ya expone `download_latest_db()` y `SqliteVecStoreAdapter` expone `search(query, k)`. El agente tiene acceso al bucket S3 vía `TITVO_RAG_INDEXER_BUCKET`. La única pieza faltante es conectar estas piezas en el flujo LangGraph.

## Goals / Non-Goals

**Goals:**

- Agregar un nodo `rag_retrieve` en LangGraph que descargue `latest/index.db` y haga búsqueda vectorial por cada archivo del commit.
- Exponer los chunks recuperados a todos los expertos como bloque `=== RAG CONTEXT ===` en el human message.
- Mantener degradación graceful: si el índice no está disponible, el análisis continúa con comportamiento actual.
- Definir en los prompts de expertos cómo interpretar el contexto RAG y cuándo escalar severidad.

**Non-Goals:**

- Reemplazar MCP como fuente de los archivos del commit.
- Crear tools MCP para búsqueda vectorial.
- Modificar el rag-indexer.
- Optimizar el modelo de embedding (se reutiliza el configurado para el rag-indexer).

## Decisions

### D1: Búsqueda vectorial dentro del nodo, no vía MCP

**Decisión:** El nodo `rag_retrieve` descarga `index.db` y ejecuta `sqlite-vec` directamente en el proceso del agente, en lugar de exponer la búsqueda como tool MCP.

**Rationale:** Agregar una tool MCP requeriría un endpoint nuevo en el gateway, serialización/deserialización adicional, y latencia de red por cada búsqueda. El nodo descarga el DB una vez y ejecuta todas las búsquedas localmente. El índice ya está en S3 accesible desde el Batch job del agente.

**Alternativa descartada:** Tool MCP `rag.search` → mayor complejidad operacional sin beneficio claro.

### D2: Query por archivo del commit + post-filtrado por experto

**Decisión:** Se genera una query de búsqueda por cada archivo del commit: `"{path}\n{content[:400]}"`. Los resultados se deduplican y se limitan a 30 chunks totales (k=3 por archivo, máximo 10 archivos × 3). Cada nodo experto aplica su `should_analyze_file()` sobre el `file_path` de los chunks para filtrar los que son relevantes a su dominio antes de incluirlos en el human message.

**Rationale:** Una query por archivo recupera el código del codebase que es semánticamente relacionado con cada archivo modificado — exactamente el contexto que los expertos necesitan para entender cómo interactúa ese código con el resto del proyecto. El post-filtrado por `file_path` es de costo cero (ningún embedding adicional) y reduce el ruido para expertos con dominio acotado (ej. `devsecops` filtra a `.yml`/`Dockerfile`; `owasp_web` a `.ts`/`.html`). Los expertos que analizan todos los archivos (`code_vulnerabilities`, `prompt_hardening`) reciben los 30 chunks sin filtrar.

**Alternativa descartada:** Una sola query global por commit → menor precisión; query por experto en runtime → multiplicaría las llamadas de embedding y requiere inyectar el puerto RAG en cada nodo experto.

### D3: Nuevo puerto de dominio `IRagContextPort` en el agente

**Decisión:** Se crea `IRagContextPort` en `code_analysis/domain/ports/` con el método `search(query, k)`. El adaptador `S3SqliteRagContextAdapter` implementa descarga S3 + búsqueda sqlite-vec.

**Rationale:** Consistente con la arquitectura hexagonal del agente (`IRagIndexStatusPort`, `ITaskRepository`, etc.). Permite testear el nodo con un mock del puerto sin depender de S3 ni sqlite-vec.

**Alternativa descartada:** Instanciar `SqliteVecStoreAdapter` directamente en el nodo → acopla el nodo a la infra, dificulta tests.

### D4: Mismo modelo de embedding que el rag-indexer

**Decisión:** El adaptador lee `embedding_model` y `embedding_api_key` de DynamoDB (mismas claves que usa el rag-indexer). Si no están configuradas, `rag_chunks = []`.

**Rationale:** La búsqueda vectorial requiere el mismo espacio de embedding usado al indexar. Reutilizar la configuración existente elimina divergencias. La degradación graceful protege contra entornos donde las claves no están configuradas.

### D5: `rag_retrieve` siempre se ejecuta tras `mcp_retrieve`

**Decisión:** El routing del grafo va `mcp_retrieve → rag_retrieve → expertos` (o `→ merge` si hay `mcp_error`). El nodo RAG se ejecuta incluso si `mcp_retrieve` tuvo éxito parcial.

**Rationale:** Si `mcp_retrieve` falla, el routing ya salta a `merge`. Si tiene éxito, `rag_retrieve` siempre corre: en el peor caso devuelve `rag_chunks = []` sin afectar el resultado.

## Risks / Trade-offs

**[Latencia adicional]** Descargar `index.db` desde S3 puede agregar 2-10 segundos dependiendo del tamaño del índice y la red del Batch job. → Mitigación: el índice ya está disponible en S3 antes del análisis (garantizado por `_ensure_rag_index`). El contenedor Batch es efímero y no persiste entre jobs, por lo que no hay oportunidad de caché entre ejecuciones; la descarga a `/tmp` ocurre una sola vez por job y el archivo vive durante toda su ejecución.

**[Costo de embeddings]** Generar embeddings para las queries (un embedding por archivo del commit) tiene costo en tokens de la API de OpenAI. → Mitigación: el límite de 10 archivos × 1 embedding = máximo 10 llamadas de embedding por scan; costo marginal.

**[Context window]** 30 chunks de ~200 tokens cada uno = ~6k tokens adicionales por experto. Con modelos de 128k tokens de contexto esto es negligible, pero puede afectar modelos con ventanas menores. → Mitigación: el límite de 30 chunks es configurable via constante en el nodo.

**[Relevancia del RAG]** Si el índice está desactualizado (rama con muchos commits desde el último full index), el contexto recuperado puede no corresponder al estado actual del codebase. → Mitigación: el delta post-scan mantiene el índice actualizado; esta es una limitación conocida y aceptable.

**[sqlite-vec en el agente]** Agregar `sqlite-vec` como dependencia del agente introduce una extensión nativa C. → Mitigación: la imagen Docker del agente puede preinstalar la extensión igual que el rag-indexer; el `pyproject.toml` la gestiona.

## Migration Plan

1. Los cambios son aditivos: `rag_chunks` es `NotRequired` en `AgentState` y los expertos reciben bloque RAG vacío si no hay chunks.
2. Deployar nueva imagen del agente con el nodo `rag_retrieve` activo.
3. No se requiere migración de datos ni cambios en el rag-indexer.
4. **Rollback:** revertir a imagen anterior del agente; el índice S3 permanece intacto.

## Open Questions

- ¿Cuál es el tamaño típico de `index.db` en producción? Si supera 500 MB, evaluar si descargar a `/tmp` del Batch job es viable o si conviene un endpoint de búsqueda dedicado.
- ¿Deberían los expertos con dominio acotado (`devsecops`, `owasp_web`) hacer queries RAG propias con términos de su dominio cuando el commit no toca sus tipos de archivo? El post-filtrado actual puede dejarlos sin contexto RAG en esos casos, aunque también significa que el commit no impacta su área. Evaluar con evidencia de producción si esto genera falsos negativos relevantes.
