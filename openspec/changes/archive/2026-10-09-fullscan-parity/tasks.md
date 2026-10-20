## 1. Clasificador de runtime

- [x] 1.1 Crear `domain/services/runtime_classifier.py`: enum `Runtime`, `ProjectProfile`, `build_project_profile(files)` y `classify(path, content, profile) -> list[Runtime]` con la precedencia de D1 (path → extensión → imports multi-señal → perfil → directorio → unknown)
- [x] 1.2 Tests de tabla `tests/unit/test_runtime_classifier.py` cubriendo cada escenario de `file-runtime-classification` (React web, NestJS, RN con y sin import, react+express → ambos, infra, test, unknown, perfil frontend/mobile/vacío) y casos de los repos Titvo
- [x] 1.3 Crear `nodes/classify_runtime_node.py`: construye perfil, anota `runtimes`, calcula `expert_metadata.coverage` y `project_profile`, aplica invariante (agrega `unknown` + WARNING si un archivo queda sin experto de dominio)
- [x] 1.4 Test del nodo: `runtimes` presente en todos los archivos, `files_without_domain_expert == 0`, perfil registrado

## 2. Chunking y batching

- [x] 2.1 Crear `domain/services/batch_planner.py`: `Chunk`, `Batch`, `split_file(file, cap, overlap)` con corte en límite de línea, prefijo estructural (máx 60 líneas, no afecta offset) y `start_line/end_line`; `plan(chunks, batch_budget)` greedy ordenado por `(runtime primario, path, chunk_index)`
- [x] 2.2 Tests `tests/unit/test_batch_planner.py`: archivo ≤ cap → 1 chunk; 80k → 3 chunks con cobertura total y solape ≈ 5k; prefijo no cambia `start_line`; lote único para commit chico; 7 lotes para 1.4M; determinismo
- [x] 2.3 Leer `TITVO_EXPERT_FILE_CAP_CHARS`, `TITVO_EXPERT_BATCH_BUDGET_CHARS`, `TITVO_EXPERT_CHUNK_OVERLAP_CHARS`, `TITVO_EXPERT_MAX_CONCURRENCY` en `main.py` con fallbacks 30000 / 200000 / 5000 / 4 y pasarlos a `create_expert_nodes`
- [x] 2.4 En `base_expert_node.py`: eliminar `_compute_file_budgets`, `_GLOBAL_BUDGET_CHARS`, `_MIN_FILE_CHARS`, `_smart_truncate`; `_format_batch(batch)` emite `=== FILE: {path} [runtime: {primary}] [lines a-b of N] ===`
- [x] 2.5 En `base_expert_node.py`: ejecutar lotes con `asyncio.gather` bajo semáforo compartido, retry con backoff (3 intentos), ensamblar por `batch_index`; corregir `line` con `start_line - 1`; poblar `metadata = {expert, batch_index, chunk_index}`
- [x] 2.6 Lote fallido o respuesta no parseable → `expert_errors` + `failed_batches` con `paths`; los demás lotes se conservan
- [x] 2.7 Reescribir `tests/unit/test_base_expert_node.py` (mismo archivo → mismos chunks en 3 y 400 archivos; sin truncado; offset de líneas) y actualizar `test_expert_nodes.py` (multi-lote, orden, lote fallido → `failed_batches`)

## 3. Selección por runtime sin fallback

- [x] 3.1 En `base_expert_node.py`: reemplazar `get_file_patterns`/`should_analyze_file`/`_filter_files` por `get_runtimes()` y `_select_files` por intersección; sin archivos → no invocar LLM, `expert_metadata[name] = {"files_analyzed": 0, "skipped": true}`
- [x] 3.2 En `expert_nodes.py`: `get_runtimes()` por experto según tabla D2 (incluye `test` en `devsecops`); borrar globs
- [x] 3.3 Filtrar `rag_chunks` por experto clasificando `file_path` del chunk con el mismo clasificador y perfil
- [x] 3.4 Actualizar `tests/unit/test_expert_nodes.py`: mapping por experto, `apiClient.ts` llega a `owasp_api` en commit y full, `["mobile","browser"]` llega a mobile y web, `owasp_mobile` se salta sin LLM, `.tsx` web no llega a mobile

## 4. Fan-out paralelo y estado con reducers

- [x] 4.1 En `state.py`: `issues`, `expert_errors`, `failed_batches` como `Annotated[list, operator.add]`; `expert_metadata` con reducer de merge de dicts; `files` con `runtimes`
- [x] 4.2 Expertos devuelven sólo su delta
- [x] 4.3 En `workflow.py`: nodo `classify_runtime` tras `rag_retrieve` (o `mcp_retrieve`); edges `classify_runtime → cada experto` y `cada experto → merge`; quitar cadena secuencial
- [x] 4.4 Routing post-MCP: error o sin archivos → `merge`; si no → `rag_retrieve` o `classify_runtime`
- [x] 4.5 Actualizar `tests/unit/test_langgraph_workflow.py` a la topología nueva

## 5. Consolidación en dos niveles

- [x] 5.1 En `merge_findings_node.py`: ordenar `state.issues` por `(expert, batch_index, path, line, category, title)` al inicio
- [x] 5.2 L1: `findings_merger.py` con clave `(path, line, category, code normalizado)`, severidad mayor, `metadata.merged_from`; usarlo desde `merge`
- [x] 5.3 L2: agrupar por `path`; grupos de 1 directo; grupos ≥ 2 en chunks ≤ 20; validar `source_ids` (cobertura exacta, severidad = máx fuentes, path/line/code de fuentes); rechazo → L1 del grupo; métricas `expert_metadata.consolidation`
- [x] 5.4 `merge` deja de devolver `issues`; `status` nunca `COMPLETED` con `incomplete`; `final_output` incluye `incomplete`/`error` cuando aplica
- [x] 5.5 Reescribir `prompts/findings_consolidation.md`: regla conservadora misma causa raíz/mismo archivo, `source_ids` obligatorio, sin "agresiva" ni fusión cross-file
- [x] 5.6 Actualizar `tests/unit/test_findings_merger.py` y tests de merge: 120 findings / 40 archivos → llamadas por archivo ≤ 20; grupo con `source_ids` incompletos rechazado; fallo en un grupo no afecta a otros; `a.ts`/`b.ts` quedan 2 issues; status WARNING con `incomplete` sin issues
- [x] 5.7 `tests/unit/test_prompts.py`: el prompt de consolidación contiene `source_ids` y no "agresiva"

## 6. Scan incompleto de punta a punta

- [x] 6.1 `ResultDto`: campos opcionales `error` e `incomplete`; test del use case construyendo `ResultDto` desde `final_output` con `error` (caso MCP) y con `incomplete`
- [x] 6.2 `LambdaReportRepository.create_report`: incluir `incomplete` en el payload cuando exista; test
- [x] 6.3 `src/mcp/issue-report`: DTO acepta `incomplete` opcional; template renderiza banner con `message` y lista de archivos antes de los hallazgos; test unitario con y sin `incomplete`
- [x] 6.4 Verificar que `task.result` conserva `incomplete` (test del use case)

## 7. Reproducibilidad y cierre

- [x] 7.1 Actualizar `tests/unit/test_reproducible_scan.py` al fan-out: modelo canned con latencias distintas por experto/lote, `final_output` byte-idéntico entre corridas
- [x] 7.2 `ruff check` y `pytest` en verde en `src/agent`; `npm test` en verde en `src/mcp/issue-report`
- [ ] 7.3 Verificación en LocalStack: commit de 3 archivos, full de 100+ archivos, lote forzado a fallar (banner en reporte, `incomplete` en Dynamo); registrar duración y lotes en Langfuse
- [x] 7.4 Documentar en `src/agent/README.md` variables nuevas y topología; anotar duración medida

## 8. Seguimiento post-despliegue (hallazgos del primer fullscan en prod)

- [ ] 8.1 Excluir archivos no analizables antes de `classify_runtime`: binarios por extensión/magic bytes (`.jpg .png .gif .webp .svg? .pdf .woff* .ttf .ico .zip .mp4 ...`) y lockfiles (`pnpm-lock.yaml`, `package-lock.json`, `yarn.lock`, `uv.lock`, `poetry.lock`, `Cargo.lock`, `Gemfile.lock`, `composer.lock`, `go.sum`). Registrar los excluidos en `expert_metadata.excluded_files` y no contarlos como lotes fallidos (el fullscan de prod falló 7/393 lotes sólo por `assets/img/hero-bg.jpg` y `pnpm-lock.yaml`)
- [ ] 8.2 Revisar mapeo de líneas en archivos chunked: varios issues de `components/claims/Tracking.vue` salieron con `line: 2` y `code` con `...` (evidencia concatenada). Opciones: numerar líneas en el cuerpo del chunk, exigir `code` como fragmento literal de una sola línea y validar `code in chunk.body` al parsear, o descartar `line` fuera de rango y marcarla como no confiable
- [ ] 8.3 Test de regresión con un archivo > 3 chunks verificando que cada issue cae en el rango absoluto del chunk que lo reportó
