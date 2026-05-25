## Why

El agente usaba un único prompt monolítico con LangChain (`create_agent`) que concentraba todas las categorías en una sola invocación, con más falsos positivos y poca especialización por dominio. **LangGraph** modela el análisis como un grafo con nodo MCP determinístico, cinco nodos experto secuenciales y merge final, manteniendo el contrato JSON y la integración MCP/Langfuse. Los **prompts de escaneo** viven embebidos en el paquete del agente (**sin DynamoDB para `scan_system_prompt` ni `content_template`**), lo que replica el ciclo del despliegue en contenedor.

## What Changes

- Flujo **`langgraph.graph.StateGraph`**: `mcp_retrieve` → cinco expertos → nodo **`merge`** (id real del grafo).
- Cinco nodos experto (`prompt_hardening`, `owasp_api`, `owasp_web`, `devsecops`, `code_vulnerabilities`) con prompts en `code_analysis/prompts/experts/`.
- **Orquestación MCP en código Python** (`MCPRetrievalNode`): mejor uso de tokens que un bucle agente multi-turn sobre tools; comportamiento debe **respetar el contrato asíncrono del gateway** (ver abajo).
- Política **conservadora** en prompts y **`FindingsMerger`** en dominio; merge final en el grafo deduplica por clave experto (primer hallazgo gana si hay duplicados en la lista acumulada).
- Adaptador **`LangGraphAgent`** que implementa `AbstractAgent`; convive con **`LangchainAgent`** vía **`TITVO_AGENT_MODE`** (`langgraph` | `legacy`).
- **`PromptRegistry`** + markdown en imagen Docker; **`localstack/app/setup.ts`** ya no persist esos prompts en DynamoDB.
- **`system_prompt.md`**: severity de prompt injection en código analizado moderada (**MEDIUM**), alineado a reducir ruido.
- **Documentación:** `docs/` (arquitectura Mermaid, prompts, troubleshooting—including MCP asíncrono—, etc.).
- **Ajustes de aplicación:** p. ej. `files_content` en plantilla para `content_template`; import Langfuse **`langfuse.langchain.CallbackHandler`**.
- Tests unitarios bajo `src/agent/tests/unit/` para registry, merger, nodos clave.

## Capability: contrato MCP del gateway (Titvo)

Las **tools no cambian** en el servidor, pero el cliente DEBE implementar el flujo documentado por el gateway:

1. **`tools/call`** `mcp.tool.git.commit-files` con `repository`, `commitId` → respuesta **`jobId`** + `pollToolName`.
2. **`tools/call`** repetido a **`mcp.tool.git.commit-files.poll`** con `jobId` hasta `status === SUCCESS` o `FAILURE`.
3. Con `filesPaths`, **`tools/call`** a **`mcp.tool.files`** con argumento **`path`** por entrada.

Sin este polling, Langfuse puede mostrar solo la primera tool y el grafo **salta expertos** (sin archivos).

## Capabilities

### New Capabilities

- `langgraph-orchestration`: StateGraph, routing condicional tras MCP (`mcp_error` o lista vacía → `merge`), trazas Langfuse.
- `security-expert-agents`: Cinco expertos, prompts incrustados, sin tools MCP en expertos.
- `conservative-findings-policy`: Criterios de severidad y deduplicación en dominio (y evolución del merge en grafo).

### Modified Capabilities

- _(dependencias locales: mismo contrato MCP; comportamiento esperado del **cliente** agente refinado tras implementación asíncrona)_

## Impact

- **Código**: `src/agent/src/code_analysis/` (dominio `expert_result`, `findings_merger`, `langgraph/` + `langgraph_agent.py`, `main.py`, prompts, tests).
- **LocalStack**: `localstack/app/setup.ts` sin semillas DynamoDB para esos prompts.
- **`docs/`** en raíz del monorepo.
- **`openspec/`** y este cambio mantienen el relato ejecutable vs legacy.

## Non-goals

- No nuevo consenso multi-modelo ni votación entre expertos en esta iteración.
- No agregar nuevas MCP tools en gateway; sí **consumir correctamente** las existentes (incluyendo **`*.poll`**).
- No paralelismo de expertos en v1.

## Risks residual

| Riesgo | Nota |
|--------|------|
| **Costo/latencia** | Cinco llamadas modelo secuenciales + contexto repetido por experto según filtros. |
| **Merge vs `FindingsMerger`** | El nodo `merge` hoy deduplica por primera aparición; el servicio domain tiene política más rica conflictos → posible refactor futuro. |
| **Polling MCP** | Timeouts/colas lentas en LocalStack pueden requerir ajustar `POLL_MAX_ATTEMPTS` / intervalo en `MCPRetrievalNode`. |
