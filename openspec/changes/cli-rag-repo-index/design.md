# Design

## Context

Hoy CLI bypasea RAG; el indexer solo habla SSH Git. El pack ya sube `snapshot.tar.gz` (con `.titvo-manifest.json` interno) y la API cli-files admite varios nombres por `batch_id`. Ver proposal.md — Why.

Constraint: CI sube árboles por run con `batch_id` nuevo; la idempotencia no puede colgarse de ese UUID.

## Goals / Non-Goals

**Goals:**

- Camino CLI: S3 temp → merge → `{repo}/cli/latest/`
- Señal agent→indexer: origen CLI + `batch_id` + `repository_url` (sin clon)
- Agent: focus desde sidecar; RAG fondo desde `cli/latest/`
- Lock en el mismo prefijo CLI

**Non-Goals:**

- CAS global; índices por commit/rama/batch; tocar layout `branches/`
- Reescribir el empaquetado working-tree más allá del sidecar y scopes de focus

## Decisions

### 1. Clave de índice = `{repo_slug}/cli/latest/`

- **Por qué:** corpus CLI es “archivos subidos del repo”, no tip de rama. `batch_id` cambia siempre → reindexaría todo.
- **Alternativas:** `commits/{sha}/cli/` (historial; user rechazó); solo CAS (overkill).

### 2. Merge = diff de `files[]` por path+sha256; ausentes se borran

- **Por qué:** `files[]` = verdad del tar; scopes `staged`/`commit` no deben dejar basura.
- **Alternativa:** solo upsert (acumula paths viejos) — descartada.

### 3. Sidecar `scan-manifest.json` (no solo `.titvo-manifest.json`)

- **Por qué:** agent/indexer leen focus/scope/commit sin abrir tar; contrato explícito versionado.
- **Impacto:** `CliSnapshotRepository` debe tipar keys (tar vs JSON).

### 4. Señal Batch

Env mínimo CLI:

| Variable | Rol |
|----------|-----|
| `TITVO_SOURCE_TYPE=cli` | selecciona provider S3/tar |
| `TITVO_SOURCE_BATCH_ID` | lee `temp/{id}/…` |
| `TITVO_REPO_URL` | slug / prefijo `cli/latest` |
| `TITVO_CLI_FILES_BUCKET` o config ya usada por agent | bucket temp |

Sin `TITVO_COMMIT_SHA` como modo delta Git.

### 5. Lock = objeto en `{repo_slug}/cli/lock.json` (mismo bucket RAG)

- Misma familia que locks de branch Git; alcance solo CLI.
- Política concreta (wait vs fail) en implementación; spec exige exclusión mutua sin corrupción.

### 6. Status port CLI

Extender verificación: existencia de `{repo}/cli/latest/meta.json` (y/o comparación ligera de inventory si se quiere skip de job). Primer slice: siempre disparar job CLI y dejar que el indexer no-op si hashes iguales — más simple y correcto.

### 7. Timeout

Reutilizar `rag_indexing_timeout_seconds` también para espera CLI (quita el escenario “CLI no lee timeout”).

## Risks / Trade-offs

- **[Concurrent PRs mismo repo]** → last-write-wins mitigado por lock; un índice vivo, no por PR.
- **[Temp TTL]** → indexer debe consumir temp en el job y persistir en bucket RAG.
- **[Agent viejo asume todo=tar]** → filtrar por nombre; tests de batch mixto.
- **[Focus con borrados]** → path en focus sin bytes; experts deben tolerar ausencia de content.

## Migration Plan

1. Desplegar indexer con provider CLI (jobs viejos Git intactos).
2. Desplegar agent que tipa objects + trigger CLI + RagRetrieval a `cli/latest`.
3. Desplegar CLI que sube sidecar (batches sin sidecar: fallar claro o degradar sin RAG CLI).
4. Rollback: reponer bypass CLI (trigger=None) — índices `cli/` quedan huérfanos inofensivos.

## Open Questions

- ~~¿Timeout de adquisición del lock CLI (espera vs fail-fast) y TTL del lock stale?~~
  **Resuelto:** wait con timeout default **300s** (`TITVO_CLI_LOCK_WAIT_SECONDS`), poll 5s;
  TTL del lock = `TITVO_LOCK_TTL_MINUTES` (default 360); locks con `expires_at` pasado se
  toman (stale takeover) igual que el path Git.
- ~~¿Skip de submit de job si agent compara manifests en S3 antes, o siempre submit + no-op en indexer?~~
  **Resuelto (decisión 6):** siempre submit; el indexer hace no-op si `files[]` path+sha256 es idéntico.
