## MODIFIED Requirements

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
