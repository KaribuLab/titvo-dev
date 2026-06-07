## ADDED Requirements

### Requirement: Gateway git file tool accepts scan mode
The MCP gateway SHALL expose `mcp.tool.git.commit-files` with input fields for `repository`, `commitId`, optional `branch`, and optional `scanMode`. Missing `scanMode` SHALL mean `commit`. Full mode SHALL require a branch or equivalent ref.

#### Scenario: Existing commit invocation remains valid
- **WHEN** an agent invokes `mcp.tool.git.commit-files` with only `repository` and `commitId`
- **THEN** the gateway publishes a commit-mode job compatible with the existing worker flow

#### Scenario: Full invocation includes branch
- **WHEN** an agent invokes `mcp.tool.git.commit-files` with `scanMode: "full"` and `branch: "main"`
- **THEN** the gateway publishes a full-mode job containing the selected branch/ref

#### Scenario: Full invocation without branch is invalid
- **WHEN** an agent invokes `mcp.tool.git.commit-files` with `scanMode: "full"` and no branch/ref
- **THEN** the gateway rejects the invocation before publishing a worker job

### Requirement: Gateway maps full scan result metadata
The MCP gateway SHALL map worker result fields from snake_case to camelCase for `files_paths`, `commit_id`, `scan_mode`, `scan_ref`, and `storage_prefix` when returning poll results.

#### Scenario: Full scan poll success
- **WHEN** the worker completes a full-mode job and stores result metadata in snake_case
- **THEN** `mcp.tool.git.commit-files.poll` returns `filesPaths`, `commitId`, `scanMode`, `scanRef`, and `storagePrefix`

### Requirement: Worker retrieves commit files by default
The `git-commit-files` worker SHALL keep existing commit-mode behavior when the input mode is absent or `commit`: list changed files for `commitId`, skip files that cannot be downloaded, upload contents to S3, and return `filesPaths`.

#### Scenario: Commit mode worker processing
- **WHEN** the worker receives a job with `commitId: "abc123"` and no scan mode
- **THEN** it retrieves files changed by commit `abc123` and uploads them under the existing commit prefix

### Requirement: Worker retrieves full branch files
The `git-commit-files` worker SHALL support full-mode processing by listing all downloadable regular files for the selected branch/ref and uploading their current contents to S3.

#### Scenario: Full mode worker processing
- **WHEN** the worker receives `scan_mode: "full"` with branch/ref `main`
- **THEN** it enumerates all downloadable files at `main`, uploads them to S3, and returns their storage paths

#### Scenario: Provider pagination is followed
- **WHEN** the repository provider returns full tree files across multiple pages
- **THEN** the worker follows pagination until all pages have been processed

### Requirement: Storage prefixes are mode-safe
The worker SHALL use storage prefixes that do not collide between commit-mode and full-mode jobs. Commit mode SHALL preserve the existing `{commitId}/{filePath}` prefix. Full mode SHALL use a distinct prefix and return it as `storage_prefix`.

#### Scenario: Commit prefix preserved
- **WHEN** a commit-mode scan uploads `src/app.ts` for commit `abc123`
- **THEN** the returned path remains `abc123/src/app.ts`

#### Scenario: Full prefix returned
- **WHEN** a full-mode scan uploads `src/app.ts`
- **THEN** the returned path starts with the reported full-mode `storagePrefix`
