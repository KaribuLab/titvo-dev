# Verificación

## Pruebas y lint

- `git-commit-files`: `npm ci`, `npm test -- --runInBand`: 4 suites, 37 tests aprobados. `npx eslint 'src/**/*.{ts,js}'`: sin errores.
- `rag-indexer`: `uv run pytest tests/unit/test_repository_provider_factory.py tests/unit/test_ssh_git_repository_adapter.py -q`: 35 aprobados. `uv run ruff check .`: sin errores.
- Ambas matrices prueban HTTPS histórico, SCP histórico y SCP nuevo, secreto Bitbucket, rechazo de dominios con sufijos engañosos y regresión GitHub. Las suites existentes cubren credencial ausente, aislamiento y opciones SSH estrictas de RAG.
- El parser RAG conserva el hostname de entrada y deriva únicamente `clone_url`. `src/main.py` continúa pasando `repo_url` original tanto a la factory como al caso de uso (`repository_url=repo_url`); los identificadores persistidos no se reescriben.
- `git diff --check` pasa en el workspace y ambos submódulos.

## Confianza y empaquetado

- `https://bitbucket.org/site/ssh` publica las tres llaves del nuevo hostname. Sus fingerprints coinciden con la documentación oficial citada en el diseño.
- El test del archivo de confianza usa `ssh-keygen` y contrasta exactamente los tres fingerprints oficiales.
- `docker build -t titvo-rag-indexer:ssh-host-check .`: exitoso.
- `docker run --rm titvo-rag-indexer:ssh-host-check ssh-keygen -F ssh.bitbucket.org -f /app/rag_indexer/infra/adapters/known_hosts`: encuentra las tres llaves empaquetadas.
- `build/lib` está rastreado, pero el build desplegable (`Dockerfile` y workflow) copia `src` a `/app`; no genera ni utiliza `build/lib`. No hay configuración de wheel/setup para regenerar ese árbol histórico, por lo que no aplica regenerarlo en esta migración. La imagen construida verifica el artefacto efectivo.

## Smoke test autenticado

No ejecutado. En la sesión no están definidos `TITVO_REPO_URL` ni
`BITBUCKET_SSH_PRIVATE_KEY_BASE64`; tampoco existe `~/.ssh/titvo_bitbucket`,
la llave de prueba documentada en el workspace. No se ha verificado acceso a un
repositorio Bitbucket ni ejecución full/delta contra servicios reales.

Para completar esta verificación operacional se necesita un repositorio/branch
de prueba, la credencial Bitbucket configurada y el entorno de indexación.
La construcción de imagen y los tests anteriores no equivalen a esa prueba.
