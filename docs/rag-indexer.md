# RAG Indexer

Servicio de indexación de repositorios para RAG (Retrieval-Augmented Generation). Genera embeddings del código fuente y los persiste en SQLite con extensión vectorial (sqlite-vec) almacenado en S3.

## Quick Start

```bash
cd src/rag-indexer

# Modo full index (primera vez, por rama)
TITVO_REPO_URL=https://github.com/org/repo \
TITVO_BRANCH=main \
python -m src.main

# Modo delta index (commits posteriores, por SHA)
TITVO_REPO_URL=https://github.com/org/repo \
TITVO_COMMIT_SHA=abc123 \
python -m src.main
```

## Arquitectura

```mermaid
flowchart TD
    Input[TITVO_REPO_URL + BRANCH/COMMIT_SHA] --> Mode{Determinar modo}
    Mode -->|TITVO_BRANCH| Full[Full Index]
    Mode -->|TITVO_COMMIT_SHA| Delta[Delta Index]

    Full --> Resolve[Resolver HEAD SHA via API]
    Resolve --> GetAll[Obtener todos los archivos vía REST API]

    Delta --> CheckLatest[Leer latest/meta.json de S3]
    CheckLatest --> DownloadDB[Descargar latest/index.db]
    DownloadDB --> Diff[Calcular diff vía API]
    Diff --> GetChanged[Obtener solo archivos cambiados]

    GetAll --> Chunk[LangChain Chunking]
    GetChanged --> Chunk

    Chunk --> Embed[Generar embeddings]
    Embed --> Store[SQLite + sqlite-vec]
    Store --> Upload[Subir a S3: {sha}/ y latest/]
```

## Estructura S3

```
s3://<bucket>/
├── github.com/org/repo/
│   ├── abc123/
│   │   ├── index.db       ← Base de datos SQLite con vectores
│   │   └── meta.json      ← {"commit_sha": "abc123", "indexed_at": "..."}
│   └── latest/
│       ├── index.db       ← Copia del commit más reciente
│       └── meta.json      ← Puntero al último commit indexado
```

## Variables de entorno

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| TITVO_REPO_URL | Sí | URL del repositorio (GitHub o Bitbucket) |
| TITVO_BRANCH | No* | Rama para full index |
| TITVO_COMMIT_SHA | No* | SHA para delta index |
| TITVO_DYNAMO_CONFIGURATION_TABLE_NAME | Sí | Tabla DynamoDB de configuración |
| TITVO_ENCRYPTION_KEY_NAME | Sí | Clave KMS para secretos |
| TITVO_CHUNK_SIZE | No | Tamaño de chunk (default: 1000) |
| TITVO_CHUNK_OVERLAP | No | Overlap de chunks (default: 200) |
| TITVO_LOG_LEVEL | No | Nivel de log (default: INFO) |

*Requiere una de las dos: BRANCH (full) o COMMIT_SHA (delta)

## Configuración DynamoDB

| Parámetro | Descripción |
|-----------|-------------|
| rag_index_bucket | Bucket S3 para los índices |
| embedding_model | Modelo de embeddings (ej: text-embedding-3-small) |
| embedding_provider | Proveedor (openai) |
| embedding_api_key | API key para embeddings (encriptado; en local mismo valor que `ai_api_key` vía `IA_API_KEY`) |
| github_access_token | Token GitHub API |
| bitbucket_api_token | Token Bitbucket API |

## Modos de operación

### Full Index

Usar cuando no existe índice previo para el repositorio.

**Flujo:**
1. Recibe `TITVO_BRANCH`
2. Resuelve HEAD SHA de la rama vía API
3. Obtiene árbol completo de archivos vía REST API
4. Divide archivos en chunks con `RecursiveCharacterTextSplitter`
5. Genera embeddings con LangChain/OpenAI
6. Almacena en SQLite + sqlite-vec
7. Sube a S3 en `{sha}/` y copia a `latest/`

**Ejemplo:**
```bash
TITVO_REPO_URL=https://github.com/KaribuLab/titvo \
TITVO_BRANCH=main \
TITVO_DYNAMO_CONFIGURATION_TABLE_NAME=titvo-config \
TITVO_ENCRYPTION_KEY_NAME=titvo-key \
python -m src.main
```

### Delta Index

Usar para commits subsiguientes cuando ya existe un índice previo.

**Flujo:**
1. Recibe `TITVO_COMMIT_SHA`
2. Lee `latest/meta.json` de S3 para obtener SHA previo
3. Calcula diff entre commits vía API (`/compare` o `/diffstat`)
4. Descarga `latest/index.db` de S3
5. Elimina vectores de archivos modified/deleted
6. Obtiene contenido de archivos added/modified vía API
7. Procesa chunks y embeddings solo para archivos nuevos/cambiados
8. Sube DB actualizada a S3

**Ejemplo:**
```bash
TITVO_REPO_URL=https://github.com/KaribuLab/titvo \
TITVO_COMMIT_SHA=a1b2c3d \
TITVO_DYNAMO_CONFIGURATION_TABLE_NAME=titvo-config \
TITVO_ENCRYPTION_KEY_NAME=titvo-key \
python -m src.main
```

## API REST utilizadas

### GitHub
- `GET /repos/{owner}/{repo}/git/ref/heads/{branch}` - Resolver SHA de rama
- `GET /repos/{owner}/{repo}/git/trees/{sha}?recursive=1` - Árbol de archivos
- `GET /repos/{owner}/{repo}/contents/{path}` - Contenido de archivo
- `GET /repos/{owner}/{repo}/compare/{base}...{head}` - Diff entre commits

### Bitbucket
- `GET /repositories/{workspace}/{slug}/refs/branches/{branch}` - Resolver SHA
- `GET /repositories/{workspace}/{slug}/src/{sha}/` - Árbol de archivos (paginado)
- `GET /repositories/{workspace}/{slug}/src/{sha}/{path}` - Contenido de archivo
- `GET /repositories/{workspace}/{slug}/diffstat/{old}..{new}` - Diff (paginado)

## Filtrado de archivos

Se excluyen automáticamente:
- Directorios: `node_modules/`, `.git/`, `__pycache__/`, `.venv/`, `venv/`, etc.
- Extensiones binarias: `.exe`, `.dll`, `.so`, `.jpg`, `.png`, `.zip`, etc.
- Bases de datos: `.db`, `.sqlite`, `.sqlite3`

## Dependencias

```toml
[dependencies]
httpx = ">=0.28.0"
langchain = ">=0.3.0"
langchain-community = ">=0.3.0"
langchain-openai = ">=0.3.0"
sqlite-vec = ">=0.1.0"
boto3 = ">=1.40.59"
```

## Troubleshooting

### "Unsupported repository provider"

- Solo soporta GitHub (`github.com`) y Bitbucket (`bitbucket.org`)
- Verificar que la URL incluya el host correcto

### "Could not resolve branch"

- Verificar que el token tenga permisos de lectura (`repo` para GitHub)
- Verificar que la rama exista en el remoto
- Verificar formato de URL: `https://github.com/owner/repo`

### "No previous index found" en modo delta

- Fallback automático a full index
- Primera ejecución debe usar `TITVO_BRANCH`

### "Rate limit exceeded"

- Implementado retry con backoff exponencial en adaptadores
- Para repos grandes, la API puede requerir varias páginas (paginación automática)

### Error cargando sqlite-vec

```python
import sqlite3
import sqlite_vec

conn = sqlite3.connect("index.db")
conn.enable_load_extension(True)
sqlite_vec.load(conn)  # Requiere sqlite-vec instalado
conn.enable_load_extension(False)
```

Si falla, verificar:
- `pip install sqlite-vec`
- Python 3.13 compatible
- No requiere dependencias de sistema adicionales en Alpine

### Diff vacío sin cambios

- El sistema detecta automáticamente cuando no hay cambios
- Termina sin modificar el índice y registra log INFO

## Rebuild después de cambios

```bash
# Desde la raíz del monorepo
docker build -f src/rag-indexer/Dockerfile -t titvo-rag-indexer:latest src/rag-indexer
```

## Tests unitarios

```bash
cd src/rag-indexer
.venv/bin/python -m pytest tests/unit/ -v
```

## Integración futura con src/agent

El diseño prepara `IVectorStorePort.search()` para ser consumido por el agente:

```python
# Pseudocódigo de integración futura
vector_store = SqliteVecStoreAdapter(
    db_path=download_latest_db(repo_url),
    embedding_provider=embedding_provider,
    ...
)
results = vector_store.search("SQL injection vulnerability", k=5)
```

El cambio `agent-rag-integration` implementará esta conexión.
