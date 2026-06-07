## MODIFIED Requirements

### Requirement: LangGraph StateGraph defines workflow nodes

The system SHALL define a `langgraph.graph.StateGraph` with the following logical nodes: **`mcp_retrieve`**, six expert nodes named **`expert_prompt_hardening`**, **`expert_owasp_api`**, **`expert_owasp_web`**, **`expert_owasp_mobile`**, **`expert_devsecops`**, **`expert_code_vulnerabilities`**, and **`merge`**. Final merge node SHALL be wired to `END`.

#### Scenario: StateGraph compilation

- **WHEN** `LangGraphAgent` is initialized with a compiled graph
- **THEN** compilation succeeds with `mcp_retrieve` as entry and experts chained in order ending at `merge`

### Requirement: Expert nodes run sequentially with file filtering

Each expert node SHALL consume **`state.files`**, apply domain filters (fallback: all files if filter empty), and extend **`state.issues`**. Sequential order SHALL match: prompt_hardening → owasp_api → owasp_web → owasp_mobile → devsecops → code_vulnerabilities.

#### Scenario: Single expert parse failure

- **WHEN** one expert yields invalid JSON or raises
- **THEN** failures SHOULD be reflected in **`expert_errors`** or logs and downstream nodes continue unless implementation aborts globally (prefer continuation per current design)

#### Scenario: OWASP mobile expert runs in sequence

- **WHEN** the workflow receives readable files and reaches the expert chain
- **THEN** `expert_owasp_mobile` runs after `expert_owasp_web` and before `expert_devsecops`
