## Context

The current scan flow is commit-scoped. The trigger API persists SCM arguments, the agent loads the task, `MCPRetrievalNode` invokes `mcp.tool.git.commit-files` with `repository` and `commitId`, the MCP gateway publishes that payload, and the `git-commit-files` worker uploads changed files to S3 under `{commitId}/{filePath}`. The agent then reads those S3 keys through `mcp.tool.files` and experts analyze the retrieved contents.

Branch-level RAG indexing already exists, but it is background context only. It cannot be treated as the source of files for LLM analysis because existing specs intentionally separate RAG context from MCP-retrieved analysis files.

## Goals / Non-Goals

**Goals:**

- Support `scan_mode=commit` and `scan_mode=full` with commit mode as the default.
- Propagate scan mode as structured data from API trigger to LangGraph state and MCP gateway input.
- Extend the existing `mcp.tool.git.commit-files` contract instead of adding a separate tool.
- Let the worker enumerate a full branch/ref file tree when full mode is selected.
- In full mode, prefer analysis accuracy over speed by requiring RAG freshness for the target commit/ref before expert analysis.
- Keep S3 paths and returned metadata unambiguous for commit and full modes.

**Non-Goals:**

- Replace RAG indexing or use RAG as the primary file source.
- Remove existing commit scan behavior or rename the existing MCP tool.
- Add local git clone support beyond the current provider clients unless needed by existing clients.
- Add repository-wide risk ranking or file sampling heuristics in this change.

## Decisions

1. Use `scan_mode` / `scanMode` instead of a boolean flag.

   Rationale: a mode enum is easier to extend and clearer in API, agent, and MCP logs. Alternatives considered: `full_scan: true` is simpler but creates ambiguous defaults and does not scale to future modes; a separate MCP tool avoids optional parameters but duplicates gateway/worker flow.

2. Preserve `mcp.tool.git.commit-files` and extend its schema.

   Rationale: the agent already depends on this async gateway flow and existing consumers continue to work when `scanMode` is omitted. The gateway input should accept `repository`, `commitId`, optional `branch`, and optional `scanMode`; full mode requires `branch`.

3. Normalize the scan mode at the API boundary and again defensively in the agent.

   Rationale: the trigger API owns user input validation, while the agent must remain robust for older persisted tasks. Missing mode means `commit`; invalid mode fails before invoking MCP.

4. Pass scan parameters as structured state, not only prompt text.

   Rationale: `LangGraphAgent._parse_message_content()` currently extracts only repository, branch, and commit. Depending on prompt parsing for operational parameters is brittle. The implementation should either extend agent invocation metadata or parse a dedicated machine-readable section, then populate `AgentState.scan_mode` and `AgentState.scan_ref`.

5. Require RAG freshness for full scan mode.

   Rationale: full scan mode is intended to maximize precision, not speed. The current pre-scan check only verifies that a branch index exists, which can allow stale context if deltas failed or external changes occurred. In full mode, the agent should call `is_commit_indexed(repository_url, branch, commit_hash)` before analysis and trigger/wait for indexing when the target commit is not indexed. Alternatives considered: use any existing branch index for speed; this is rejected for full mode because stale dependency context can reduce finding quality.

6. Use distinct S3 storage prefixes per mode.

   Rationale: commit mode keeps `{commitId}/{filePath}` for compatibility. Full mode uses a non-conflicting prefix derived from the job, such as `full/{jobId}/{filePath}`, and returns `storagePrefix` so the agent can normalize analysis paths back to repository-relative paths.

## Risks / Trade-offs

- Large repositories can exceed LLM context or MCP/Lambda processing limits -> keep existing expert truncation, add tests for large path lists, and accept slower full scans when needed for accuracy.
- Waiting for RAG freshness can make full scans much slower -> limit this behavior to full mode and keep commit mode compatible with the existing branch-index check.
- Provider APIs have different tree listing semantics -> implement provider-specific pagination and only return downloadable regular files.
- Full mode may create many S3 objects per scan -> use an isolated prefix per job and rely on existing bucket lifecycle/cleanup policies or add cleanup later.
- Case conversion can break new fields -> align gateway camelCase schema with worker snake_case DTOs and test the published payload shape.
- Findings may include S3 prefixes instead of repository paths -> normalize paths in the agent before expert prompts and final reporting.

## Migration Plan

1. Ship gateway and worker changes with `scanMode` optional and defaulting to commit mode.
2. Ship API and agent propagation changes; older tasks without `scan_mode` continue as commit scans.
3. Update RAG pre-scan logic so full mode waits for commit/ref freshness before analysis.
4. Update `src/api/task/trigger/task.http` with examples for default commit mode and explicit full mode.
5. Add full mode tests in API, agent, gateway, worker, and RAG freshness handling.
6. Rollback by disabling callers from sending `scan_mode=full`; commit mode remains compatible.

## Open Questions

- Should the public API expose only `scan_mode`, or also allow an explicit `scan_ref` separate from `branch`?
- Should full scan mode have a maximum file count or repository size guard before implementation goes to production?
