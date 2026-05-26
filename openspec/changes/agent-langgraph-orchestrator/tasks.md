## 1. Dominio y contratos

- [x] 1.1 Crear `SecurityExpertPort` en `domain/ports/security_expert.py` con método `analyze(files, metadata) -> ExpertResult`
- [x] 1.2 Crear dataclasses `ExpertIssue`, `ExpertResult` y `FileContent` en `domain/entities/`
- [x] 1.3 Crear `FindingsMerger` en `domain/services/findings_merger.py` con deduplicación conservadora por `(path, line, category)`

## 2. Prompts en código

- [x] 2.1 Crear `PromptRegistry` en `code_analysis/prompts/__init__.py` con carga vía `importlib.resources`
- [x] 2.2 Agregar `system_prompt.md` basado en titvo-installer (**severity MEDIUM para prompt injection**)
- [x] 2.3 Agregar `content_template.md` (igual que titvo-installer)
- [x] 2.4 Crear `orchestrator_prompt.md` con instrucciones de fases MCP para LangGraph
- [x] 2.5 Crear `experts/prompt_hardening.md` para detectar payloads de prompt injection en código (comentarios, strings, nombres de archivos diseñados para manipular agentes AI)
- [x] 2.6 Crear `experts/owasp_api.md` cubriendo OWASP API Security Top 10
- [x] 2.7 Crear `experts/owasp_web.md` cubriendo OWASP Web Top 10
- [x] 2.8 Crear `experts/devsecops.md` para CI/CD, IaC y contenedores
- [x] 2.9 Crear `experts/code_vulnerabilities.md` para vulnerabilidades a nivel de código

## 3. Nodos experto LangGraph

Ubicación real: `infra/adapters/langgraph/nodes/`.

- [x] 3.1 Crear `BaseExpertNode` en `nodes/base_expert_node.py` con invocación LLM y parsing JSON
- [x] 3.2–3.6 Nodos expertos en `nodes/expert_nodes.py` (`PromptHardeningNode`, `OwaspApiNode`, …) con filtros por dominio

## 4. LangGraph workflow

Ubicación: `infra/adapters/langgraph/` y `infra/adapters/langgraph_agent.py`.

- [x] 4.1 Crear `MCPRetrievalNode` en `langgraph/nodes/mcp_retrieval_node.py` (MCP asíncrono: commit-files → poll hasta SUCCESS → files por path)
- [x] 4.2 Crear `MergeFindingsNode` en `langgraph/nodes/merge_findings_node.py`
- [x] 4.3 Crear builder en `langgraph/workflow.py` (`LangGraphWorkflowBuilder`, `create_workflow`)
- [x] 4.4 Crear `LangGraphAgent` en `langgraph_agent.py` implementando `AbstractAgent`

## 5. Integración y configuración

- [x] 5.1 Refactorizar `main.py` para cargar prompts desde `PromptRegistry` (eliminar lectura DynamoDB de `scan_system_prompt` y `content_template`)
- [x] 5.2 Eliminar carga de prompts en `localstack/app/setup.ts` (`scan_system_prompt`, `content_template`)
- [x] 5.3 Agregar feature flag `TITVO_AGENT_MODE` (`langgraph` | `legacy`; default `langgraph`) en `main.py`
- [x] 5.4 Integrar spans Langfuse con `langfuse.langchain.CallbackHandler`

## 6. Validación

- [x] 6.1 Probar LangGraph en LocalStack con commit de prueba (incl. visibilidad de poll en MCP/Langfuse)
- [x] 6.2 Validar comportamiento conservador manualmente en escenarios conocidos
- [x] 6.3 Verificar rollback con `TITVO_AGENT_MODE=legacy`

## 7. Tests unitarios

- [x] 7.1 Tests para `PromptRegistry`
- [x] 7.2 Tests para `ExpertIssue`, `ExpertResult`, `FileContent`
- [x] 7.3 Tests para `FindingsMerger` (deduplicación, merge de severidades)
- [x] 7.4 Tests para nodos experto (filtros de archivos)
- [x] 7.5 Tests para `MCPRetrievalNode` y `MergeFindingsNode`

## 8. Documentación (`docs/` en raíz del repo)

- [x] 8.1 Crear `docs/README.md` con quick start
- [x] 8.2 Crear `docs/architecture.md` con diagramas Mermaid
- [x] 8.3 Crear `docs/prompts.md` con guía de prompts
- [x] 8.4 Crear `docs/adding-experts.md` para agregar nuevos expertos
- [x] 8.5 Crear `docs/troubleshooting.md` (incl. MCP asíncrono y Langfuse)
- [x] 8.6 Alinear toda `docs/` con implementación (polling MCP, `TITVO_AGENT_MODE`, Dockerfile, merge vs `FindingsMerger`, `orchestrator_prompt` solo referencia en LangGraph)

## 9. Calidad de código

- [x] 9.1 Configurar ruff correctamente
- [x] 9.2 Ejecutar ruff check y corregir errores

## 10. Bug fixes post-implementación

- [x] 10.1 Corregir import de `CallbackHandler` (`langfuse.callback` → `langfuse.langchain`)
- [x] 10.2 Agregar `files_content` parameter en `AnalyseCodeUseCase` para template formatting
- [x] 10.3 Agregar logging detallado en `MCPRetrievalNode` para debugging de invocación de tools
- [x] 10.4 Corregir nombres de tools MCP: `git.commit-files` → `mcp.tool.git.commit-files`, `files` → `mcp.tool.files`
- [x] 10.5 Corregir parámetros del tool `git-commit-files`: `repository_url` → `repository`, `commit_hash` → `commitId`
- [x] 10.6 Corregir parámetros del tool `files`: solo requiere `path`, no `repository_url` ni `commit_hash`
- [x] 10.7 Polling MCP de `git.commit-files` (`mcp.tool.git.commit-files.poll` hasta SUCCESS y `filesPaths`)

## 11. OpenSpec y alineación documental

- [x] 11.1 Actualizar `proposal.md`, `design.md`, `tasks.md` y specs con rutas reales, `TITVO_AGENT_MODE`, contrato MCP asíncrono y notas de merge/dedup
