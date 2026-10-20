## ADDED Requirements
### Requirement: CLI no dispara delta Git
CLI tasks SHALL bypass post-scan Git delta indexing.
#### Scenario: Resultado CLI
- **WHEN** a CLI analysis returns
- **THEN** no remote Git delta job is triggered
