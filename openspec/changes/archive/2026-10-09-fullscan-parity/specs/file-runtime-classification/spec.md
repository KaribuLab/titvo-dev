## ADDED Requirements

### Requirement: Every retrieved file is tagged with a deterministic ordered list of runtimes

The system SHALL classify every file in `state.files` with a non-empty ordered list `runtimes`
whose elements are from `browser`, `server`, `mobile`, `infra`, `test`, `config`, `unknown`. The
first element is the primary runtime. Classification MUST be a pure function of
`(path, content, project_profile)`: identical inputs MUST always yield the identical list, and no
LLM call MUST be involved. When a file shows signals of more than one runtime it SHALL receive all
of them, ordered `mobile`, `browser`, `server`.

#### Scenario: React component is classified as browser

- **WHEN** a file `src/components/Checkout.tsx` imports from `react`, does not import
  `react-native`, and the project profile is not `mobile_js`
- **THEN** its runtimes are `["browser"]`

#### Scenario: NestJS controller is classified as server

- **WHEN** a file `src/app/task/task.controller.ts` imports from `@nestjs/common`
- **THEN** its runtimes are `["server"]`

#### Scenario: React Native screen is classified as mobile

- **WHEN** a file `app/screens/Login.tsx` imports from `react-native`
- **THEN** its runtimes are `["mobile"]`

#### Scenario: File with both browser and server signals gets both

- **WHEN** a file imports `react` and `express`
- **THEN** its runtimes are `["browser", "server"]`

#### Scenario: Terraform and workflow files are classified as infra

- **WHEN** files `aws/batch/terragrunt.hcl` and `.github/workflows/deploy.yml` are retrieved
- **THEN** both have runtimes `["infra"]`

#### Scenario: Test file is classified as test regardless of content

- **WHEN** a file `tests/unit/test_task_service.py` imports `flask`
- **THEN** its runtimes are `["test"]`

#### Scenario: File without signals is classified as unknown

- **WHEN** a file `src/utils/format.ts` has no framework imports, its directory gives no hint and
  the project profile is empty
- **THEN** its runtimes are `["unknown"]`

### Requirement: A deterministic project profile widens classification

Before classifying files, the system SHALL build a project profile from all files in `state.files`
by inspecting `package.json` dependencies (`react-native`/`expo` → `mobile_js`; frontend
frameworks without server frameworks → `frontend_js`; server frameworks without frontend ones →
`backend_js`), `pubspec.yaml` → `flutter`, `Podfile` → `ios`, Android Gradle files → `android`.
The profile SHALL only add runtimes to a file, never remove them. When no profile file is present
the profile SHALL be empty and classification falls back to per-file signals.

#### Scenario: React Native component without explicit import still reaches mobile

- **WHEN** the project profile is `mobile_js` and a file `src/components/Card.tsx` imports only
  `react` and local modules
- **THEN** its runtimes include `mobile`

#### Scenario: Ambiguous file in a frontend project defaults to browser

- **WHEN** the project profile is `frontend_js` and a file `src/api/client.ts` has no framework
  imports
- **THEN** its runtimes are `["browser", "unknown"]`

#### Scenario: Commit without package.json yields empty profile

- **WHEN** a commit scan retrieves only `src/components/Card.tsx`
- **THEN** the project profile is empty and the file is classified by its own signals only

### Requirement: Runtime labels and coverage are attached to state before expert execution

The workflow SHALL run a `classify_runtime` node after `rag_retrieve` (or after `mcp_retrieve`
when RAG is absent) and before any expert node. The node SHALL add `runtimes` to each entry of
`state.files` without altering `path` or `content`, SHALL write `expert_metadata.project_profile`,
and SHALL write `expert_metadata.coverage` with the number of files each expert will select and
`files_without_domain_expert`. If any file would be selected by no domain expert, the node MUST
append `unknown` to its runtimes and log a warning.

#### Scenario: Files carry runtimes when experts start

- **WHEN** any expert node receives `state`
- **THEN** every item in `state.files` has `path`, `content` and non-empty `runtimes`

#### Scenario: Coverage invariant holds

- **WHEN** `classify_runtime` finishes
- **THEN** `expert_metadata.coverage.files_without_domain_expert` equals `0`

### Requirement: Runtime label is visible in the expert prompt

The formatted file header sent to the LLM SHALL include the primary runtime in the form
`=== FILE: <path> [runtime: <primary>] ===`, followed by `[lines <start>-<end> of <total>]` when
the file was split into chunks.

#### Scenario: Header includes runtime

- **WHEN** an expert formats a single-chunk file classified `["browser"]`
- **THEN** the human message contains `=== FILE: src/components/Checkout.tsx [runtime: browser] ===`
