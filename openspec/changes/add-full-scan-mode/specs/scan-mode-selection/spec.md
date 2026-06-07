## ADDED Requirements

### Requirement: Trigger API accepts scan mode selection
The trigger API SHALL accept an optional `scan_mode` argument for all scan sources. Valid values SHALL be `commit` and `full`. When `scan_mode` is absent, empty, or not provided by an older caller, the system SHALL use `commit` mode.

#### Scenario: Default commit mode
- **WHEN** a scan request is submitted without `scan_mode`
- **THEN** the trigger API stores and propagates `scan_mode: "commit"`

#### Scenario: Full mode requested
- **WHEN** a scan request is submitted with `scan_mode: "full"` and a valid branch for the source
- **THEN** the trigger API accepts the request and stores `scan_mode: "full"`

#### Scenario: Invalid scan mode rejected
- **WHEN** a scan request is submitted with a `scan_mode` value other than `commit` or `full`
- **THEN** the trigger API rejects the request with a descriptive argument validation error

### Requirement: Scan mode is persisted with the task
The system SHALL persist the normalized scan mode in the task arguments so the agent can load the selected file scope from DynamoDB or the configured task repository.

#### Scenario: Persisted commit scan mode
- **WHEN** a commit-mode scan task is saved
- **THEN** the task arguments include `scan_mode: "commit"`

#### Scenario: Persisted full scan mode
- **WHEN** a full-mode scan task is saved
- **THEN** the task arguments include `scan_mode: "full"` and the task includes the selected branch

### Requirement: Agent receives scan mode as structured state
The agent SHALL derive the scan mode from the loaded task and provide it to LangGraph as structured state, not solely as natural-language prompt content.

#### Scenario: Agent initializes commit mode state
- **WHEN** the agent executes a task with `scan_mode: "commit"`
- **THEN** the initial LangGraph state includes `scan_mode: "commit"`

#### Scenario: Agent initializes full mode state
- **WHEN** the agent executes a task with `scan_mode: "full"`
- **THEN** the initial LangGraph state includes `scan_mode: "full"` and a scan reference based on the task branch

#### Scenario: Older task without scan mode
- **WHEN** the agent executes a persisted task that has no `scan_mode` argument
- **THEN** the agent treats the task as `commit` mode
