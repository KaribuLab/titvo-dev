# Arquitectura del Agente

## Vista General

```mermaid
flowchart TD
    API[API Gateway] -->|POST /analyze| Lambda[Lambda: Titvo Agent]
    Lambda -->|inicializa| Agent{Agent Mode}
    Agent -->|langgraph| LGA[LangGraphAgent]
    Agent -->|legacy| LCA[LangchainAgent]
    
    LGA -->|StateGraph| WF[Workflow]
    WF --> MCP[MCP Retrieval Node]
    subgraph MCP_Fases["Contrato MCP (gateway Titvo)"]
        MCP --> A[mcp.tool.git.commit-files<br/>repository, commitId]
        A --> B[mcp.tool.git.commit-files.poll<br/>jobId hasta SUCCESS]
        B --> C[mcp.tool.files<br/>path por cada entrada]
    end
    C --> Files[Lista path + contenido]

    Files -->|secuencial| Exp1[Expert: Prompt Hardening]
    Exp1 --> Exp2[Expert: OWASP API]
    Exp2 --> Exp3[Expert: OWASP Web]
    Exp3 --> Exp4[Expert: DevSecOps]
    Exp4 --> Exp5[Expert: Code Vulns]
    Exp5 --> Merge[Merge Node]
    
    Merge -->|JSON| Notify[Notificaciones]
    Notify --> Bit[Bitbucket]
    Notify --> GitHub[GitHub]
    Notify --> S3[Report S3]
```

## LangGraph Workflow

```mermaid
flowchart LR
    Start([Start]) --> MCP[mcp_retrieve]
    MCP -->|archivos OK| EH[expert_prompt_hardening]
    MCP -->|mcp_error o sin files| MG[merge]

    EH --> EAPI[expert_owasp_api]
    EAPI --> EWEB[expert_owasp_web]
    EWEB --> EDO[expert_devsecops]
    EDO --> ECV[expert_code_vulnerabilities]
    ECV --> MG
    
    MG --> END([End])
```

## Flujo de Datos (State)

```mermaid
flowchart TD
    subgraph State["AgentState (TypedDict)"]
        Task[task_id, repository_url, commit_hash]
        Files[files, scaned_files]
        MCPERR[mcp_error opcional]
        Issues[issues, expert_errors]
        Meta[expert_metadata]
    end
    
    MCP -->|popula| Files
    Exp1 -->|appends| Issues
    Exp2 -->|appends| Issues
    Exp3 -->|appends| Issues
    Exp4 -->|appends| Issues
    Exp5 -->|appends| Issues
    Merge -->|dedupe + estado| Final[Final JSON]
```

## Componentes Principales

| Componente | Archivo | Responsabilidad |
|------------|---------|-----------------|
| LangGraphAgent | `infra/adapters/langgraph_agent.py` | Implementa AbstractAgent con workflow LangGraph |
| Workflow Builder | `infra/adapters/langgraph/workflow.py` | Construye StateGraph con nodos |
| MCP Node | `infra/adapters/langgraph/nodes/mcp_retrieval_node.py` | Invoke + polling MCP (`commit-files`, `commit-files.poll`, `files`), parámetros `repository`/`commitId`/`path` |
| Expert Nodes | `infra/adapters/langgraph/nodes/expert_nodes.py` | Cinco expertos con filtros de archivo |
| Merge Node | `infra/adapters/langgraph/nodes/merge_findings_node.py` | Dedup por clave (`get_dedup_key`), estado FAILED/WARNING/COMPLETED |
| FindingsMerger | `domain/services/findings_merger.py` | Política en dominio: severidad menor ante conflictos mismos `(path,line,category)`; el grafo puede evolucionar a reutilizarlo plenamente en `merge` |
| PromptRegistry | `prompts/__init__.py` | Carga prompts embebidos |

## Contrato MCP (gateway Titvo)

Las tools **no están descritas de nuevo aquí**, pero el agente debe respetar el flujo asíncrono:

1. `mcp.tool.git.commit-files` → respuesta `jobId` (+ `pollToolName`).
2. `mcp.tool.git.commit-files.poll` con `jobId` hasta `SUCCESS`/`FAILURE` → lista `filesPaths`.
3. `mcp.tool.files` con **`path`** por cada elemento.

Legacy: el modelo puede orquestarlo en varios turnos. LangGraph: lo hace código en `MCPRetrievalNode` (sin LLM para esa parte).

| Experto | Patrones | Fallback |
|---------|----------|----------|
| prompt_hardening | Todos | - |
| owasp_api | rutas/handlers/controllers, openapi/swagger, patrones nombre | Todos si vacío |
| owasp_web | `*.html`, `*.tsx`, `*template*`, `*.js`/`.jsx`/`.vue`, etc. | Todos si vacío |
| devsecops | `*.yml`, `Dockerfile*`, `*.tf`, `.github/**` | Todos si vacío |
| code_vulnerabilities | Todos | - |

## Modos de agente (`TITVO_AGENT_MODE`)

### LangGraph (default)

Default si no defines la variable (`main.py` usa `langgraph`).

```bash
export TITVO_AGENT_MODE=langgraph
```

- MCP en código determinístico (menos tokens en fase MCP).
- Cinco expertos secuenciales y nodo **`merge`**.
- Tracing Langfuse vía **`langfuse.langchain.CallbackHandler`**.

### Legacy

```bash
export TITVO_AGENT_MODE=legacy
```

- Un solo **`create_agent`** con todas las tools MCP; el modelo decide la secuencia por turnos.
- Útil para rollback o diagnóstico comparativo.

## Paths en componentes de la tabla

Los archivos están bajo `src/agent/src/code_analysis/` (prefijo omitido arriba en paths relativos típicos a `infra/...`).
