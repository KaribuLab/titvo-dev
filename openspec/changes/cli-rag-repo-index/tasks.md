# Tasks

## 1. CLI: scan-manifest sidecar

- [x] 1.1 Generar `scan-manifest.json` (version 1, scope commit|staged|full, commit, branch, focus_files, files[]) al planear el scan y verificar con unit tests de semántica focus por scope
- [x] 1.2 Subir sidecar + `snapshot.tar.gz` vía `/cli-files` en el mismo `batch_id` y verificar que el cliente pide ambos `name` y hace PUT de ambos
- [x] 1.3 Documentar el contrato en el módulo CLI (comentario o doc corta) y verificar que un `tli scan` de prueba deja ambos objetos bajo `temp/{batch}/`

## 2. Agent: recuperación y foco

- [x] 2.1 Tipar objetos del batch en `CliSnapshotRepository` (tar vs `scan-manifest.json`) y verificar test de batch mixto sin abrir JSON como tar
- [x] 2.2 Aplicar `focus_files` (vacío = todos los analizables) en recuperación/nodo CLI y verificar unit tests de focus + path borrado sin content
- [x] 2.3 Cablear prompt CLI para distinguir snapshot/focus vs índice `cli/latest/` y verificar test o snapshot de prompt

## 3. Agent: trigger y status CLI

- [x] 3.1 Extender `RagIndexerBatchTrigger` con env `TITVO_SOURCE_TYPE=cli`, `TITVO_SOURCE_BATCH_ID`, `TITVO_REPO_URL` (sin modo Git) y verificar unit test del environment CLI
- [x] 3.2 En `main` / `AnalyseCodeUseCase`, habilitar trigger+status+timeout RAG para CLI hacia índice `cli/latest/` (quitar bypass) y verificar tests que CLI dispara job y espera con timeout de tabla
- [x] 3.3 Adaptar status/retrieval RAG para prefijo `{repo}/cli/latest/` en tasks CLI y verificar head/read de meta/index en tests

## 4. Indexer: provider S3 + merge cli/latest

- [x] 4.1 Añadir provider/adaptador que lea `temp/{batch}/snapshot.tar.gz` + `scan-manifest.json` cuando `TITVO_SOURCE_TYPE=cli` y verificar que no ejecuta Git en tests unitarios
- [x] 4.2 Implementar layout `{repo}/cli/latest/` (index.db, manifest, meta) + `cli/lock.json` (wait con timeout o fail-fast documentado) y verificar acquire/release en tests
- [x] 4.3 Implementar merge path+sha256 (skip / reembed / drop ausentes) y verificar tests: no-op mismo inventory, un file cambiado, path eliminado
- [x] 4.4 Integrar `main`/use case CLI (siempre submit → merge no-op si igual) y verificar test de integración local o unit del execute CLI

## 5. Integración

- [x] 5.1 Flujo local/LocalStack: CLI sube dual → agent → job indexer → `cli/latest/` → análisis con focus + RAG fondo; verificar que no hay `ls-remote` en logs del job CLI
  - Cubierto por unit tests: `test_cli_snapshot_repository_adapter` (métodos Git levantan; sin `ls-remote`), `test_main_cli_uses_cli_provider_and_execute_cli` (`create_repository_provider` no se llama). E2E completo con LocalStack (CLI dual upload → agent → Batch → `cli/latest/` → análisis) queda como follow-up manual.
- [x] 5.2 Segundo scan mismo repo sin cambios de hash: verificar que no regenera embeddings (skip) y el análisis sigue OK
  - Cubierto por `test_identical_inventory_is_noop` y `test_execute_cli_noop_when_inventory_identical` (mismo inventory → 0 chunks, sin `get_files_for_paths` ni upload). E2E segundo scan en LocalStack: follow-up manual.

## 6. Documentation

- [x] 6.1 Actualizar `docs/rag-indexer.md` con path CLI, layout `cli/latest/`, lock, merge y env vars; verificar que las secciones nuevas coinciden con el design
- [x] 6.2 Actualizar `tools/cli/README.md` (o doc de contrato) con `scan-manifest.json` y scopes; verificar ejemplos de JSON del proposal

## Workflow follow-up

- Archive el change tras review/implementación (`openspec archive`).
- ~~Resolver en implementación: TTL/wait del lock CLI (Open Question del design).~~ Resuelto: wait 300s + TTL `TITVO_LOCK_TTL_MINUTES` (documentado en design y `docs/rag-indexer.md`).
- E2E LocalStack completo (5.1/5.2 end-to-end) queda como follow-up manual.
