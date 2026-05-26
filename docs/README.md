# Titvo Agent Documentation

Agente de análisis de seguridad con arquitectura LangGraph y múltiples expertos especializados.

## Quick Start

Desde `src/agent` (según Dockerfile y empaquetado del paquete `code_analysis`):

```bash
cd src/agent

# Modo recomendado: LangGraph (default si omites la variable)
TITVO_SCAN_TASK_ID=abc123 TITVO_AGENT_MODE=langgraph python -m src.main

# Modo legacy: un solo agente LangChain que elige MCP tools por turnos
TITVO_AGENT_MODE=legacy python -m src.main
```

## Documentación

- [Arquitectura](architecture.md) - Diagramas de flujo y componentes
- [Guía de prompts](prompts.md) - Cómo modificar prompts de expertos
- [Agregar expertos](adding-experts.md) - Guía para nuevos expertos
- [Troubleshooting](troubleshooting.md) - Errores comunes

## Estructura del Proyecto

```
src/agent/src/code_analysis/
├── prompts/              # Prompts embebidos
│   ├── system_prompt.md
│   ├── content_template.md
│   ├── orchestrator_prompt.md
│   └── experts/
│       ├── prompt_hardening.md
│       ├── owasp_api.md
│       ├── owasp_web.md
│       ├── devsecops.md
│       └── code_vulnerabilities.md
├── domain/
│   ├── entities/         # ExpertIssue, ExpertResult
│   ├── ports/            # AbstractAgent, SecurityExpertPort
│   └── services/         # FindingsMerger
├── infra/adapters/
    ├── langchain_agent_adapter.py  # Legacy + AsyncMCPToolsFactory (sanitiza nombres MCP)
    ├── langgraph_agent.py           # Adaptador LangGraph
    └── langgraph/                   # Workflow LangGraph
        ├── nodes/                   # MCP, expertos, merge
        ├── state.py
        └── workflow.py
```

El nodo MCP implementa el contrato **asíncrono** del gateway: **`mcp.tool.git.commit-files`** → **`mcp.tool.git.commit-files.poll`** (hasta SUCCESS) → **`mcp.tool.files`** por cada `path`.

## Cambios requieren rebuild

Los prompts están empaquetados en la imagen Docker. Cualquier cambio en `prompts/` o en el código del agente requiere rebuild, por ejemplo **desde la raíz del monorepo**:

```bash
docker build -f src/agent/Dockerfile -t titvo-agent:latest src/agent
```
