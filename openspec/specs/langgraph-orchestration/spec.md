# langgraph-orchestration Specification

## Purpose

Orquestación del análisis de código con LangGraph: nodos MCP, expertos de seguridad, merge de hallazgos y contrato `AbstractAgent`. La integración RAG (pre-scan y post-scan delta) vive fuera del grafo en `AnalyseCodeUseCase`.

## Requirements

### Requirement: LangGraph StateGraph defines workflow nodes

The system SHALL define a `langgraph.graph.StateGraph` with the following logical nodes:
**`mcp_retrieve`**, **`rag_retrieve`** (when a RAG adapter is configured), **`classify_runtime`**,
six expert nodes named **`expert_prompt_hardening`**, **`expert_owasp_api`**, **`expert_owasp_web`**,
**`expert_owasp_mobile`**, **`expert_devsecops`**, **`expert_code_vulnerabilities`**, and **`merge`**.
`classify_runtime` SHALL fan out to all six expert nodes, every expert node SHALL have an edge to
`merge`, and `merge` SHALL be wired to `END`.

#### Scenario: StateGraph compilation

- **WHEN** `LangGraphAgent` is initialized with a compiled graph
- **THEN** compilation succeeds with `mcp_retrieve` as entry, `classify_runtime` fanning out to six
  experts, and all experts converging on `merge`

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

After `mcp_retrieve`, IF **`mcp_error`** is set OR **`files`** is empty, the graph SHALL route to
**`merge`** (skip RAG, classification and all expert nodes). OTHERWISE it SHALL route to
`rag_retrieve` when present, else directly to `classify_runtime`.

#### Scenario: No files after MCP

- **WHEN** retrieval yields no readable files
- **THEN** experts are not executed and `merge` still runs to produce a consistent final envelope.

### Requirement: Expert nodes run sequentially with file filtering

Expert nodes SHALL run **in parallel** after `classify_runtime`. Each expert SHALL select files by
runtime intersection, split them into chunks and batches, and return **only its delta** of
`issues`, `expert_errors`, `failed_batches` and `expert_metadata`. `AgentState.issues`,
`AgentState.expert_errors` and `AgentState.failed_batches` SHALL use an additive list reducer and
`AgentState.expert_metadata` a dict-merge reducer so concurrent writes accumulate. The `merge`
node SHALL sort `state.issues` by `(metadata.expert, metadata.batch_index, path, line, category,
title)` before consolidation so the final output does not depend on completion order.

#### Scenario: Single expert parse failure

- **WHEN** one expert yields invalid JSON or raises
- **THEN** the failure is reflected in **`expert_errors`** and **`failed_batches`** and the other
  experts' issues are still merged

#### Scenario: Output is independent of expert completion order

- **WHEN** the same scan is executed twice and expert nodes complete in different orders
- **THEN** `final_output` is byte-identical between the two executions

#### Scenario: Merge does not write back to issues

- **WHEN** `merge` produces the consolidated list
- **THEN** it writes it to `final_output.issues` and does not return an `issues` key

### Requirement: Merge node consolidates findings

The **`merge`** node SHALL consolidate `state.issues` in two levels. **L1** SHALL deduplicate
deterministically by `(path, line, category, normalized code)`, keeping the highest severity and
recording merged expert names in `metadata.merged_from`. **L2** SHALL group L1 results by `path`;
groups with a single finding bypass the LLM; groups with two or more findings SHALL be sent to the
consolidation model in chunks of at most 20 findings with the conservative consolidation prompt,
which requires a `source_ids` list per output issue. The node SHALL accept a group's consolidation
only if every input id appears in exactly one `source_ids`, every output severity equals the
maximum severity of its sources, and every output `path`, `line` and `code` exist in one of its
sources; otherwise the group keeps its L1 findings. The node SHALL record
`expert_metadata.consolidation = {l1_in, l1_out, l2_in, l2_out, l2_groups, l2_groups_rejected}`.
The node SHALL determine **`status`**: `FAILED` if any CRITICAL/HIGH; otherwise **`WARNING`** if
there are issues or `final_output.incomplete` is present; otherwise **`COMPLETED`**. It SHALL expose
**`final_output`** with **`status`**, **`scaned_files`**, **`issues`** and, when applicable,
**`incomplete`** and **`error`**.

#### Scenario: Status determination

- **WHEN** merge executes with the consolidated issues list and no failed batches
- **THEN** **`status`** matches the severity rules described above.

#### Scenario: Large scan does not send all findings in one call

- **WHEN** L1 yields 120 findings across 40 files
- **THEN** each consolidation LLM call contains findings of a single file and at most 20 of them

#### Scenario: Consolidation that loses a finding is rejected

- **WHEN** the model returns, for a group of 3 findings, two issues whose `source_ids` cover only
  ids 0 and 1
- **THEN** the group keeps its 3 L1 findings and `l2_groups_rejected` increases by one

#### Scenario: Consolidation failure in one group does not affect others

- **WHEN** the model returns invalid JSON for one file group
- **THEN** that group keeps its L1 findings and the remaining groups keep their consolidated results

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

### Requirement: Fuente CLI alternativa

The workflow SHALL accept a CLI retrieval node producing the same files envelope as MCP retrieval. CLI scans SHALL use uploaded files without Git or branch RAG.

#### Scenario: CLI fullscan

- **WHEN** a CLI source is supplied
- **THEN** experts receive verified uploaded content and no Git tool is invoked

### Requirement: Contexto estable por lote

Experts SHALL partition formatted files into bounded messages without reducing a file budget due to scan size. Parse and invocation failures SHALL preserve other batch findings and report incomplete coverage.

#### Scenario: Lote falla

- **WHEN** one batch fails
- **THEN** successful findings remain and the scan cannot be COMPLETED

### Requirement: Consolidación conservadora con trazabilidad

Consolidation SHALL operate within one file in bounded groups and account for every input ID. Missing inputs SHALL be retained; invalid outputs SHALL fall back to originals.

#### Scenario: Hallazgo omitido

- **WHEN** a model output does not represent one input
- **THEN** that input remains in the final report

### Requirement: Recuperación acotada de hallazgos inválidos

Experts SHALL normalize unambiguous relative-path and numeric-line representations. Rejected finding objects SHALL receive at most one correction request per batch, within a bounded input and context budget. Already-valid findings SHALL remain unchanged. Every corrected finding SHALL account for its original source ID; unresolved, omitted or unsupported records SHALL keep coverage incomplete.

#### Scenario: Campo faltante corregido

- **WHEN** a model returns one valid finding and one finding with missing required fields
- **THEN** the agent retains the valid finding and attempts correction of the rejected record only

#### Scenario: Corrección incompleta

- **WHEN** a correction omits a rejected source ID or changes existing evidence
- **THEN** the batch remains incomplete and other valid findings remain in the report

### Requirement: Diagnóstico de validación por lote

Coverage metadata SHALL record 1-based batch numbers, rejection reasons and repair outcome without persisting rejected raw response text.

#### Scenario: Rechazo persistente

- **WHEN** a finding cannot be repaired
- **THEN** the report explains its validation reason instead of showing only an invalid-finding count
