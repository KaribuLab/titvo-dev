## 1. Contrato y selección del proveedor

- [x] 1.1 Extender `IRepositoryProvider` con cierre idempotente y ajustar los mocks del caso de uso al nuevo contrato.
- [x] 1.2 Implementar parsing estricto de URLs HTTPS y SSH, normalización al remoto SSH y selección exacta de GitHub o Bitbucket.
- [x] 1.3 Cambiar la factory para desencriptar solo `github_ssh_private_key` o `bitbucket_ssh_private_key` según el host y fallar explícitamente si falta.
- [x] 1.4 Agregar unit tests para formatos de URL válidos, hosts ambiguos/no soportados, selección de llave y parámetro ausente.

## 2. Ejecución Git SSH segura

- [x] 2.1 Implementar el runner de subprocess con `shell=False`, argumentos estructurados, entorno mínimo, timeout y errores sanitizados.
- [x] 2.2 Implementar creación de llave `0600`, repositorio Git temporal lazy y cierre repetible que elimine ambos recursos.
- [x] 2.3 Incorporar `known_hosts` versionado con claves oficiales de GitHub y Bitbucket y configurar verificación estricta, `BatchMode=yes` e `IdentitiesOnly=yes`.
- [x] 2.4 Agregar unit tests del runner, permisos de llave, entorno SSH, rechazo de host key y limpieza en éxito/error.

## 3. Adaptador de fuentes Git

- [x] 3.1 Implementar resolución exacta de `refs/heads/<branch>` mediante `git ls-remote` por SSH.
- [x] 3.2 Implementar fetch shallow reutilizable de commits y lectura de blobs con `git ls-tree`/`git cat-file`, sin checkout ni seguimiento de symlinks.
- [x] 3.3 Centralizar exclusiones existentes y omitir por archivo blobs no UTF-8, gitlinks y rutas excluidas.
- [x] 3.4 Implementar diff NUL-delimited con detección de renames y mapeo a `DiffResult` usando los SHA previo y objetivo.
- [x] 3.5 Agregar unit tests de resolución, lectura, exclusiones, caracteres especiales, no UTF-8, symlinks, submódulos, diff, rename y reutilización del repositorio.

## 4. Integración del servicio

- [x] 4.1 Conectar el adaptador SSH en `main.py` y garantizar su cierre con `try/finally` en resultados normales, idempotentes y excepcionales.
- [x] 4.2 Eliminar `GitHubApiAdapter`, `BitbucketApiAdapter`, sus tests, toda lectura de `github_access_token`/`bitbucket_api_token` y cualquier ruta de fallback REST en `rag-indexer`.
- [x] 4.3 Actualizar las pruebas de composición y del caso de uso para verificar full, delta, idempotencia y preservación del error original durante cleanup.
- [x] 4.4 Sincronizar los cambios de `src` con el espejo versionado `build/lib` y comprobar que no conserva adaptadores o tokens REST obsoletos.

## 5. Runtime y dependencias

- [x] 5.1 Actualizar el Dockerfile para instalar Git y OpenSSH en la imagen final sin conservar cachés del package manager.
- [x] 5.2 Eliminar el uso directo de `httpx` del proyecto, regenerar `uv.lock` y verificar que el entorno frozen se instala correctamente.
- [x] 5.3 Construir la imagen y confirmar disponibilidad de `git`, `ssh` y `known_hosts`.

## 6. Validación operativa

- [x] 6.1 Ejecutar la suite unitaria completa y Ruff para `src/rag-indexer`.
- [x] 6.2 Ejecutar una integración Git local real que cubra full, delta, dos SHA, renames y limpieza sin usar credenciales externas.

## 7. Documentation

- [x] 7.1 Actualizar `docs/rag-indexer.md` con arquitectura SSH, parámetros, comandos Git, seguridad, troubleshooting y eliminación de referencias REST/rate-limit.
- [x] 7.2 Actualizar `src/rag-indexer/README.md` con requisitos de llaves, URLs admitidas, herramientas del runtime y ejecución local mediante SSH.
