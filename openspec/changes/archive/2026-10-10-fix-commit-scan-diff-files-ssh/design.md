## Context

`git-commit-files` es una Lambda NestJS que, por job, clona el repo por SSH a un directorio temporal, lista archivos, los sube a S3 bajo `{commitId}/` (commit) o `full/{jobId}/` (full) y emite el resultado por EventBridge. El clon es shallow (`--depth 1`) y, para un SHA, hace `fetch --depth 1 <sha>` + `checkout`.

`SshGitRepoClient.getCommitFiles(_commitId)` hoy es `return this.getAllFiles(...)`. El `GitRunner` (interfaz interna, inyectable para tests) solo expone `clone`, `fetchCommit`, `checkout`, `revParseHead`, `lsFiles`, `readFile`, `resolveRemoteRef`. No hay primitiva de diff.

Restricciones: env mínimo para `git` (sin herencia de `process.env`), `--` antes de URLs/refs para evitar argument injection, un job = un clon aislado.

## Goals / Non-Goals

**Goals**

- `commit` devuelve exactamente los archivos añadidos/modificados/renombrados/copiados por ese commit.
- Shallow clone sigue siendo shallow: solo una profundidad más.
- Casos borde definidos: commit raíz, merge commit, commit sin cambios de archivos.
- Cubierto por tests con `GitRunner` fake; sin git real en CI unitario.

**Non-Goals**

- Ver proposal.

## Decisions

### D1. `git diff-tree` de dos árboles: primer padre vs commit

`getCommitFiles(sha)` ejecuta, tras confirmar que `<sha>^` existe (D3):

```
git diff-tree -r -z --name-only --diff-filter=ACMR <sha>^ <sha>
```

- Forma de dos árboles: `<sha>^` es siempre el primer padre, también en merges, sin depender de `-m`/`--first-parent`.
- `--diff-filter=ACMR`: excluye `D` (borrados; no hay contenido que subir) y `T`/`U`/`X`.
- `--name-only -r`: rutas relativas al root, recursivo. Para renombres devuelve la ruta destino.
- `-z` para separar por NUL y soportar rutas con espacios o saltos de línea; se parte por `\0`.
- Los SHA se validan como 40 hex en el cliente antes de llegar al runner, así que no pueden leerse como flags.

Verificado con git real sobre un repo temporal clonado con `--depth 2` por `file://`: commit normal devuelve A/M y omite D; merge devuelve solo lo que difiere del primer padre; raíz cae a `ls-tree`.

*Alternativa descartada*: `git diff-tree -m --first-parent <sha>` (un solo commit). Equivalente, pero el soporte de `--first-parent` en `diff-tree` varía por versión de git.

*Alternativa descartada*: `git show --name-only --format=`. Imprime cabecera en merges y requiere más parseo.

### D2. Profundidad 2 solo en modo commit

`prepare(ref)` ya distingue rama (clone `--branch`) de SHA (clone HEAD + fetch SHA). Se añade `depth` al `GitRunner`:

- `clone(cloneUrl, targetDir, ref, depth)` y `fetchCommit(cloneDir, cloneUrl, sha, depth)`.
- `prepare(ref, { depth })`: `SshGitRepoClient` recibe la profundidad desde `GitCommitFilesService` según el modo: `commit` → 2, `full` → 1.

Con `--depth 2` el padre del commit está en el clon shallow y `diff-tree` funciona. Si el commit es raíz, el clon solo tiene 1 commit y `git rev-parse <sha>^` falla: ese es el detector del caso raíz.

*Alternativa descartada*: `fetch --deepen 1` después del clon. Un round-trip extra por job; `--depth 2` cuesta lo mismo en un solo comando.

*Alternativa descartada*: calcular diff en el agente a partir de los paths del MCP. El agente no tiene el repo; el MCP es el único con git.

### D3. Commit raíz devuelve el árbol completo

Si `rev-parse <sha>^` falla (shallow grafted o raíz real), se usa `git ls-tree -r --name-only -z <sha>` y se loguea `commit <sha> has no parent in clone; selecting full tree (N files)`. Con `--depth 2` un commit no raíz siempre tiene padre, así que el fallback solo dispara en raíces reales. Es el mismo resultado que daría cualquier diff contra el árbol vacío.

### D4. Commit sin archivos elegibles

Un commit que solo borra archivos devuelve `[]`. `GitCommitFilesService` ya reporta `filesPaths = []` con `success = true`; el agente responde `mcp_error = "No files in commit"` y marca `FAILED`. Se mantiene: no es responsabilidad de este change cambiar la semántica del agente. Se documenta.

### D5. Interfaz `GitRunner` y tests

Nuevo método `diffTreeFiles(cloneDir, sha): string[]` y `lsTreeFiles(cloneDir, sha): string[]`, `hasParent(cloneDir, sha): boolean`. Los tests del cliente usan el runner fake existente ampliado; se afirma que en modo `commit` no se llama `lsFiles` y que `clone` recibe `depth=2`. El test de `GitCommitFilesService` ya cubre `commit` con un `RepoClient` mock; se añade aserción sobre la profundidad pasada a `prepare`.

## Risks / Trade-offs

- [Pipelines que dependían del "commit scan" para ver hallazgos en archivos no tocados] → Era un bug, no una feature; `scan_mode=full` existe para eso. Se avisa en el changelog del submódulo.
- [Renombre con modificación: solo se sube la ruta nueva] → Correcto para el análisis; el contenido antiguo no existe en el commit.
- [Rutas con caracteres especiales] → `-z` y split por NUL; test con un path con espacio.
- [Repos donde el primer padre no es "la rama" (merges invertidos)] → Caso raro; `--first-parent` es la convención de los proveedores SCM para "Files changed" de un merge.

## Migration Plan

Despliegue normal de la Lambda `git-commit-files`. Sin cambio de contrato con gateway ni agente. Rollback: versión anterior de la Lambda.

## Open Questions

- Ninguna bloqueante. Si en el futuro se quiere `base..head` para PRs, se extiende `diffTreeFiles` con dos refs.
