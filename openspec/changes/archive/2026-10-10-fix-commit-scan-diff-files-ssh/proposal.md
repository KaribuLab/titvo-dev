## Why

Desde la migración a acceso SSH (commit `8412819` de `git-commit-files`, 2026-08-09), `SshGitRepoClient.getCommitFiles` devuelve `git ls-files` del clon completo e ignora el `commitId`. Como `RepoFactoryService` solo entrega ese cliente, todo scan `scan_mode=commit` analiza el árbol entero: un commit de 1 archivo produjo 1279 archivos y ~393 lotes de expertos. Esto multiplica el costo por scan, el tiempo de ejecución y viola el spec `repository-ssh-access` ("selects files using the existing Git commit-scan behavior").

## What Changes

- `getCommitFiles(commitId)` calcula los archivos tocados por el commit con `git diff-tree` contra su primer padre, filtrando a añadidos, copiados, modificados y renombrados (sin borrados).
- El clon/fetch en modo `commit` trae profundidad suficiente para que el padre exista (`--depth 2` / `fetch --deepen 1`).
- Commit raíz (sin padre): se devuelve el árbol completo de ese commit, con log explícito.
- Merge commit: diff contra el primer padre (`--first-parent`), que es lo que un pipeline de rama espera.
- El `GitRunner` gana un método `diffTreeFiles(cloneDir, sha)`; el `clone`/`fetchCommit` reciben la profundidad como parámetro.
- Log `Found N files.` pasa a incluir el modo y el SHA resuelto para diagnóstico.
- Tests unitarios del cliente SSH con `GitRunner` fake cubriendo commit normal, raíz y merge; modo `full` no cambia.

## Capabilities

### New Capabilities

- Ninguna.

### Modified Capabilities

- `repository-ssh-access`: el requisito "Existing scan contracts are preserved" especifica cómo se seleccionan los archivos en modo `commit` por la vía SSH (diff contra el primer padre, exclusión de borrados, caso raíz).

## Impact

- `src/mcp/git-commit-files/src/git-commit-files/respositories-handler/ssh/ssh-git-repo-client.service.ts`: `getCommitFiles`, `GitRunner`, `prepare`.
- `src/mcp/git-commit-files/src/git-commit-files/respositories-handler/ssh/ssh-git-repo-client.service.spec.ts`: nuevos casos.
- `src/mcp/git-commit-files/src/git-commit-files/git-commit-files.service.ts`: solo el log.
- `docs/architecture.md`: nota sobre selección de archivos en modo `commit`.
- Sin cambios en agente, gateway, API ni layout S3 (`{commitId}/{filePath}` se mantiene).
- Scans `commit` pasan de analizar cientos de archivos a solo los del commit: menos lotes, menos costo, menos tiempo. Los hallazgos en archivos no tocados por el commit dejan de aparecer en scans `commit` (comportamiento previo a 2026-08-09).

## Non-goals

- No reintroducir clientes API de GitHub/Bitbucket.
- No cambiar la selección en modo `full`.
- No incluir archivos borrados ni el contenido del padre en el análisis.
- No añadir opción para scan de rango de commits (`base..head`); si se necesita, será otro change.
