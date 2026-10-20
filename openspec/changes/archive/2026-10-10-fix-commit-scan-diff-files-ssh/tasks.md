## 1. GitRunner

- [x] 1.1 Ampliar la interfaz `GitRunner` en `ssh-git-repo-client.service.ts` con `diffTreeFiles(cloneDir, sha): string[]`, `lsTreeFiles(cloneDir, sha): string[]`, `hasParent(cloneDir, sha): boolean`, y parámetro `depth` en `clone` y `fetchCommit`.
- [x] 1.2 Implementar en `createDefaultGitRunner`: `diff-tree --no-commit-id --name-only -r -z -m --first-parent --diff-filter=ACMR -- <sha>`, `ls-tree -r --name-only -z <sha>`, `rev-parse --verify <sha>^` para `hasParent`; split por `\0`; mantener `--` y env mínimo.
- [x] 1.3 `clone`/`fetchCommit` usan `--depth <depth>` en lugar de `1` fijo.

## 2. SshGitRepoClient

- [x] 2.1 `prepare(ref, options?: { depth?: number })` con default 1; pasar `depth` a `clone` y `fetchCommit`.
- [x] 2.2 `getCommitFiles(commitId)`: usar `this.resolvedSha ?? commitId`; si `hasParent` → `diffTreeFiles`; si no → `lsTreeFiles` + log `commit <sha> has no parent in clone; selecting full tree (N files)`. Nunca llamar `lsFiles` en este método.
- [x] 2.3 Ampliar la interfaz `CloneableRepoClient.prepare` en `repo.client.ts` con el parámetro de opciones.

## 3. GitCommitFilesService

- [x] 3.1 Llamar `prepare(data.commitId, { depth: 2 })` en modo `commit`; `prepare(ref, { depth: 1 })` en modo `full`.
- [x] 3.2 Log `Found N files.` → `Found N files (mode=<scanMode>, ref=<scanRef>).`

## 4. Tests

- [x] 4.1 Ampliar `createMockGitRunner` en `ssh-git-repo-client.service.spec.ts` con `diffTreeFiles`, `lsTreeFiles`, `hasParent` y registro de `depth` en `clone`/`fetchCommit`.
- [x] 4.2 Test: commit normal → `getCommitFiles` devuelve solo el diff y no llama `lsFiles`; `clone` recibe `depth=2`.
- [x] 4.3 Test: commit raíz (`hasParent=false`) → devuelve `lsTreeFiles` y loguea el fallback.
- [x] 4.4 Test: path con espacio en el diff se preserva íntegro.
- [x] 4.5 Test: `getAllFiles` (modo full) sigue usando `lsFiles` con `depth=1`.
- [x] 4.6 `git-commit-files.service.spec.ts`: modo `commit` llama `prepare` con `depth: 2`; modo `full` con `depth: 1`.

## 5. Verificación y docs

- [x] 5.1 `npm test` y `npm run lint` en `src/mcp/git-commit-files` en verde.
- [ ] 5.2 Prueba manual en LocalStack: scan `commit` de un commit con 1 archivo → `filesPaths` de longitud 1 y el agente loguea `[MCP Node] Retrieved 1 file paths`.
- [x] 5.3 Actualizar `docs/architecture.md` (sección MCP commit-files): selección en `commit` = diff contra primer padre, borrados excluidos, raíz = árbol completo.
