## MODIFIED Requirements

### Requirement: Recuperación íntegra
The agent SHALL retrieve all registered batch packages and validate paths, limits, duplicate paths and optional manifest hashes before analysis. After validation it SHALL exclude files containing NUL bytes or invalid UTF-8, logging each path and reason without file contents. Excluded paths SHALL remain subject to duplicate and integrity checks. Retrieval SHALL fail clearly if no analyzable files remain across the batch.

#### Scenario: Paquete corrupto
- **WHEN** a manifest file is missing or differs
- **THEN** retrieval fails without analyzing a partial snapshot

#### Scenario: Snapshot mixto
- **WHEN** valid packages contain UTF-8 source alongside binary or non-UTF-8 files
- **THEN** only analyzable text is returned unchanged and exclusions are logged

#### Scenario: Paquete binario junto a código
- **WHEN** one package contains only excluded files and another contains valid text
- **THEN** retrieval succeeds with the valid text

#### Scenario: Batch sin texto
- **WHEN** all files in the batch are excluded
- **THEN** retrieval fails explicitly because no analyzable UTF-8 text remains

#### Scenario: Integridad de archivos excluidos
- **WHEN** an excluded file has an invalid hash or duplicates a path across packages
- **THEN** retrieval fails without analyzing a partial snapshot
