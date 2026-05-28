# langgraph-orchestration Specification

## Purpose

Orquestación del análisis de código con LangGraph: nodos MCP, expertos de seguridad, merge de hallazgos y contrato `AbstractAgent`. La integración RAG (pre-scan y post-scan delta) vive fuera del grafo en `AnalyseCodeUseCase`.

## Requirements

### Requirement: LangGraph StateGraph defines workflow nodes

The system SHALL define a `langgraph.graph.StateGraph` with the following logical nodes: **`mcp_retrieve`**, five expert nodes named **`expert_prompt_hardening`**, **`expert_owasp_api`**, **`expert_owasp_web`**, **`expert_devsecops`**, **`expert_code_vulnerabilities`**, and **`merge`**. Final merge node SHALL be wired to `END`.

#### Scenario: StateGraph compilation

- **WHEN** `LangGraphAgent` is initialized with a compiled graph
- **THEN** compilation succeeds with `mcp_retrieve` as entry and experts chained in order ending at `merge`

### Requirement: MCP retrieval implements gateway async commit-files contract

The `mcp_retrieve` node SHALL use the MCP **`tools/call`** flow compatible with Titvo Gateway:

1. Call **`mcp.tool.git.commit-files`** (or equivalent resolved tool name) with **`repository`** and **`commitId`** matching the scan task.
2. Read **`jobId`** from the response (JSON object with `jobId` / `pollToolName` per gateway contract).
3. Repeatedly call **`mcp.tool.git.commit-files.poll`** with **`jobId`** until **`status`** is **`SUCCESS`** or **`FAILURE`**, backing off between attempts within configured limits.
4. On **`SUCCESS`**, extract **`filesPaths`** from the polled payload (**top-level** or **`data.filesPaths`** as returned).
5. For each path, call **`mcp.tool.files`** (**or **`files`** resolved name**) with argument **`path`** only, and accumulate `{path, content}` into **`state.files`**.

If **`git.commit-files`** or **`poll`** returns failure, times out, or yields no paths, the node MUST set **`mcp_error`**, **`files`** empty, **`scaned_files`**: 0, and optional **`status`**: **`FAILED`** as implemented.

#### Scenario: Successful file retrieval

- **WHEN** the async job completes with `SUCCESS` and non-empty `filesPaths`
- **THEN** **`state.files`** lists all successfully read blobs and **`state.scaned_files`** reflects the count of items with content.

#### Scenario: MCP or job failure early exit

- **WHEN** commit-files job fails (`FAILURE`) or polling exceeds limits
- **THEN** **`state.mcp_error`** is populated and **`state.files`** MAY be empty; conditional routing skips experts.

### Requirement: Conditional routing after MCP

After `mcp_retrieve`, IF **`mcp_error`** is set OR **`files`** is empty, the graph SHALL route to **`merge`** (skip all expert nodes). OTHERWISE it SHALL route to **`expert_prompt_hardening`**.

#### Scenario: No files after MCP

- **WHEN** retrieval yields no readable files
- **THEN** experts are not executed and `merge` still runs to produce a consistent final envelope.

### Requirement: Expert nodes run sequentially with file filtering

Each expert node SHALL consume **`state.files`**, apply domain filters (fallback: all files if filter empty), and extend **`state.issues`**. Sequential order SHALL match: prompt_hardening → owasp_api → owasp_web → devsecops → code_vulnerabilities.

#### Scenario: Single expert parse failure

- **WHEN** one expert yields invalid JSON or raises
- **THEN** failures SHOULD be reflected in **`expert_errors`** or logs and downstream nodes continue unless implementation aborts globally (prefer continuation per current design).

### Requirement: Merge node consolidates findings

The **`merge`** node SHALL deduplicate **`state.issues`** by expert dedup key (`get_dedup_key()` → path, line, category), SHALL determine **`status`** (`FAILED` if any CRITICAL/HIGH, **`WARNING`** if medium/low only, **`COMPLETED`** if none), and SHALL expose **`final_output`** with **`status`**, **`scaned_files`**, **`issues`** for the LangGraph adapter to serialize.

_Nota de implementación: el nodo `merge` puede deduplicar por primera aparición; el servicio domain **`FindingsMerger`** documenta fusión más rica ante conflictos de severidad — convergencia futura opcional._

#### Scenario: Status determination

- **WHEN** merge executes with merged issues list
- **THEN** **`status`** matches severity rules described above.

### Requirement: LangGraphAgent implements AbstractAgent port

The `LangGraphAgent` SHALL be the only agent implementation wired in `main.py`. There is no legacy mode or feature flag switching.

The `AnalyseCodeUseCase` SHALL execute a pre-scan RAG indexing check and a post-scan delta trigger **outside** the LangGraph graph, before and after calling `self.agent.invoke()` respectively. These steps SHALL NOT be implemented as LangGraph nodes.

#### Scenario: Pre-scan RAG check is outside the graph

- **WHEN** `AnalyseCodeUseCase.execute()` is called
- **THEN** the RAG index check and full indexing (if needed) run BEFORE `self.agent.invoke()` is called, with no changes to the LangGraph node topology

#### Scenario: Post-scan delta trigger is outside the graph

- **WHEN** `self.agent.invoke()` returns
- **THEN** the fire-and-forget delta trigger runs AFTER the graph result is obtained, with no changes to the LangGraph node topology

### Requirement: Langfuse tracing

Tracing SHALL use **`langfuse.langchain.CallbackHandler`** compatible with LangChain 1.x. Child spans SHOULD appear per tool/graph step when tracing is configured.

#### Scenario: Tool visibility

- **WHEN** MCP polling is active and tracing enabled
- **THEN** spans for **`mcp.tool.git.commit-files`**, **`mcp.tool.git.commit-files.poll`** (possibly multiple), and **`mcp.tool.files`** MAY appear depending on LC/Langfuse integration layering.
