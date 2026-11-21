# Proposal

## Why

Scans CLI suben un snapshot a S3 y no deben clonar por Git/SSH: la llave del workspace Titvo no alcanza repos ajenos, y el pack ya trae el árbol. Hoy el agent bypasea RAG en CLI; hace falta indexar desde ese snapshot con un índice vivo por repositorio, idempotente entre runs de CI.

## What Changes

- CLI sube `scan-manifest.json` sidecar junto a `snapshot.tar.gz` (`focus_files` + inventory `path/sha256/size`).
- Agent dispara indexación CLI (no Git): lee tar + manifest desde `temp/{batch_id}/`.
- Indexer mantiene `{repo}/cli/latest/` (índice + manifest + meta) con lock en el mismo prefijo.
- Merge por path+sha256: igual → skip; distinto/nuevo → embed; ausente en `files[]` → borrar del índice.
- Agent analiza `focus_files`; RAG de fondo usa `cli/latest` (no `branches/…`).
- Se retira el bypass “CLI no indexa” a favor de este flujo snapshot-scoped.

## Non-goals

- Content-addressed storage (CAS) global por hash.
- Unificar índices Git (`branches/`) y CLI.
- Claves de índice por `batch_id`, commit o rama.
- Normalización especial de `repository_url` más allá del slug actual.
- Cambiar el pack working-tree existente (`.titvo-manifest.json` dentro del tar sigue).

## Capabilities

### New Capabilities

- `cli-rag-indexing`: indexación RAG desde snapshot CLI + `scan-manifest.json`, layout `{repo}/cli/latest/`, lock y merge idempotente por sha256.

### Modified Capabilities

- `rag-pre-scan-full-indexing`: reemplazar bypass CLI por pre-scan CLI hacia el indexer snapshot-scoped; timeout RAG también aplica a espera CLI.
- `agent-rag-context`: habilitar RAG de fondo CLI desde `cli/latest`; análisis sigue por snapshot/`focus_files`, no MCP Git.
- `cli-snapshot-analysis`: contrato de upload del sidecar `scan-manifest.json` y consumo de `focus_files` / inventory.

## Impact

- `tools/cli` (upload manifest + scopes).
- API `cli-files` (ya multi-file; registro Dynamo).
- `src/agent` (trigger env CLI, status `cli/latest`, CliRetrievalNode + RagRetrievalNode).
- `src/rag-indexer` (provider S3/tar, merge, lock; sin SSH en path CLI).
