## ADDED Requirements
### Requirement: CLI no indexa Git
CLI tasks SHALL bypass Git RAG pre-indexing until snapshot-scoped indexing is supported.
#### Scenario: Snapshot local
- **WHEN** the task source is CLI
- **THEN** no pre-scan Git RAG job is submitted
