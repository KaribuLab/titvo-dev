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

### Requirement: Merge node consolidates repeated expert findings

The LangGraph merge step SHALL consolidate findings that refer to the same underlying vulnerability before producing `final_output.issues`. The consolidated finding SHALL keep the existing issue JSON structure used by reports and downstream tools; it SHALL NOT wrap duplicates in a new nested `merged` object or otherwise change the annotation schema. Consolidation MAY combine useful description, summary, and remediation details from multiple experts when they report the same weakness.

#### Scenario: Same code evidence with different categories

- **WHEN** two expert findings have the same repository path, same line, and same normalized code snippet, but different titles or categories
- **THEN** the merge step returns a single issue in `final_output.issues`
- **AND** the returned issue keeps the existing fields such as `title`, `description`, `severity`, `category`, `path`, `line`, `summary`, `code`, and `recommendation`

#### Scenario: One code snippet contains the other

- **WHEN** two expert findings have the same repository path and line
- **AND** both findings include code snippets where one normalized snippet contains the other
- **THEN** the merge step returns a single issue in `final_output.issues`
- **AND** the merged issue uses the finding with the more complete code snippet as the primary output shape/content

#### Scenario: Duplicate where only one finding has code

- **WHEN** two expert findings are duplicate candidates for the same repository path and line
- **AND** one finding has a non-empty `code` value while the other has no code example
- **THEN** the merged issue uses the finding that has the code example as the primary output shape/content

#### Scenario: Duplicate report items are not rendered twice

- **WHEN** duplicate expert findings are collapsed by the merge step
- **THEN** the generated report receives only the deduplicated issue list and does not render repeated findings for the same evidence

### Requirement: Merge node uses model-based findings consolidation

When two or more findings remain, the LangGraph merge step SHOULD ask the model to produce a final consolidated issue list. The consolidation pass SHALL send the full structured findings produced by the experts, without pre-grouping, filtering, or selecting candidate pairs in code. The model SHALL decide which findings describe the same underlying vulnerability and SHALL return only JSON containing final issues with the existing issue fields: `title`, `description`, `severity`, `category`, `path`, `line`, `summary`, `code`, and `recommendation`.

The consolidation prompt SHALL live in a Markdown file bundled with the agent package, not as a hardcoded string in Python. The consolidation pass SHALL preserve concrete evidence from the input findings and SHALL NOT invent files or code snippets. When multiple findings describe the same vulnerability in the same file, the model MAY choose a representative line from the input findings for that file. When multiple findings describe the same root problem or affected security control, the output SHOULD combine complementary feedback from those findings into one clearer issue, preserve the highest severity, and use the most actionable path/line/code evidence. The merge step SHALL accept strict JSON returned as plain text, fenced text, embedded text, or structured chat content blocks where a block `text` field is already an object containing `issues`. The merge step SHALL NOT apply deterministic deduplication, candidate selection, exact-evidence cleanup, or severity heuristics before or after model consolidation. If the model fails, times out, returns invalid JSON, or returns an invalid issue shape, the merge step SHALL log the response shape and a compact redacted preview of the returned content before keeping the original expert findings without failing the scan.

#### Scenario: Equivalent findings from different experts

- **WHEN** web and mobile experts report the same token storage weakness with different titles, summaries, or recommendations
- **THEN** the consolidation pass returns one issue using the existing issue fields
- **AND** the issue MAY combine useful explanation or remediation details from both experts

#### Scenario: Consolidation payload remains bounded

- **WHEN** the consolidation pass is invoked
- **THEN** the model input includes structured expert findings and not precomputed duplicate groups or candidate pairs
- **AND** it does not include full file contents, RAG context, or expert prompts

#### Scenario: Consolidation prompt is externalized

- **WHEN** the merge node builds the consolidation request
- **THEN** it loads the prompt instructions from a Markdown prompt resource bundled with the agent package
- **AND** the Python code only injects the serialized findings payload into that template

#### Scenario: Consolidation failure falls back safely

- **WHEN** the model call fails, times out, or returns invalid JSON
- **THEN** the merge step logs the response shape and compact redacted preview without full code snippets
- **AND** keeps the original expert findings without failing the scan

#### Scenario: Structured content block response

- **WHEN** the model response content is a list of chat blocks and a block `text` value is already an object with `issues`
- **THEN** the merge step parses that object directly instead of converting the whole content list to a Python string representation
- **AND** no JSON repair call is required

#### Scenario: No deterministic merge cleanup

- **WHEN** the consolidation model returns valid issues, even if they appear duplicate
- **THEN** the merge step uses the model output as-is after schema/evidence validation
- **AND** it does not call deterministic merge or deduplication logic to alter that output
