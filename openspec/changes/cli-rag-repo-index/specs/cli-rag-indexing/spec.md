# Spec Delta

## Purpose

Indexación RAG para scans CLI desde snapshot S3 y `scan-manifest.json`, con índice vivo por repositorio bajo `{repo}/cli/latest/`, lock y actualización idempotente por path+sha256 sin clonar Git.

## ADDED Requirements

### Requirement: Origen de archivos es snapshot S3, no Git
Para jobs CLI el indexer SHALL obtener el árbol desde `temp/{batch_id}/snapshot.tar.gz` y el inventario desde `temp/{batch_id}/scan-manifest.json`. SHALL NOT usar SSH ni `git ls-remote`/`fetch` en ese camino.

#### Scenario: Job CLI con batch
- **WHEN** el job indica origen CLI y un `batch_id` con snapshot y manifest válidos
- **THEN** el indexer lee esos objetos S3 y no ejecuta comandos Git remotos

#### Scenario: Snapshot o manifest ausente
- **WHEN** falta el tar o el `scan-manifest.json` del batch
- **THEN** el job falla con error que identifica el objeto faltante

### Requirement: Índice vivo por repositorio bajo cli/latest
El índice CLI SHALL persistirse en el bucket RAG bajo `{repo_slug}/cli/latest/` con al menos `index.db`, copia del manifest aplicado y `meta.json`. SHALL NOT usar `batch_id`, commit SHA o rama como segmento de clave del índice.

#### Scenario: Primer scan de un repo
- **WHEN** no existe `cli/latest/meta.json` para el repo
- **THEN** el indexer crea `cli/latest/` con el índice del inventory completo del manifest

#### Scenario: Clave independiente de Git
- **WHEN** el mismo repo tiene índices bajo `branches/`
- **THEN** el path CLI escribe solo bajo `cli/` y no modifica `branches/`

### Requirement: Lock exclusivo en el prefijo cli
Antes de mutar `cli/latest/` el indexer SHALL adquirir un lock en el mismo bucket/prefijo CLI y liberarlo al terminar (éxito o fallo controlado). Jobs concurrentes del mismo repo SHALL no escribir `cli/latest/` a la vez.

#### Scenario: Lock libre
- **WHEN** no hay lock activo para `{repo}/cli`
- **THEN** el job adquiere el lock, actualiza el índice y lo libera

#### Scenario: Lock ocupado
- **WHEN** otro job sostiene el lock del mismo repo CLI
- **THEN** el job nuevo espera o falla según la política de lock sin corromper `cli/latest/`

### Requirement: Merge idempotente por path y sha256
Tras comparar el inventory nuevo con el manifest previo en `cli/latest/`, el indexer SHALL: omitir paths cuyo sha256 no cambió; reindexar paths nuevos o con sha distinto; eliminar del índice paths ausentes en el nuevo `files[]`. El nuevo `files[]` SHALL ser la verdad absoluta del índice tras el merge.

#### Scenario: Segundo run sin cambios de contenido
- **WHEN** todos los `files[].sha256` coinciden con el manifest previo
- **THEN** no se regeneran embeddings y `cli/latest/` queda coherente con ese inventory

#### Scenario: Archivo modificado
- **WHEN** un path existe en ambos manifests con sha256 distinto
- **THEN** solo ese path se re-embebe y el resto se reutiliza

#### Scenario: Path ausente en el nuevo inventory
- **WHEN** un path estaba indexado y no aparece en el nuevo `files[]`
- **THEN** sus chunks se eliminan del índice

### Requirement: meta.json registra el run sin ser clave
`meta.json` de `cli/latest/` SHALL incluir al menos marca temporal y referencias de auditoría del run (p. ej. `batch_id`, commit/branch del manifest si existen). Esas referencias SHALL NOT formar la clave S3 del índice.

#### Scenario: Auditoría tras merge
- **WHEN** un merge CLI completa con éxito
- **THEN** `meta.json` refleja el run aplicado y el índice sigue en `cli/latest/`
