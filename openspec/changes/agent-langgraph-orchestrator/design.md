## Context

El agente Titvo (`src/agent/`) analiza commits vía MCP y un modelo LLM. El modo **legacy** usa `LangchainAgent` (`create_agent`) con todas las tools MCP en el modelo: el agente puede encadenar **varias `tools/call`** por sí mismo (consume más tokens en esa fase). El modo **`langgraph`** usa `LangGraphAgent` con grafó explícito: **solo `MCPRetrievalNode`** invoca MCP de forma determinística (`MultiServerMCPClient.get_tools()` + `StructuredTool.ainvoke`); los expertos reciben texto y llaman `ChatModel.ainvoke`.

**Contrato asíncrono del gateway Titvo** (`invoke-tool.service.ts`): `mcp.tool.git.commit-files` inicia job; **`mcp.tool.git.commit-files.poll`** devuelve `status`, y en SUCCESS **`filesPaths`** (y opcional **`commitId`**). Luego `mcp.tool.files` con **`path`**.

Referencias de prompts públicas titvo-installer siguen válidas como comparación conceptual; fuente ejecutable actual: **`code_analysis/prompts/*.md`** empaquetados con el agente.

## Goals / Non-Goals

**Goals:** Grafo LangGraph, cinco expertos, merge, prompts embebidos, feature flag **`TITVO_AGENT_MODE`** (default **`langgraph`**), MCP invoke+poll+files robusto en código, troubleshooting documentado.

**Non-Goals:** Paralelo expertos en v1, nuevas MCP tools, prompts dinámicos desde Dynamo para escaneo.

## Decisions (implementadas)

### 1. Arquitectura LangGraph StateGraph

Nodos efectivos:

- `mcp_retrieve` → (condicional) `expert_prompt_hardening` → … → `expert_code_vulnerabilities` → `merge` → `END`
- Si `mcp_error` o `files` vacío: `mcp_retrieve` → `merge` (sin expertos).

Builder: `infra/adapters/langgraph/workflow.py` (`LangGraphWorkflowBuilder`). Agente orquestador: `infra/adapters/langgraph_agent.py`.

```
                    ┌─────────────┐
    entry ───────►  │ mcp_retrieve │
                    └──────┬──────┘
                           │ hay files y sin mcp_error
           ┌───────────────┴───────────────┐
           ▼                               ▼
 expert_prompt_hardening ──► … ─► expert_code_vulnerabilities
           │                               │
           └───────────────┬───────────────┘
                           ▼
                    ┌─────────────┐
                    │    merge    │
                    └─────────────┘
```

### 2. MCP: código determinístico vs agente legacy

**Decisión:** LangGraph ejecuta MCP en **`MCPRetrievalNode`** (sin LM en ese tramo).

**Ventajas:** Menos tokens en fase MCP, menos errores tipo “solo una tool y listo”; contrato asíncrono se implementa de forma reproducible (**polling hasta SUCCESS**).

**Legacy:** sigue usando el loop del agente donde el modelo elige herramientas (puede ser más flexible pero más chat por turn).

### 3. Parámetros y nombres de tools vistos por el cliente

El adaptador LangChain MCP puede exponer nombres como `mcp.tool.git.commit-files` o variantes sanitizadas; el nodo resuelve por nombre completo y fallback.

### 4. Estructura de módulos (real)

```
src/agent/src/code_analysis/
├── domain/
│   ├── ports/ia_agent.py, security_expert.py
│   ├── services/findings_merger.py
│   └── entities/expert_result.py
├── application/analyse_code_use_case.py   # ej. placeholder files_content para template
├── prompts/                               # PromptRegistry + *.md + experts/
└── infra/adapters/
    ├── langchain_agent_adapter.py          # Legacy + AsyncMCPToolsFactory
    ├── langgraph_agent.py                  # LangGraphAgent
    └── langgraph/
        ├── state.py
        ├── workflow.py
        └── nodes/
            ├── mcp_retrieval_node.py
            ├── merge_findings_node.py
            ├── base_expert_node.py
            └── expert_nodes.py
```

### 5. Prompts embebidos

`importlib.resources` + `PromptRegistry`. Cambiar prompt implica redeploy/rbuild imagen agente.

### 6. Defensa (system) vs detección (experto Prompt Hardening)

Sin cambio conceptual respecto propuesta inicial: sistema ignora contenido instructivo-hostil **en código** para no obedecer; el **experto** reporta ese contenido como riesgo (manipular analizadores automatizados).

### 7. Langfuse

`CallbackHandler` desde **`langfuse.langchain`**; trazas anidadas típicamente bajo grafo LangChain/LangGraph.

### 8. Merge y deduplicación (estado código)

Dominio **`FindingsMerger`**: política `(path,line,category)`, severidad menor en conflicto entre expert results.

El nodo **`merge`** concatena la lista `issues` ya acumulada en el estado y elimina duplicados por `get_dedup_key()`, **primera aparición gana**. Si se requiere la misma regla conservadora que en dominio (“conservador completo” en conflictos de severidad entre expertos), conviene refactorizar este nodo para reutilizar `FindingsMerger` de forma directa.

## Risks / Trade-offs

| Riesgo | Mitigación documentada |
|--------|-------------------------|
| Polling MCP | Timeouts configurables en nodo |
| Divergencia merge | Refactor usar `FindingsMerger` en nodo merge |
| Tamaño contexto por experto | Filtros de archivos en expertos |

## Migration / Estado

Implementado: grafo, polling MCP, prompts en código, cleanup LocalStack Dynamo seed, `docs/troubleshooting.md`, suite unitaria parcial.

Rollback runtime: **`TITVO_AGENT_MODE=legacy`** (mismo entry `main.py`).

## Open Questions (post v1)

- ¿Unificar `MergeFindingsNode` con `FindingsMerger` para severidad en duplicados?
- ¿Paralelizar expertos con `Send` cuando se acepte costo/banda?
