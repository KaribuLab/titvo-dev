## Context

El grafo actual es `mcp_retrieve → rag_retrieve → 6 expertos en secuencia → merge`. Cada experto
recibe **todos** sus archivos en una sola llamada LLM, con un presupuesto global de 200k chars
(`_GLOBAL_BUDGET_CHARS`) repartido proporcionalmente. En commit (2-10 archivos) cada archivo llega
casi íntegro; en full (100-500 archivos) el shrink deja ~500 chars por archivo y el floor de 3k se
descarta cuando no cabe. La selección de archivos por experto usa globs por nombre
(`*api*`, `*route*`, `*.js`…) con fallback "si nada matchea, analiza todo", lo que produce cobertura
distinta por modo sin intención. La consolidación final es una única llamada LLM con prompt
"consolida de forma agresiva" sobre todos los findings. Un lote de experto que falla sólo se
registra en logs; el resultado sigue diciendo `COMPLETED`.

Restricciones:

- **Scan reproducible** (`tests/unit/test_reproducible_scan.py`): mismo input → mismo JSON byte a
  byte. Cualquier paralelismo debe agregar en orden determinista.
- **Schema de `ExpertIssue` fijo**: viaja a `issue-report`, notificaciones y Code Insights. No se toca.
- **`ResultDto` es dataclass con campos fijos** y el use case hace `ResultDto(**{**result, ...})`.
  Cualquier clave extra en `final_output` (hoy `error` cuando falla MCP) lanza `TypeError`.
- **`AgentState` sin reducers**: hoy los nodos hacen `state["issues"] + nuevos` porque corren en
  secuencia. Con fan-out paralelo LangGraph exige reducers para claves escritas por varios nodos.
- Costo LLM declarado no restrictivo; sin timeout configurado en el job de AWS Batch.
- Repos objetivo: 100-500 archivos.

## Goals / Non-Goals

**Goals:**

- Que un archivo reciba el mismo contexto al LLM esté en un commit de 3 archivos o en un full de 500,
  y que ese contexto sea el archivo **completo** (no truncado).
- Que cada experto vea el mismo conjunto de archivos (por tipo) en commit y en full, y que un error
  de clasificación nunca reste expertos.
- Que ningún finding de un experto desaparezca en la consolidación sin estar representado.
- Que un scan con lotes fallidos lo diga explícitamente en el resultado y en el reporte.
- Mantener reproducibilidad byte a byte.

**Non-Goals:**

- Cambiar reglas de detección de los prompts de expertos (change `client-side-trust-boundary`).
- Cambios en MCP `git.commit-files`, RAG o API trigger.
- Clasificación por LLM.

## Decisions

### D1. Clasificador de runtime determinista, multi-label, con perfil de proyecto

Nuevo `domain/services/runtime_classifier.py`:

- `Runtime ∈ {browser, server, mobile, infra, test, config, unknown}`.
- `build_project_profile(files) -> ProjectProfile`: una pasada sobre todos los archivos buscando
  señales de repo: `package.json` con `react-native`/`expo` → `mobile_js`; con `react`/`vue`/
  `svelte`/`next`/`@angular` y sin `express`/`fastify`/`@nestjs`/`koa` → `frontend_js`; con los
  de servidor y sin los de frontend → `backend_js`; `pubspec.yaml` → `flutter`; `Podfile`/
  `*.xcodeproj` → `ios`; `build.gradle` con `com.android` → `android`. En commit mode el
  `package.json` puede no venir: perfil vacío, clasificación per-file.
- `classify(path, content, profile) -> list[Runtime]`: lista ordenada, el primero es el runtime
  primario (se muestra en el prompt). Precedencia:
  1. **Path**: `test/ tests/ __tests__/ *.spec.* *.test.* *_test.go` → `[test]`.
     `.github/ k8s/ helm/ terraform/ cloudformation/` → `[infra]`.
  2. **Extensión inequívoca**: `.tf .tfvars .hcl Dockerfile* docker-compose* .yml .yaml
     Jenkinsfile` → `[infra]`; `.json .toml .ini .env* .properties` y `.xml` no Android →
     `[config]`; `.kt .kts .swift .m .mm .dart AndroidManifest.xml Info.plist .entitlements
     Podfile pubspec.yaml` y `.java` con `android.` → `[mobile]`; `.html .htm .vue .svelte .css
     .scss` → `[browser]`.
  3. **Imports/contenido** para `.js .jsx .ts .tsx .mjs .cjs .py .rb .php .go .cs .java`:
     `react-native`/`expo` → mobile; `react vue svelte @angular next/ window. document.
     localStorage sessionStorage navigator.` → browser; `express fastify @nestjs koa hapi
     http.createServer flask fastapi django rails laravel net/http gin-gonic aspnetcore` →
     server. Si hay señales de más de un lado → **todas**, en orden mobile, browser, server.
  4. **Perfil de proyecto**: `.tsx/.jsx` en `mobile_js` → se agrega `mobile` aunque el archivo no
     importe `react-native`; archivo sin señal en `frontend_js` → `[browser, unknown]`; en
     `backend_js` → `[server, unknown]`.
  5. **Directorio** como desempate sólo si sigue sin señal: `frontend/ web/ client/ ui/
     components/ pages/ views/` → browser; `backend/ server/ api/ services/ lambda/ handlers/`
     → server.
  6. Sin señal → `[unknown]`.

`unknown` es "cubrir ampliamente": lo reciben todos los expertos de código.

Un nodo delgado `classify_runtime` (después de `rag_retrieve`) construye el perfil, anota
`runtimes` en cada entrada de `state.files` y escribe `expert_metadata.project_profile`.

### D2. Selección por intersección de runtimes, sin fallback, con invariante de cobertura

`BaseExpertNode.get_runtimes() -> set[Runtime]`; un archivo se selecciona si
`set(file.runtimes) & expert.runtimes` no es vacío.

| Experto | Runtimes |
|---|---|
| `prompt_hardening` | todos |
| `code_vulnerabilities` | todos |
| `owasp_api` | `server`, `browser`, `unknown`, `config` |
| `owasp_web` | `browser`, `server`, `unknown` |
| `owasp_mobile` | `mobile` |
| `devsecops` | `infra`, `config`, `test` |

`test` entra en `devsecops`: los tests no son superficie de ataque de front/back pero sí filtran
secretos en fixtures, `verify=False`, endpoints productivos en mocks (dominio secret management).

**Invariante de cobertura** (verificado en `classify_runtime`, no en los expertos): todo archivo con
`browser|server|unknown` debe quedar seleccionado por ≥1 de `owasp_api`/`owasp_web`; todo `mobile`
por `owasp_mobile`; todo `infra|config|test` por `devsecops`. Por construcción de la tabla se cumple
siempre; el nodo igualmente calcula `expert_metadata.coverage = {expert: n_files}` y
`files_without_domain_expert` (debe ser 0; si no, agrega `unknown` al archivo y loguea WARNING).

Si un experto no selecciona archivos, **no corre** y registra
`expert_metadata[name] = {"files_analyzed": 0, "skipped": true}`. Se elimina el fallback.

### D3. Batching con chunking de archivos grandes

Nuevo `domain/services/batch_planner.py`:

- `Chunk = {path, runtimes, start_line, end_line, content, chunk_index, total_chunks}`.
- Archivo ≤ `per_file_cap` → un chunk con todo el contenido.
- Archivo > cap → ventanas de `per_file_cap` chars cortadas en límite de línea, con solape de
  `overlap_chars` (default 5_000); cada chunk > 0 lleva prefijo
  `# [context: imports and signatures of <path>]` con las líneas estructurales del archivo completo
  (`extract_structural_lines`, máx 60 líneas) para no perder imports. El prefijo no cuenta para el
  offset de líneas.
- `plan(files, per_file_cap, batch_budget, overlap) -> list[Batch]`: ordena chunks por
  `(runtime primario, path, chunk_index)`; greedy hasta `batch_budget` (default 200_000); un chunk
  nunca se parte.
- Env: `TITVO_EXPERT_FILE_CAP_CHARS` (30_000), `TITVO_EXPERT_BATCH_BUDGET_CHARS` (200_000),
  `TITVO_EXPERT_CHUNK_OVERLAP_CHARS` (5_000), `TITVO_EXPERT_MAX_CONCURRENCY` (4). Todas con
  fallback.

Encabezado en el prompt: `=== FILE: {path} [runtime: {primary}] [lines {start}-{end} of {total}] ===`
(el rango sólo aparece si el archivo tiene más de un chunk). Al parsear la respuesta, `line` se
corrige con `start_line - 1`. Duplicados en zona solapada los absorbe L1.

`_compute_file_budgets`, `_GLOBAL_BUDGET_CHARS`, `_MIN_FILE_CHARS` y `_smart_truncate` desaparecen.

### D4. Fan-out paralelo con agregación determinista

```
mcp_retrieve → rag_retrieve → classify_runtime ─┬→ expert_prompt_hardening ─┐
                                                 ├→ expert_owasp_api        ─┤
                                                 ├→ expert_owasp_web        ─┤
                                                 ├→ expert_owasp_mobile     ─┼→ merge → END
                                                 ├→ expert_devsecops        ─┤
                                                 └→ expert_code_vulns       ─┘
```

- `AgentState.issues`, `expert_errors`, `failed_batches` → `Annotated[list, operator.add]`;
  `expert_metadata` → reducer de merge de dicts. Los expertos devuelven sólo su delta.
- Lotes con `asyncio.gather` bajo `asyncio.Semaphore` compartido; reintento con backoff
  exponencial (3 intentos) ante errores de proveedor.
- Cada `ExpertIssue` lleva `metadata = {"expert", "batch_index", "chunk_index"}`.
- `merge` ordena `state.issues` por `(expert, batch_index, path, line, category, title)` al inicio.
- `merge` **no escribe `issues`**; el resultado vive en `final_output`.

### D5. Consolidación en dos niveles sin pérdida silenciosa

**L1 (determinista)**: clave `(path, line, category, code normalizado)`. Sólo evidencia idéntica se
fusiona; conserva severidad **más alta** y registra `metadata.merged_from` (expertos). Cambia la
regla "severidad menor" de `conservative-findings-policy`: dos expertos coincidiendo es evidencia a
favor, y el prompt de consolidación ya usaba la mayor.

**L2 (LLM, por archivo, con rendición de cuentas)**: agrupa L1 por `path`; grupos de 1 finding
pasan directo; grupos ≥ 2 van al modelo en chunks ≤ 20 findings. El prompt exige por cada issue de
salida un campo `source_ids` con los ids de entrada que consolida. Validación determinista del
grupo, cualquier violación → el grupo vuelve a L1 completo:

1. cada id de entrada aparece en exactamente un `source_ids`;
2. `severity` de salida == máxima entre sus fuentes;
3. `path`, `line` y `code` de salida existen en alguna de sus fuentes.

`source_ids` se elimina antes de construir `ExpertIssue`. Prompt: "fusiona sólo hallazgos que
describan la misma causa raíz en el mismo archivo; ante duda, mantenlos separados". No hay
consolidación entre archivos. Métricas en `expert_metadata.consolidation =
{l1_in, l1_out, l2_in, l2_out, l2_groups, l2_groups_rejected}`.

### D6. Scan incompleto explícito

Un lote que agota reintentos produce una entrada en `state.failed_batches =
[{expert, batch_index, paths, error}]`. En `merge`:

- Si `failed_batches` no está vacío → `final_output.incomplete = {failed_batches,
  files_not_fully_analyzed: <paths únicos>, message: "Análisis incompleto: X de Y lotes
  fallaron; N archivos sin analizar completamente"}`.
- `status` nunca es `COMPLETED` con `incomplete`: sin issues → `WARNING`; con issues → por
  severidad. Así siempre se genera reporte.
- `ResultDto` gana `error: str | None = None` e `incomplete: dict | None = None`. Esto arregla el
  `TypeError` latente cuando `merge` emite `error` por fallo de MCP.
- `LambdaReportRepository.create_report` envía `incomplete` en el payload; el lambda
  `src/mcp/issue-report` lo acepta como opcional y renderiza un banner al inicio del HTML con
  `message` y la lista de archivos. `GithubIssue`/Code Insights no cambian en este change.
- `task.result` (Dynamo) conserva `incomplete` completo.

### D7. Encabezado de archivo con runtime

Ver D3. Los prompts de expertos no cambian en este change; la etiqueta queda disponible para el
siguiente.

## Risks / Trade-offs

- [Rate limit del proveedor por N lotes × 6 expertos] → semáforo configurable, backoff; commit
  mode sigue siendo 1 lote por experto.
- [Duración del full scan sube] → paralelismo; medir con repo de ~300 archivos y documentar.
- [Perfil de proyecto ausente en commit mode] → clasificación per-file + `unknown` amplio; nunca
  menos cobertura que hoy.
- [Chunking duplica findings en zona solapada] → L1 los absorbe si línea y code coinciden; si el
  modelo varía la línea en ±1, L2 por archivo los fusiona.
- [L2 rechaza grupos con frecuencia si el modelo no respeta `source_ids`] → métrica
  `l2_groups_rejected` visible; fallback mantiene todos los findings (más ruido, cero pérdida).
- [Cambio de severidad "menor → mayor" en L1 puede subir status de WARNING a FAILED] → explícito
  en spec; coherente con la preferencia de recall.
- [`incomplete` cambia el payload hacia `issue-report`] → campo opcional; lambda viejo lo ignora.
- [Reducers rompen tests que asumen secuencia] → actualizar harness y agregar aserción de orden.

## Migration Plan

1. Desplegar `issue-report` primero (acepta `incomplete` opcional; sin él se comporta igual).
2. Desplegar imagen del agente. Sin migración de datos.
3. Verificar en LocalStack: commit de 3 archivos, full de 100+ archivos, un lote forzado a fallar
   (banner visible en reporte y `incomplete` en Dynamo).
4. Rollback: tag anterior de la imagen ECR; `issue-report` es compatible hacia atrás.

## Open Questions

Resueltas con el usuario (2026-10-06):

- Archivos > cap → chunking con solapamiento (D3), no truncar.
- Concurrencia → env `TITVO_EXPERT_MAX_CONCURRENCY`, fallback 4.
- `test` → `devsecops` (D2).
- Banner de incompleto en reporte → incluido en este change (D6).
