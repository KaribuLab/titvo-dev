## MODIFIED Requirements

### Requirement: MCP retrieval implements gateway async commit-files contract

The `mcp_retrieve` node SHALL use the MCP **`tools/call`** flow compatible with Titvo Gateway:

1. Call **`mcp.tool.git.commit-files`** (or equivalent resolved tool name) with **`repository`** and **`commitId`** matching the scan task.
2. Read **`jobId`** from the response (JSON object with `jobId` / `pollToolName` per gateway contract).
3. Repeatedly call **`mcp.tool.git.commit-files.poll`** with **`jobId`** until **`status`** is **`SUCCESS`** or **`FAILURE`**, backing off between attempts within configured limits.
4. On **`SUCCESS`**, extract **`filesPaths`** from the polled payload (**top-level** or **`data.filesPaths`** as returned).
5. For each path, call **`mcp.tool.files`** (**or **`files`** resolved name**) with argument **`path`** only, and accumulate `{path, content}` into **`state.files`**.
6. After populating `state.files`, if `state.is_delta` is `true`, the node SHALL also set `state.delta_paths` from the intersection of retrieved paths and the known diff paths (provided at graph initialization).

If **`git.commit-files`** or **`poll`** returns failure, times out, or yields no paths, the node MUST set **`mcp_error`**, **`files`** empty, **`scaned_files`**: 0, `delta_paths`: [], and optional **`status`**: **`FAILED`** as implemented.

#### Scenario: Successful file retrieval in delta mode

- **WHEN** the async job completes with `SUCCESS`, non-empty `filesPaths`, and `is_delta` is `true`
- **THEN** **`state.files`** lists all successfully read blobs, **`state.scaned_files`** reflects the count, and **`state.delta_paths`** contains the paths that are part of the commit diff

#### Scenario: Successful file retrieval in full mode

- **WHEN** the async job completes with `SUCCESS` and `is_delta` is `false`
- **THEN** **`state.files`** lists all successfully read blobs and **`state.delta_paths`** remains empty

#### Scenario: MCP or job failure early exit

- **WHEN** commit-files job fails (`FAILURE`) or polling exceeds limits
- **THEN** **`state.mcp_error`** is populated, **`state.files`** MAY be empty, and **`state.delta_paths`** is empty; conditional routing skips experts.
