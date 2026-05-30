## 1. Dependencias y dominio

- [x] 1.1 Agregar `sqlite-vec` a `src/agent/pyproject.toml` (v0.1.9, misma que `src/rag-indexer/`); `uv.lock` actualizado; Dockerfile migrado de `python:3.13-alpine` a `python:3.13-slim-bookworm` (sqlite-vec requiere glibc); import de `sqlite_vec` movido a lazy dentro de `_query_db` para degradación graceful si no está instalado
- [x] 1.2 Crear `src/agent/src/code_analysis/domain/ports/rag_context_port.py` con `IRagContextPort`: métodos `configure(repository_url, branch)`, `search(query, k) -> list[dict]` y `close()`

## 2. Adaptador S3 + SQLite-vec

- [x] 2.1 Crear `src/agent/src/code_analysis/infra/adapters/s3_sqlite_rag_context_adapter.py`: `S3SqliteRagContextAdapter` implementa `IRagContextPort`
- [x] 2.2 Implementar `configure()` + descarga lazy de `{repo_path}/branches/{branch}/latest/index.db` desde S3 a archivo temporal en `/tmp`
- [x] 2.3 Implementar `search()`: carga `sqlite-vec` (lazy import), genera embedding con `OpenAIEmbeddings` y ejecuta query vectorial con sintaxis `k = ?` en el WHERE (requerida por vec0 virtual table al seleccionar columnas auxiliares)
- [x] 2.4 Degradación graceful en `search()`: captura `ClientError` S3 (404 → log info, otros → log warning), `ImportError` de sqlite_vec, errores de embedding y errores de sqlite; retorna `[]` en todos los casos
- [x] 2.5 Implementar `close()`: elimina el archivo temporal de `index.db`

## 3. Nodo LangGraph RagRetrievalNode

- [x] 3.1 Agregar campos `branch: str` y `rag_chunks: NotRequired[list[dict[str, Any]]]` a `AgentState` en `src/agent/src/code_analysis/infra/adapters/langgraph/state.py`; agregar parseo de `Branch:` en `LangGraphAgent._parse_message_content()`
- [x] 3.2 Crear `src/agent/src/code_analysis/infra/adapters/langgraph/nodes/rag_retrieval_node.py` con clase `RagRetrievalNode`
- [x] 3.3 Implementar `__call__`: llama `configure(repository_url, branch)` desde state, itera `state["files"]` (máx 10), construye query con `_build_file_query()` (extracción estructural vía `_structural_lines.extract_structural_lines()`), llama `search(query, k=3)`, deduplica por `chunk_text`, limita a 30 chunks totales
- [x] 3.4 Manejar `state.get("files", [])` vacío: retorna `{"rag_chunks": []}` sin llamar al adaptador

## 4. Integración en el workflow LangGraph

- [x] 4.1 Modificar `src/agent/src/code_analysis/infra/adapters/langgraph/workflow.py`: `LangGraphWorkflowBuilder` acepta `rag_node: RagRetrievalNode | None`; agrega nodo `rag_retrieve` si está presente
- [x] 4.2 Routing `mcp_retrieve → rag_retrieve` cuando hay archivos (success); `mcp_retrieve → merge` cuando hay `mcp_error` o sin archivos
- [x] 4.3 Edge `rag_retrieve → expert_prompt_hardening` (siempre; errores RAG se absorben dentro del nodo); fallback a routing directo sin RAG cuando `rag_node=None`

## 5. Modificar BaseExpertNode

- [x] 5.1 Agregar `_format_rag_chunks(chunks: list[dict]) -> str`: bloque `=== RAG CONTEXT ===` vacío si no hay chunks (no agrega ruido al prompt)
- [x] 5.2 Actualizar `__call__`: filtra `rag_chunks` con `should_analyze_file(chunk["file_path"])` y concatena `_format_rag_chunks(filtered_rag)` al human message
- [x] 5.3 (fix post-implementación) `_format_files` usa `_smart_truncate()`: presupuesto adaptativo por número de archivos (`_max_file_chars`: 30k/15k/8k/5k/3k chars según tamaño del commit) + truncación estructural (70% verbatim del inicio + 30% resumen de firmas del resto); previene `context_length_exceeded` en commits grandes

## 6. Wiring en main.py

- [x] 6.1 Leer `embedding_provider`, `embedding_model` y `embedding_api_key` desde `configuration_provider` en `src/agent/src/main.py`
- [x] 6.2 Instanciar `S3SqliteRagContextAdapter` (con S3 client, `TITVO_RAG_INDEXER_BUCKET`, provider, model y api_key); log warning si falta configuración (RAG deshabilitado, no falla)
- [x] 6.3 Instanciar `RagRetrievalNode` y pasarlo a `create_langgraph_agent()` → `LangGraphAgent.__init__()` → `create_workflow()`

## 7. Actualizar prompts de expertos

- [x] 7.1 Sección `## RAG Context` en `experts/prompt_hardening.md`: instrucciones para escalar severidad si RAG confirma impacto amplio; regla de no-reporte exclusivo desde RAG
- [x] 7.2 Misma sección en `experts/owasp_api.md`: contexto de middlewares/guards/servicios; escalado BOLA por uso multi-punto
- [x] 7.3 Misma sección en `experts/owasp_web.md`: flujo de datos desde fuentes user-controlled; citar funciones de sanitización existentes si el commit las omite
- [x] 7.4 Misma sección en `experts/devsecops.md`: nota sobre RAG vacío frecuente cuando el commit no toca `.yml`/`Dockerfile`
- [x] 7.5 Misma sección en `experts/code_vulnerabilities.md`: escalar si función vulnerable es expuesta por endpoints públicos según RAG

## 8. Tests unitarios

- [x] 8.1 `tests/unit/test_rag_retrieval_node.py`: 6 casos para `RagRetrievalNode` (exitoso, error en search, sin archivos, deduplicación, límite 30 chunks, configure llamado con repo+branch correctos)
- [x] 8.2 `tests/unit/test_expert_nodes.py`: tests de `_format_rag_chunks()` (con chunks, vacío, file_path ausente) + `_smart_truncate()` (sin truncar, flag truncado, dentro de budget, líneas estructurales preservadas en tail, no-estructurales omitidas) + `_build_file_query()` (extrae estructurales, fallback sin estructurales)
- [x] 8.3 `tests/unit/test_langgraph_workflow.py`: verifica que `rag_retrieve` aparece en el grafo cuando se pasa `rag_node`; verifica que no aparece cuando `rag_node=None`
- [x] 8.4 (nuevo) `tests/unit/test_expert_nodes.py::TestStructuralLines`: 40+ casos de `is_structural()` cubriendo Python, TypeScript, Java, Kotlin, Go, Rust, C#, Ruby, PHP, Terraform, Dockerfile, SQL, C/C++, y casos negativos

## 9. Módulo compartido de detección estructural

- [x] 9.1 Crear `src/agent/src/code_analysis/infra/adapters/langgraph/nodes/_structural_lines.py`: regex comprehensiva `_STRUCTURAL_RE` + funciones `is_structural(line)` y `extract_structural_lines(content, max_lines)` usadas por `RagRetrievalNode` (query embedding) y `BaseExpertNode` (truncación); cubre 11 categorías: modificadores de acceso, funciones, tipos/clases, módulos/namespaces, imports, JS/TS, decoradores, IaC, Dockerfile, SQL DDL, Shell

## 10. Documentación

- [x] 10.1 Actualizar `docs/architecture.md`: diagrama LangGraph actualizado con nodo `rag_retrieve`, sección de rol activo del RAG, campo `branch` en AgentState, tabla de componentes con RAG Context Port y Adapter
- [x] 10.2 Actualizar `docs/rag-indexer.md`: sección completa de consumo del `index.db` por el agente (configure+descarga, búsqueda vectorial, post-filtrado por experto, entrega al LLM, limpieza, degradación graceful)
- [x] 10.3 Actualizar `docs/prompts.md`: sección de contexto RAG en expertos (estructura del bloque `=== RAG CONTEXT ===`, instrucciones de interpretación, regla de no-reporte independiente, caso sin RAG)
