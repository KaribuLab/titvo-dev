## Why

`scan_mode=full` detecta menos vulnerabilidades que el análisis por commit sobre el mismo código.
La causa está en el pipeline del agente, no en el modelo: el presupuesto de contexto es global
(200k chars para todos los archivos), así que en repos de 100-500 archivos cada uno queda en unos
cientos de caracteres y los cuerpos de función nunca llegan al LLM. Además, la selección de archivos
por experto tiene un fallback accidental ("si nada matchea, analiza todo") que en commit hace que
`owasp_api` vea frontend y en full no. Fullscan promete máxima precisión; hoy entrega lo contrario.

## What Changes

- **Chunking + batching por experto**: archivos > 30k se parten en chunks con solape (no se
  truncan); chunks agrupados en lotes ≤ 200k chars; una llamada LLM por lote. Se elimina el shrink
  proporcional global.
- **Clasificación determinista de runtime**: nuevo nodo `classify_runtime` etiqueta cada archivo
  con uno o más de `browser | server | mobile | infra | test | config | unknown` por path,
  extensión, imports y perfil de proyecto. Sin LLM. Error de clasificación suma expertos, nunca resta.
- **Selección por runtime** en lugar de globs por nombre. **BREAKING** respecto a spec: se elimina
  el fallback "analiza todo". `prompt_hardening` y `code_vulnerabilities` siguen viendo todo.
- **Expertos en paralelo por lote**, agregación en orden determinista (expert, path, line) para
  preservar el scan reproducible (`test_reproducible_scan.py`).
- **Consolidación en dos niveles sin pérdida silenciosa**: L1 dedupe determinista
  `(path, line, category, code)`; L2 LLM por archivo con `source_ids` obligatorio y validación
  (todo finding de entrada representado o el grupo se rechaza).
- **Scan incompleto explícito**: lote fallido → `incomplete` en resultado, status nunca
  `COMPLETED`, banner en reporte HTML. Arregla `TypeError` latente en `ResultDto` ante `error`.
- Encabezado de archivo en prompts incluye runtime: `=== FILE: path [runtime: browser] ===`.
  Las reglas por runtime quedan para el change `client-side-trust-boundary`.

## Capabilities

### New Capabilities
- `file-runtime-classification`: etiquetado determinista del runtime de cada archivo, disponible en
  el estado del grafo.
- `expert-analysis-batching`: chunking con solapamiento de archivos grandes, lotes con presupuesto,
  ejecución paralela por lote y agregación determinista.

### Modified Capabilities
- `security-expert-agents`: selección de archivos por runtime sin fallback.
- `langgraph-orchestration`: nodo `classify_runtime`; expertos paralelos por lote
  con orden determinista; `merge` consolida en dos niveles.
- `conservative-findings-policy`: dedupe L1 determinista (clave con `code`) + L2 por archivo con `source_ids` obligatorio.
- `scan-completeness` (nueva): lotes fallidos → `incomplete` en resultado, `ResultDto` tolerante y banner en reporte HTML.

## Impact

- `src/agent/src/code_analysis/infra/adapters/langgraph/`: `state.py`, `workflow.py`,
  `nodes/base_expert_node.py`, `nodes/expert_nodes.py`, `nodes/merge_findings_node.py`, nuevos
  `nodes/classify_runtime_node.py`; nuevos servicios de dominio `runtime_classifier.py` y `batch_planner.py`.
- `prompts/findings_consolidation.md`, `domain/dto/result_dto.py`, `lambda_report_repository.py`.
- `src/mcp/issue-report`: DTO y template HTML (banner).
- Tests existentes de expertos, workflow y reproducibilidad; nuevos para clasificador, batching y
  consolidación.
- Más llamadas LLM por scan (lotes × 6 expertos + consolidaciones). Aceptado; revisar timeout del
  job AWS Batch.
- Sin cambios en MCP `git-commit-files`, API ni schema de `ExpertIssue`.

## Non-goals

- Reglas de detección y política de sospechas en prompts (change `client-side-trust-boundary`).
- Campo `confidence` en issues.
- RAG (límites, consultas, cross-repo) y flujo MCP `git.commit-files`.
- Clasificación de runtime por LLM.
- Optimización de costo de tokens.
