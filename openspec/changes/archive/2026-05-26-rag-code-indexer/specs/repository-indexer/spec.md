## ADDED Requirements

### Requirement: Detectar proveedor del repositorio
El sistema SHALL detectar automáticamente si el repositorio pertenece a GitHub o Bitbucket a partir de la URL, y usar el cliente REST correspondiente con su access token.

#### Scenario: Detectar GitHub
- **WHEN** la URL contiene el host `github.com`
- **THEN** el sistema SHALL usar `GitHubApiAdapter` con `github_access_token` leído de DynamoDB cifrado

#### Scenario: Detectar Bitbucket
- **WHEN** la URL contiene el host `bitbucket.org`
- **THEN** el sistema SHALL usar `BitbucketApiAdapter` con `bitbucket_api_token` leído de DynamoDB cifrado

#### Scenario: Proveedor no soportado
- **WHEN** la URL no contiene ni `github.com` ni `bitbucket.org`
- **THEN** el sistema SHALL lanzar un error descriptivo y terminar con código de salida no cero

### Requirement: Full index — obtener todos los archivos de una rama
El sistema SHALL obtener la lista completa de archivos de código del HEAD de la rama especificada en `TITVO_BRANCH` via REST API y construir el índice desde cero.

#### Scenario: Resolver HEAD sha de la rama
- **WHEN** se provee `TITVO_BRANCH = "main"` para un repositorio GitHub
- **THEN** el sistema SHALL resolver el commit SHA del HEAD de esa rama via `GET /repos/{owner}/{repo}/git/ref/heads/{branch}` antes de obtener los archivos

#### Scenario: Obtener árbol completo de archivos GitHub
- **WHEN** se dispone del commit SHA del HEAD
- **THEN** el sistema SHALL obtener el árbol recursivo via `GET /repos/{owner}/{repo}/git/trees/{sha}?recursive=1` y descargar el contenido de cada archivo relevante

#### Scenario: Obtener árbol completo de archivos Bitbucket
- **WHEN** se dispone del commit SHA del HEAD en un repositorio Bitbucket
- **THEN** el sistema SHALL paginar `GET /repositories/{ws}/{slug}/src/{sha}/` para obtener todos los archivos relevantes

#### Scenario: Filtrar archivos no relevantes en full index
- **WHEN** el árbol de archivos contiene rutas en `node_modules/`, `.git/`, o archivos con extensiones binarias
- **THEN** el sistema SHALL excluirlos y no descargar su contenido

### Requirement: Delta index — obtener archivos cambiados entre commits
El sistema SHALL obtener via REST API solo los archivos `added`, `modified` y `deleted` entre el commit SHA del último índice y el nuevo commit SHA, cuando se ejecuta en modo delta (`TITVO_COMMIT_SHA`).

#### Scenario: Diff vía GitHub compare API
- **WHEN** se dispone del SHA previo `A` y el nuevo `B` para un repositorio GitHub
- **THEN** el sistema SHALL invocar `GET /repos/{owner}/{repo}/compare/{A}...{B}` y extraer el campo `files[]` con su `status` (`added`, `modified`, `removed`, `renamed`)

#### Scenario: Diff vía Bitbucket diffstat API
- **WHEN** se dispone del SHA previo `A` y el nuevo `B` para un repositorio Bitbucket
- **THEN** el sistema SHALL invocar `GET /repositories/{ws}/{slug}/diffstat/{A}..{B}` paginando hasta obtener todos los archivos cambiados

#### Scenario: Sin cambios entre commits
- **WHEN** el diff entre `A` y `B` no devuelve ningún archivo modificado
- **THEN** el sistema SHALL retornar un `DiffResult` vacío y el proceso SHALL terminar sin modificar el índice

#### Scenario: Archivo renombrado
- **WHEN** el diff incluye un archivo con `status = "renamed"` (GitHub) o equivalente Bitbucket
- **THEN** el sistema SHALL tratar el nombre anterior como `deleted` y el nombre nuevo como `added`
