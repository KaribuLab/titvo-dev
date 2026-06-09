## Context

The current scan flow is commit-scoped. The trigger API persists SCM arguments, the agent loads the task, `MCPRetrievalNode` invokes `mcp.tool.git.commit-files` with `repository` and `commitId`, the MCP gateway publishes that payload, and the `git-commit-files` worker uploads changed files to S3 under `{commitId}/{filePath}`. The agent then reads those S3 keys through `mcp.tool.files` and experts analyze the retrieved contents.

Branch-level RAG indexing already exists, but it is background context only. It cannot be treated as the source of files for LLM analysis because existing specs intentionally separate RAG context from MCP-retrieved analysis files.

## Goals / Non-Goals

**Goals:**

- Support `scan_mode=commit` and `scan_mode=full` with commit mode as the default.
- Propagate scan mode as structured data from API trigger to LangGraph state and MCP gateway input.
- Extend the existing `mcp.tool.git.commit-files` contract instead of adding a separate tool.
- Let the worker enumerate the full file tree for the selected branch in full mode.
- Resolve the selected branch to its current HEAD commit before provider tree listing/downloading, so full mode scans the branch's latest snapshot rather than only the trigger commit.
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

6. Resolve full-mode branch refs to provider HEAD commits before listing files.

   Rationale: users requesting `scan_mode=full` want the current full contents of the selected branch, not the file set changed by the trigger commit. The branch name remains the user-selected scope, while `scanRef` should represent the concrete provider revision used to retrieve files. For Bitbucket, branch names such as `feature/titvo-integration` cannot be passed raw to `/src/{commit}/{path}` because the API interprets `feature` as the commit/ref and `titvo-integration` as the path. Resolving the branch through the provider refs API and then using the resulting HEAD commit avoids slash ambiguity and makes the scan snapshot explicit.

7. Use distinct S3 storage prefixes per mode.

   Rationale: commit mode keeps `{commitId}/{filePath}` for compatibility. Full mode uses a non-conflicting prefix derived from the job, such as `full/{jobId}/{filePath}`, and returns `storagePrefix` so the agent can normalize analysis paths back to repository-relative paths.

8. Deduplicate duplicate expert findings deterministically without changing issue shape.

   Rationale: full scans increase the chance that multiple experts report the same underlying weakness. The merge step should collapse findings that point to the same evidence, such as identical repository path, line, and code snippet, even when titles or categories differ. The merged issue should preserve the existing issue/report JSON structure instead of introducing a new nested merge object. When duplicate candidates differ in evidence quality, the issue containing a non-empty code example should win over an otherwise equivalent issue without code because it is more actionable in the final report.

## Risks / Trade-offs

- Large repositories can exceed LLM context or MCP/Lambda processing limits -> keep existing expert truncation, add tests for large path lists, and accept slower full scans when needed for accuracy.
- Waiting for RAG freshness can make full scans much slower -> limit this behavior to full mode and keep commit mode compatible with the existing branch-index check.
- Provider APIs have different tree listing semantics -> implement provider-specific branch HEAD resolution, pagination, and only return downloadable regular files.
- Branch names can contain path separators -> never pass branch names with `/` raw into provider endpoints that parse refs and paths from the same URL segment; resolve or encode according to provider semantics.
- Full mode may create many S3 objects per scan -> use an isolated prefix per job and rely on existing bucket lifecycle/cleanup policies or add cleanup later.
- Case conversion can break new fields -> align gateway camelCase schema with worker snake_case DTOs and test the published payload shape.
- Findings may include S3 prefixes instead of repository paths -> normalize paths in the agent before expert prompts and final reporting.
- Multiple experts can report the same issue with different titles/categories -> deduplicate by stable evidence while preserving the current report annotation shape.

## Migration Plan

1. Ship gateway and worker changes with `scanMode` optional and defaulting to commit mode.
2. Ship API and agent propagation changes; older tasks without `scan_mode` continue as commit scans.
3. Update RAG pre-scan logic so full mode waits for branch HEAD commit/ref freshness before analysis.
4. Update `src/api/task/trigger/task.http` with examples for default commit mode and explicit full mode.
5. Add full mode tests in API, agent, gateway, worker, and RAG freshness handling.
6. Rollback by disabling callers from sending `scan_mode=full`; commit mode remains compatible.

## Open Questions

- Should the public API expose only `scan_mode`, or also allow an explicit `scan_ref` separate from `branch` for advanced callers that want a fixed historical snapshot instead of branch HEAD?
- Should full scan mode have a maximum file count or repository size guard before implementation goes to production?
