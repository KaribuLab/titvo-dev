## ADDED Requirements

### Requirement: Bitbucket Code Insights is best-effort

Publishing Bitbucket Code Insights SHALL be treated as a notification side effect. If Code Insights publishing fails, returns an error payload, or omits `codeInsightsURL`, the scan SHALL keep the generated HTML report URL and SHALL NOT fail solely because Code Insights failed.

#### Scenario: Code Insights publish fails after report creation

- **WHEN** a Bitbucket scan produces findings and the HTML report is created successfully
- **AND** publishing Code Insights fails or returns an invalid payload
- **THEN** the scan result includes the HTML `report_url`
- **AND** the scan does not raise an exception solely due to the Code Insights failure

### Requirement: Bitbucket Code Insights report ID is stable by scan mode

The Bitbucket Code Insights worker SHALL publish scan reports using a deterministic report ID that includes the scan mode (`commit` or `full`). This allows repeated scans of the same commit and mode to update the same Code Insights report instead of creating unbounded new reports.

#### Scenario: Commit mode report ID

- **WHEN** Code Insights is published without a scan mode or with `scanMode: "commit"`
- **THEN** the Bitbucket report URL uses a deterministic commit-mode report ID

#### Scenario: Full mode report ID

- **WHEN** Code Insights is published with `scanMode: "full"`
- **THEN** the Bitbucket report URL uses a deterministic full-mode report ID distinct from commit mode
