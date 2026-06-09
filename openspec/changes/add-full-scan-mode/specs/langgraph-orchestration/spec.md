## MODIFIED Requirements

### Requirement: MCP retrieval implements gateway async commit-files contract

The `mcp_retrieve` node SHALL use the MCP **`tools/call`** flow compatible with Titvo Gateway:

1. Call **`mcp.tool.git.commit-files`** (or equivalent resolved tool name) with **`repository`**, **`commitId`**, **`scanMode`**, and when available **`branch`** matching the scan task. If `scanMode` is missing from state, it SHALL default to **`commit`**.
2. Read **`jobId`** from the response (JSON object with `jobId` / `pollToolName` per gateway contract).
3. Repeatedly call **`mcp.tool.git.commit-files.poll`** with **`jobId`** until **`status`** is **`SUCCESS`** or **`FAILURE`**, backing off between attempts within configured limits.
4. On **`SUCCESS`**, extract **`filesPaths`** from the polled payload (**top-level** or **`data.filesPaths`** as returned), plus optional **`scanMode`**, **`scanRef`**, and **`storagePrefix`** metadata.
5. For each path, call **`mcp.tool.files`** (**or **`files`** resolved name**) with argument **`path`** only, and accumulate readable files into **`state.files`**.
6. When a **`storagePrefix`** is returned, normalize file paths in **`state.files`** to repository-relative paths before expert analysis while still using the storage path to read content.

If **`git.commit-files`** or **`poll`** returns failure, times out, or yields no paths, the node MUST set **`mcp_error`**, **`files`** empty, **`scaned_files`**: 0, and optional **`status`**: **`FAILED`** as implemented.

#### Scenario: Successful file retrieval

- **WHEN** the async job completes with `SUCCESS` and non-empty `filesPaths`
- **THEN** **`state.files`** lists all successfully read blobs and **`state.scaned_files`** reflects the count of items with content.

#### Scenario: MCP or job failure early exit

- **WHEN** commit-files job fails (`FAILURE`) or polling exceeds limits
- **THEN** **`state.mcp_error`** is populated and **`state.files`** MAY be empty; conditional routing skips experts.

#### Scenario: Full scan retrieval

- **WHEN** the state contains `scan_mode: "full"` and a branch
- **THEN** `mcp_retrieve` invokes the gateway with full-mode parameters and stores repository-relative paths for the retrieved files.

### Requirement: Merge node deduplicates repeated expert findings

The LangGraph merge step SHALL deduplicate findings that refer to the same concrete code evidence before producing `final_output.issues`. The merged finding SHALL keep the existing issue JSON structure used by reports and downstream tools; it SHALL NOT wrap duplicates in a new nested `merged` object or otherwise change the annotation schema.

#### Scenario: Same code evidence with different categories

- **WHEN** two expert findings have the same repository path, same line, and same normalized code snippet, but different titles or categories
- **THEN** the merge step returns a single issue in `final_output.issues`
- **AND** the returned issue keeps the existing fields such as `title`, `description`, `severity`, `category`, `path`, `line`, `summary`, `code`, and `recommendation`

#### Scenario: Duplicate where only one finding has code

- **WHEN** two expert findings are duplicate candidates for the same repository path and line
- **AND** one finding has a non-empty `code` value while the other has no code example
- **THEN** the merged issue uses the finding that has the code example as the primary output shape/content

#### Scenario: Duplicate report items are not rendered twice

- **WHEN** duplicate expert findings are collapsed by the merge step
- **THEN** the generated report receives only the deduplicated issue list and does not render repeated findings for the same evidence
