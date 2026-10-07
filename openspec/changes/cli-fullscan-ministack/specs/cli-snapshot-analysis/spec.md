## ADDED Requirements
### Requirement: Snapshot local verificable
The CLI SHALL select UTF-8 files from the local working tree, honor Git ignores including initialized submodules, exclude dependencies/builds/symlinks, and display a preview. It SHALL create a tar.gz with per-file hashes and an exclusion inventory.
#### Scenario: Cambios locales
- **WHEN** a tracked file has uncommitted changes
- **THEN** the snapshot contains its current content
### Requirement: Recuperación íntegra
The agent SHALL retrieve all registered batch packages and validate paths, limits, duplicate paths and optional manifest hashes before analysis.
#### Scenario: Paquete corrupto
- **WHEN** a manifest file is missing or differs
- **THEN** retrieval fails without analyzing a partial snapshot
### Requirement: Laboratorio honesto
The lab SHALL use MiniStack S3/DynamoDB and an actual Docker worker; mock reports MUST clearly state that they do not assess security.
#### Scenario: Batch simulado
- **WHEN** a task is analyzed
- **THEN** completion is based on the worker result, not MiniStack Batch SUCCEEDED
### Requirement: Sesión interactiva de terminal
The CLI SHALL launch an arrow-key menu when invoked without arguments in a terminal, retain project and scope during the session, allow choosing mock or real mode and masked provider credentials, and return to the menu after a scan. It SHALL keep secrets in process memory without saving them to disk and require explicit authorization before a real scan. Non-interactive invocation SHALL continue to display help.
#### Scenario: Resultado con hallazgos
- **WHEN** a scan finishes with complete execution coverage and a FAILED evaluation due to findings
- **THEN** the terminal explains that the analysis completed with findings and returns to the menu
#### Scenario: Envío remoto cancelado
- **WHEN** the user declines authorization for a real-model scan
- **THEN** the CLI performs no scan or upload and returns to the menu
#### Scenario: Salida de sesión
- **WHEN** the user exits the menu
- **THEN** AI configuration inherited by the process is restored and no session credentials are persisted
### Requirement: Revisión guiada y preferencias locales
The interactive CLI SHALL present a compact block-character robot and one primary review action. Missing project, scope and model choices SHALL be requested in order. Non-secret preferences SHALL be remembered locally; credentials SHALL NOT be serialized.
#### Scenario: Retomar preferencias
- **WHEN** the user starts the CLI again with saved preferences
- **THEN** it restores the project, scope and model settings without loading a persisted API key
### Requirement: Confirmación y avance de revisión guiada
A real scan SHALL require one explicit confirmation after preview, without uploading when declined. Review progress SHALL use actual worker batch counters and separate technical logs from normal output.
#### Scenario: Confirmación de revisión real
- **WHEN** the user declines the final real-model confirmation
- **THEN** no snapshot is uploaded and the interactive menu remains available
### Requirement: Exploración de hallazgos en terminal
Saved findings SHALL be navigable in the terminal with evidence and recommendations.
#### Scenario: Explorar hallazgo
- **WHEN** the user selects a saved finding
- **THEN** the CLI displays its path, line, evidence and recommendation without executing project code

### Requirement: Final execution and AI usage summary
The CLI worker SHALL persist task and agent durations, completed and total batches,
provider-reported input/cached/output tokens and per-task model call counts including
corrections and consolidation. CLI, HTML and dashboard SHALL display the same summary.
Pricing SHALL be snapshotted and identified as estimated USD for model calls only.

#### Scenario: Complete measured usage
- **WHEN** every real model call supplies valid usage and a known tariff
- **THEN** the summary discounts cached input, sums all calls and marks cost estimated

#### Scenario: Missing usage or pricing
- **WHEN** telemetry or pricing is unavailable for all or some calls
- **THEN** the summary marks cost unavailable or partial and never claims a known total

#### Scenario: Historical report and simulated model
- **WHEN** a historical report lacks metrics or a scan uses the simulated model
- **THEN** historical cost is unrecorded and simulated cost is explicitly zero

### Requirement: Existing dashboard against local artifacts
The laboratory SHALL provide a loopback-only read adapter exposing the existing
frontend repo/scan contracts backed by MiniStack tasks and reports. The frontend
SHALL identify laboratory mode and its read-only scope without changing production auth.

#### Scenario: View the same CLI analysis in the dashboard
- **WHEN** a local task has persisted its report
- **THEN** the dashboard displays its summary, coverage and findings using that report

#### Scenario: Read-only boundaries
- **WHEN** a browser attempts admin writes or sends an external origin to the lab API
- **THEN** writes are denied and external origins cannot read code evidence

### Requirement: Branded terminal workspace and keyboard navigation
The interactive CLI SHALL use Titvo indigo colors and replace nested menus in a
single alternate terminal workspace. List navigation SHALL support arrows and
Vim keys, without intercepting text/password inputs. Exit SHALL restore the shell.

#### Scenario: Move between nested menus
- **WHEN** the user navigates using arrows or j/k and confirms with Enter/l
- **THEN** the next menu replaces the previous one and Esc/h returns to its parent

#### Scenario: Explicit exit and back choices
- **WHEN** the user selects Salir or Volver with Enter/l
- **THEN** Salir closes the session and restores the shell, and Volver returns to its parent
- **AND** exit/back actions do not dispatch a scan or repeat the current menu
- **AND** closing the session displays a farewell and confirms reports remain saved

#### Scenario: Work animation and reduced motion
- **WHEN** a scan is running on a compatible terminal
- **THEN** the compact mascot animates without modifying measured progress
- **AND** NO_COLOR or TITVO_NO_ANIMATION disables motion

### Requirement: Ordered and explorable dashboard results
The dashboard SHALL prioritize summary and coverage, order findings by severity,
file and line, and provide search, severity filtering and pagination. Evidence,
recommendation, usage and technical JSON SHALL remain accessible via disclosures.

#### Scenario: Filter a report without dropping results
- **WHEN** the user searches or filters a report with more than twenty findings
- **THEN** matching findings are paginated, changing a filter resets the page,
  and clearing filters restores access to all original findings

### Requirement: Independent execution, security and technical error outcomes
CLI and dashboard SHALL display execution, security findings and technical errors
as independent facts. Complete coverage SHALL mean completed execution even when
the evaluation status is FAILED. The original evaluation SHALL remain in technical data.
Local dashboard summaries SHALL expose measured execution separately from raw status.

#### Scenario: Completed scan with findings
- **WHEN** coverage is complete and the report contains findings
- **THEN** CLI and dashboard show completed execution and findings without implying a technical failure

#### Scenario: Partial or failed execution
- **WHEN** coverage is incomplete with some completed batches
- **THEN** execution is incomplete and any findings and technical errors remain visible
- **WHEN** coverage is incomplete, zero batches completed and an error is recorded
- **THEN** execution is failed

#### Scenario: Independent errors and historical coverage
- **WHEN** execution is complete and a technical diagnostic is recorded
- **THEN** the UI shows completed execution with technical errors separately
- **WHEN** execution coverage is absent
- **THEN** execution is not recorded rather than inferred from findings or raw FAILED


### Requirement: Selectable MiniStack and AWS transport
The CLI SHALL offer an explicit MiniStack or AWS destination in menus and commands,
remember non-secret destination settings, show the actual destination before
upload and never fall back to another destination automatically.

#### Scenario: AWS fullscan through the existing service
- **WHEN** the user selects AWS and supplies an HTTPS API endpoint, a Titvo API key and repository identity
- **THEN** the CLI SHALL obtain a presigned URL, PUT the immutable package without the Titvo key, trigger source=cli with scan_mode=full, and consult the task until terminal status or a bounded timeout
- **AND** the model SHALL be configured by the service rather than the user's local AI key

#### Scenario: Cloud wait interrupted or timed out
- **WHEN** polling is interrupted or its deadline expires
- **THEN** the CLI SHALL display the existing task identifier and consultation command without restarting or cancelling the AWS task

#### Scenario: AWS findings in the external HTML report
- **WHEN** the service returns a count and report URL without inline issues
- **THEN** the CLI SHALL display the recorded count and allow opening the full report without reporting zero findings

#### Scenario: Local execution after switching back
- **WHEN** the user selects MiniStack
- **THEN** the existing SDK, Docker, mock/real selection and read-only local dashboard SHALL remain available
