## 1. API Trigger Contract

- [x] 1.1 Add scan mode normalization and validation for `commit` and `full` in the trigger API flow.
- [x] 1.2 Persist normalized `scan_mode` in saved task args while preserving existing commit-mode behavior for older callers.
- [x] 1.3 Add or update trigger strategy tests for missing, valid, and invalid `scan_mode` values across GitHub, Bitbucket, and CLI where applicable.
- [x] 1.4 Update `src/api/task/trigger/task.http` with request examples for default commit mode and explicit `scan_mode: "full"`.

## 2. Agent Propagation

- [x] 2.1 Add structured scan mode fields to LangGraph state and default missing values to `commit`.
- [x] 2.2 Propagate scan mode and branch/ref from the loaded task into the agent workflow without relying only on prompt parsing.
- [x] 2.3 Update pre-scan RAG logic so full mode validates `is_commit_indexed(repository_url, branch, commit_hash)` and waits for indexing when stale.
- [x] 2.4 Keep commit mode compatible with the existing branch-index check.
- [x] 2.5 Update `MCPRetrievalNode` to invoke `mcp.tool.git.commit-files` with `scanMode` and `branch` when available.
- [x] 2.6 Normalize returned storage-prefixed file paths to repository-relative paths before expert prompts and final reporting.
- [x] 2.7 Add unit tests for commit mode defaulting, full mode RAG freshness, stale RAG indexing wait, and full mode MCP invocation in `src/agent`.
- [x] 2.8 Update findings merge/dedup logic to collapse duplicate expert findings by stable code evidence while preserving the existing issue JSON/report shape; prefer findings with non-empty `code` when duplicates differ.
- [x] 2.9 Deduplicate duplicate findings when one normalized code snippet contains the other, preserving the more complete code evidence.
- [x] 2.10 Add low-token semantic deduplication as a second merge pass after deterministic deduplication, with safe fallback on model errors or invalid JSON.
- [x] 2.11 Replace semantic duplicate grouping with model-based findings consolidation that returns the final issue list while preserving the existing issue JSON shape.
- [x] 2.12 Add a regression test for consolidating equivalent `localStorage` token findings from different experts into one enriched issue.
- [x] 2.13 Move findings consolidation instructions to a bundled Markdown prompt file and have the merge node load it through the prompt registry.
- [x] 2.14 Send all structured expert findings to the consolidation model without precomputing candidate pairs or blocking equivalent findings on nearby line differences.
- [x] 2.15 Update the consolidation prompt to merge aggressively by root security problem/control, and add final exact-evidence cleanup if the model returns duplicate report items.
- [x] 2.16 Remove deterministic findings merge/deduplication from `FindingsMerger` and from merge-node fallback/cleanup so the consolidation agent is the only component that decides final grouping.
- [x] 2.17 Add robust JSON parsing and model-assisted JSON repair for consolidation responses, preserving original findings if parsing and repair both fail.
- [x] 2.18 Parse structured chat content block responses from the consolidation model and log redacted response shape/preview when parsing fails.

## 3. MCP Gateway Contract

- [x] 3.1 Extend `GetCommitInputDto` to accept optional `scanMode` and `branch` fields with validation and descriptions.
- [x] 3.2 Update `mcp.tool.git.commit-files` descriptions to document commit mode, full mode, and required branch/ref behavior.
- [x] 3.3 Extend `GitCommitFilesOutputDto` and poll result mapping for `scanMode`, `scanRef`, and `storagePrefix`.
- [x] 3.4 Add gateway tests for schema generation, full-mode input validation, and snake_case to camelCase result mapping.

## 4. Git File Worker

- [x] 4.1 Extend `GitCommitFilesInputDto` and output DTOs to accept mode/ref metadata from gateway-published snake_case payloads.
- [x] 4.2 Refactor worker processing to select commit file listing or full branch/ref listing based on scan mode.
- [x] 4.3 Preserve commit-mode S3 keys as `{commitId}/{filePath}`.
- [x] 4.4 Add full-mode S3 storage prefixes that cannot collide with commit-mode keys and return `storage_prefix`.
- [x] 4.5 Add worker service tests for commit defaulting, full mode processing, failure handling, and returned metadata.

## 5. Repository Providers

- [x] 5.1 Extend the shared `RepoClient` interface with full tree listing and ref-based download support.
- [x] 5.2 Implement paginated full tree listing for GitHub regular files at a branch/ref.
- [x] 5.3 Implement paginated full tree listing for Bitbucket regular files at a branch/ref.
- [x] 5.4 Add provider tests for pagination, directory filtering, removed-file behavior, and file downloads by ref.
- [x] 5.5 Resolve full-mode branch/ref input to the provider HEAD commit before tree listing and downloads.
- [x] 5.6 Add provider tests proving full mode scans the branch HEAD full tree, not only the trigger commit diff.
- [x] 5.7 Add Bitbucket tests for branch names containing `/` (for example `feature/titvo-integration`) to ensure the branch is resolved before calling `/src/{commit}/{path}`.

## 6. End-to-End Verification

- [x] 6.1 Run relevant API trigger tests.
- [x] 6.2 Run relevant `src/agent` unit tests, including RAG freshness behavior for full mode.
- [x] 6.3 Run relevant `src/mcp/gateway` tests.
- [x] 6.4 Run relevant `src/mcp/git-commit-files` tests.
- [ ] 6.5 Exercise the updated `.http` examples against LocalStack or the local API when the environment is available.

## 7. Documentation

- [x] 7.1 Update `docs/architecture.md` to describe commit vs full scan mode across API, agent, gateway, and MCP worker.
- [x] 7.2 Update `docs/rag-indexer.md` to clarify that RAG remains background context and full scan mode waits for target commit/ref freshness.
- [x] 7.3 Update `docs/prompts.md` to document how prompts distinguish selected analysis files from RAG background context.

## 8. Bitbucket Code Insights Resilience

- [x] 8.1 Treat Bitbucket Code Insights publication as best-effort in `src/agent` so a Code Insights failure does not fail the entire scan after the HTML report is created.
- [x] 8.2 Pass scan mode to the Bitbucket Code Insights worker and publish reports with deterministic report IDs that differ for `commit` and `full` modes.
- [x] 8.3 Add regression tests for Code Insights fallback behavior and stable report IDs.
