## Why

Current security scans analyze only the files returned by the MCP `git.commit-files` tool for a specific commit. This misses vulnerabilities that depend on repository-wide context or files untouched by the commit, even though the agent already maintains branch-level RAG background context.

## What Changes

- Add an explicit scan mode contract so callers can request either commit-only analysis or full repository analysis.
- Propagate the selected scan mode from the trigger API through the persisted task, agent state, MCP gateway tool schema, and `git-commit-files` worker.
- Extend MCP git file retrieval to enumerate and upload all files for a branch/ref when full scan mode is selected.
- Preserve the existing commit scan behavior as the default mode.
- Return enough metadata from MCP polling to identify the mode and storage prefix used for retrieved files.
- In full scan mode, verify that RAG context is fresh for the target commit/ref before analysis, even if this makes the scan slower.

## Capabilities

### New Capabilities
- `scan-mode-selection`: Defines how scans select, validate, persist, and propagate `commit` vs `full` analysis mode.
- `mcp-git-file-retrieval`: Defines the MCP gateway and worker contract for retrieving either commit files or full branch/ref file snapshots.

### Modified Capabilities
- `langgraph-orchestration`: `mcp_retrieve` must pass scan mode/ref into MCP retrieval and analyze the resulting file set.
- `agent-rag-context`: The agent must distinguish selected analysis files from RAG background context for both commit and full scan modes.
- `rag-pre-scan-full-indexing`: Full scan mode must wait for RAG freshness at the target commit/ref, not only for an existing branch index.

## Non-goals

- Do not replace RAG indexing or use RAG as the primary source of files to analyze.
- Do not change expert prompts beyond wording needed to identify the selected file scope.
- Do not remove or rename the existing `mcp.tool.git.commit-files` tool.
- Do not implement incremental repository indexing in this change.

## Impact

- API trigger: accepts and persists scan mode while defaulting to commit mode.
- Agent: carries scan mode as structured state instead of relying on prompt parsing.
- RAG pre-scan: full mode validates freshness against the target commit/ref and waits for indexing when stale.
- MCP gateway: updates tool input/output schemas, descriptions, and result mapping.
- MCP `git-commit-files`: lists files by commit or branch/ref, downloads them, uploads to S3, and reports metadata.
- Repository clients: GitHub and Bitbucket gain full tree listing support.
- API examples: `src/api/task/trigger/task.http` is updated with commit and full scan request examples.
- Tests and OpenSpec specs are updated across `src/api`, `src/agent`, `src/mcp/gateway`, and `src/mcp/git-commit-files`.
