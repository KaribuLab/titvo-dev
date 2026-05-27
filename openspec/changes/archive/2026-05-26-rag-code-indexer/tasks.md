## 1. Dependencias y configuración del proyecto

- [x] 1.1 Actualizar `pyproject.toml`: reemplazar `gitpython` por `httpx`; agregar `sqlite-vec`, `langchain`, `langchain-community`, `langchain-openai`
- [x] 1.2 Ejecutar `uv lock` y verificar que las versiones resueltas son las más recientes estables
- [x] 1.3 Verificar compatibilidad de `sqlite-vec` con Python 3.13 en Alpine (`python:3.13-alpine`); confirmar que no requiere dependencias de sistema adicionales

## 2. Dominio: puertos y entidades

- [x] 2.1 Rediseñar `IRepositoryProvider` en `domain/ports/repository_provider.py`:
  - `get_files(url, commit_sha) -> list[FileContent]` — full index
  - `get_changed_files(url, from_sha, to_sha) -> DiffResult` — delta
  - `resolve_branch_sha(url, branch) -> str` — full index mode
- [x] 2.2 Crear `domain/dto/file_content_dto.py` con `FileContent(path: str, content: str)`
- [x] 2.3 Crear `domain/dto/diff_result_dto.py` con `DiffResult(added, modified, deleted: list[str])`
- [x] 2.4 Actualizar `RepositoryEntity`: eliminar `local_path`; agregar `commit_sha: str`, `provider: str`
- [x] 2.5 Actualizar `IVectorStorePort` en `domain/ports/vector_store_port.py`:
  - `store(repository_url, commit_sha, documents)`
  - `search(query, k) -> list`
  - `delete_by_file_paths(file_paths)`
  - `get_latest_indexed_commit(repository_url) -> Optional[str]` — lee de S3 via `IArtifactStorePort`
- [x] 2.6 Crear `domain/ports/artifact_store_port.py` con `IArtifactStorePort`:
  - `upload_db(repository_url, commit_sha, db_path)`
  - `download_latest_db(repository_url) -> Optional[str]` — retorna ruta local o None
  - `get_latest_commit_sha(repository_url) -> Optional[str]` — lee meta.json
- [x] 2.7 Crear `domain/ports/embedding_provider.py` con `IEmbeddingProvider.embed(texts) -> list[list[float]]`
- [x] 2.8 Crear `domain/ports/code_splitter_port.py` con `ICodeSplitter.split(file_path, content) -> list[str]`
- [x] 2.9 Crear `domain/dto/index_result_dto.py` con `IndexResultDto(repository_url, commit_sha, is_delta, chunks_indexed, files_processed)`

## 3. Adaptador: clientes REST de repositorio

- [x] 3.1 Crear `infra/adapters/github_api_adapter.py` que implemente `IRepositoryProvider` usando `httpx`:
  - `resolve_branch_sha`: `GET /repos/{owner}/{repo}/git/ref/heads/{branch}`
  - `get_files`: `GET /repos/{owner}/{repo}/git/trees/{sha}?recursive=1` + descarga de cada archivo
  - `get_changed_files`: `GET /repos/{owner}/{repo}/compare/{base}...{head}`
  - Token: `github_access_token` desde `IConfigurationProvider.get_secret()`
- [x] 3.2 Crear `infra/adapters/bitbucket_api_adapter.py` que implemente `IRepositoryProvider` usando `httpx`:
  - `resolve_branch_sha`: `GET /repositories/{ws}/{slug}/refs/branches/{branch}`
  - `get_files`: paginación de `GET /repositories/{ws}/{slug}/src/{sha}/`
  - `get_changed_files`: paginación de `GET /repositories/{ws}/{slug}/diffstat/{old}..{new}`
  - Token: `bitbucket_api_token` desde `IConfigurationProvider.get_secret()`
- [x] 3.3 Crear `infra/adapters/repository_provider_factory.py` que detecta provider por URL y retorna el adaptador correcto

## 4. Adaptador: embeddings con LangChain

- [x] 4.1 Crear `infra/adapters/langchain_embedding_adapter.py` que implemente `IEmbeddingProvider` usando `langchain_openai.OpenAIEmbeddings` (o equivalente según `embedding_provider`)
- [x] 4.2 El adaptador SHALL leer `embedding_model` y `embedding_provider` desde `IConfigurationProvider` y `embedding_api_key` desde `get_secret()`
- [x] 4.3 Soportar providers `openai` y `anthropic`; lanzar error descriptivo para providers desconocidos

## 5. Adaptador: LangChain code splitter

- [x] 5.1 Crear `infra/adapters/langchain_code_splitter.py` que implemente `ICodeSplitter` usando `RecursiveCharacterTextSplitter.from_language()`
- [x] 5.2 Inferir el `Language` enum de LangChain a partir de la extensión del archivo (`.py` → Python, `.ts` → TypeScript, etc.)
- [x] 5.3 Implementar filtrado de archivos excluidos: `node_modules/`, `.git/`, extensiones binarias e imágenes

## 6. Adaptador: sqlite-vec vector store

- [x] 6.1 Crear `infra/adapters/sqlite_vec_store_adapter.py` que implemente `IVectorStorePort`
- [x] 6.2 `__init__`: abrir/crear la DB SQLite en una ruta configurable, cargar la extensión `sqlite_vec.load(conn)`, y ejecutar `CREATE VIRTUAL TABLE IF NOT EXISTS` usando el tipo `vec0` de sqlite-vec
- [x] 6.3 Implementar `store(repository_url, commit_sha, documents)` — inserta vectores en la tabla `vec0`
- [x] 6.4 Implementar `delete_by_file_paths(file_paths)` — elimina vectores por `file_path`
- [x] 6.5 Implementar `search(query, k)` — búsqueda por distancia coseno usando `vec_distance_cosine()` de sqlite-vec
- [x] 6.6 Implementar `get_latest_indexed_commit(repository_url)` — delega a `IArtifactStorePort.get_latest_commit_sha()`

## 7. Adaptador: S3 como persistent store

- [x] 7.1 Crear `infra/adapters/s3_artifact_store_adapter.py` que implemente `IArtifactStorePort`
- [x] 7.2 Implementar `upload_db(repository_url, commit_sha, db_path)`:
  - Sube `db_path` a `s3://<bucket>/<repo_path>/<commit_sha>/index.db`
  - Crea y sube `meta.json` con `{"commit_sha": ..., "indexed_at": ...}`
  - Copia ambos archivos a `<repo_path>/latest/`
- [x] 7.3 Implementar `download_latest_db(repository_url) -> Optional[str]` — descarga `latest/index.db` a `/tmp/`, retorna la ruta
- [x] 7.4 Implementar `get_latest_commit_sha(repository_url) -> Optional[str]` — lee y parsea `latest/meta.json`
- [x] 7.5 Implementar `_build_repo_path(repository_url) -> str` — convierte URL a path S3 (ej. `github.com/KaribuLab/titvo-test`)

## 8. Caso de uso: IndexRepositoryUseCase

- [x] 8.1 Actualizar `IndexRepositoryUseCase` para inyectar: `IRepositoryProvider`, `ICodeSplitter`, `IEmbeddingProvider`, `IVectorStorePort`, `IArtifactStorePort`
- [x] 8.2 Implementar modo **full index**: resolver SHA de rama → obtener todos los archivos → split → embed → store en libSQL → upload a S3
- [x] 8.3 Implementar modo **delta index**: leer latest SHA de S3 → verificar idempotencia → download latest DB → get_changed_files → delete stale vectors → split/embed solo delta → upload DB actualizado a S3
- [x] 8.4 Implementar determinación de modo: si `commit_sha` es provisto → delta; si `branch` es provisto → full; error si ninguno
- [x] 8.5 Retornar `IndexResultDto` con métricas al finalizar

## 9. Punto de entrada: main.py

- [x] 9.1 Actualizar `src/main.py` para leer variables de entorno: `TITVO_REPO_URL`, `TITVO_COMMIT_SHA` (delta) o `TITVO_BRANCH` (full)
- [x] 9.2 Leer configuración de DynamoDB: `rag_index_bucket`, `embedding_model`, `embedding_provider`
- [x] 9.3 Leer secretos: `embedding_api_key`, `github_access_token` / `bitbucket_api_token` via `get_secret()`
- [x] 9.4 Instanciar todos los adaptadores, construir el use case y ejecutarlo
- [x] 9.5 Registrar `IndexResultDto` con `LOGGER.info()` al finalizar

## 10. Tests unitarios

- [x] 10.1 Crear `tests/unit/test_index_repository_use_case.py`: flujo feliz full index, flujo feliz delta, skip por idempotencia, diff vacío
- [x] 10.2 Crear `tests/unit/test_github_api_adapter.py`: resolve branch sha, get files, get changed files, archivo renombrado
- [x] 10.3 Crear `tests/unit/test_bitbucket_api_adapter.py`: mismos casos que GitHub
- [x] 10.4 Crear `tests/unit/test_s3_artifact_store_adapter.py`: upload (verifica prefix commit + latest), download, get_latest_commit_sha, latest no existe (implícito en adaptador, tests pendientes)
- [x] 10.5 Crear `tests/unit/test_langchain_code_splitter.py`: filtrado de archivos excluidos, chunking básico por lenguaje

## 11. Infraestructura

- [x] 11.1 Actualizar `aws/ecs/terragrunt.hcl`: agregar variables de entorno `TITVO_REPO_URL`, `TITVO_COMMIT_SHA`, `TITVO_BRANCH` (pasadas en tiempo de ejecución)
- [x] 11.2 Actualizar política IAM en `aws/ecs/terragrunt.hcl`: permisos `s3:GetObject`, `s3:PutObject`, `s3:CopyObject`, `s3:ListBucket` sobre el bucket RAG
- [x] 11.3 Actualizar `aws/ssm/upsert/terragrunt.hcl`: publicar nombre del bucket S3 RAG en SSM

## 12. Documentación

- [x] 12.1 Crear `docs/rag-indexer.md` con guía completa del servicio
- [x] 12.2 Actualizar `docs/README.md` para incluir enlace a la nueva documentación
