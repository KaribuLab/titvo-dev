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
