## ADDED Requirements

### Requirement: Sidecar scan-manifest.json en el batch
Tras un scan AWS exitoso de empaquetado, la CLI SHALL solicitar URLs prefirmadas y subir `snapshot.tar.gz` y `scan-manifest.json` bajo `temp/{batch_id}/`. El sidecar SHALL NO ir dentro del tar ni listarse como archivo de código en `original_files` / inventory de análisis.

#### Scenario: Upload dual
- **WHEN** la CLI inicia un scan AWS con batch_id
- **THEN** el batch en S3 contiene `snapshot.tar.gz` y `scan-manifest.json` como objetos hermanos

### Requirement: Contrato de scan-manifest version 1
`scan-manifest.json` SHALL usar `version: 1` y campos `scope` (`commit`|`staged`|`full`), `commit`, `branch`, `focus_files` (paths, orden lexicográfico) y `files` (objetos `path`, `sha256`, `size` ordenados por path) que inventarían el contenido del tar.

#### Scenario: Semántica focus por scope
- **WHEN** `scope` es `commit` o `staged`
- **THEN** `focus_files` lista el foco del diff correspondiente; paths borrados PUEDEN estar en focus y no en `files`
- **WHEN** `scope` es `full`
- **THEN** `focus_files` es `[]`

#### Scenario: Inventory alineado al tar
- **WHEN** el manifest lista un path en `files`
- **THEN** ese path existe dentro de `snapshot.tar.gz` con el mismo sha256 y size

## MODIFIED Requirements

### Requirement: Recuperación íntegra
The agent SHALL retrieve registered batch objects, treat `*.tar.gz` / snapshot packages as archives and `scan-manifest.json` as JSON metadata (not as a tar). It SHALL validate archive paths, limits, duplicate paths and optional in-tar manifest hashes before analysis. After validation it SHALL exclude files containing NUL bytes or invalid UTF-8, logging each path and reason without file contents. Excluded paths SHALL remain subject to duplicate and integrity checks. Retrieval SHALL fail clearly if no analyzable files remain across the batch. When `scan-manifest.json` is present, the agent SHALL use its `focus_files` / inventory for analysis focus as specified in agent-rag-context.

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

#### Scenario: Sidecar JSON no se abre como tar
- **WHEN** el batch registra `scan-manifest.json` junto al snapshot
- **THEN** el agent parsea el JSON como metadatos y no intenta descomprimirlo como tar.gz
