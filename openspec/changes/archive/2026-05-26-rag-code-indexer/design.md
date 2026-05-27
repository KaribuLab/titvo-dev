## Context

El proyecto Titvo analiza código de repositorios en busca de vulnerabilidades de seguridad. Actualmente, `src/agent` accede a los archivos del repositorio directamente en cada ejecución a través de herramientas MCP, sin ninguna capa de indexación previa. Esto genera consultas costosas y latencia en el análisis.

Este diseño describe cómo implementar la indexación RAG dentro del servicio `src/rag-indexer`. El servicio se ejecuta como tarea ECS a demanda, obtiene archivos del repositorio vía REST API, y produce un índice de embeddings almacenado en S3 listo para ser consultado por `src/agent` en un futuro cambio.

**Stack en `src/rag-indexer`**: Python 3.13, uv, arquitectura hexagonal, boto3, httpx, sqlite-vec.

## Goals / Non-Goals

**Goals:**
- Obtener archivos de repositorios GitHub/Bitbucket vía REST API con access token (mismo patrón que `git-commit-files` Lambda).
- Dos modos de indexado: full (por rama, primera vez) y delta (por commit SHA, incremental).
- Generar embeddings con LangChain y almacenarlos en una DB libSQL embebida (SQLite local).
- Persistir la DB en S3 con estructura por commit SHA y puntero `latest/`.
- Exponer `IVectorStorePort` para consultas futuras desde `src/agent`.

**Non-Goals:**
- Integrar el RAG en `src/agent` (cambio futuro `agent-rag-integration`).
- Soporte para git clone, SSH keys, ni proveedores distintos de GitHub y Bitbucket.
- API de consulta del índice ni webhooks de reindexado.

## Decisions

### 1. Vector store: sqlite-vec + S3 sobre Turso cloud o pgvector

**Decisión**: Usar `sqlite-vec` (extensión vectorial para SQLite) cargada sobre `sqlite3` estándar de Python. La base de datos se serializa y persiste en S3, no en un servicio gestionado.

La extensión se instala como dependencia pip (`pip install sqlite-vec`) y se carga en cada apertura de conexión:
```python
import sqlite3, sqlite_vec
db = sqlite3.connect("index.db")
db.enable_load_extension(True)
sqlite_vec.load(db)
db.enable_load_extension(False)
```

El archivo `.db` resultante es SQLite estándar — portable, sin formato propietario.

**Layout de S3**:
```
s3://<bucket>/
└── github.com/org/repo/
    ├── abc123/
    │   ├── index.db       ← base de datos libSQL
    │   └── meta.json      ← {"commit_sha": "abc123", "indexed_at": "..."}
    └── latest/
        ├── index.db       ← copia del commit más reciente
        └── meta.json      ← {"commit_sha": "abc123", "indexed_at": "..."}
```

**Alternativas descartadas**:
- `Turso cloud` / `libsql`: requiere credenciales externas, plan gestionado, latencia de red en cada operación. Descartado.
- `libsql-experimental-python`: binding experimental del fork de Turso. Descartado por estabilidad frente a `sqlite-vec`.
- `FAISS en memoria`: no persiste entre ejecuciones ECS. Descartado.
- `pgvector`: overhead operacional (RDS/Aurora). Descartado.

**Ventajas del enfoque elegido**:
- Sin servicios externos: solo S3 (ya usado en el proyecto).
- `sqlite-vec` es puro pip, sin dependencias de sistema — funciona en Alpine sin modificar la imagen Docker base.
- El archivo `.db` es SQLite estándar: cualquier consumidor future (`src/agent`) solo necesita `pip install sqlite-vec`.
- Snapshot por commit: historial queryable, rollback trivial.
- Puntero `latest/` para acceso rápido desde el agente.

### 2. Obtención de archivos: REST API sobre git clone

**Decisión**: Usar la REST API de GitHub (PyGithub u Octokit-equivalente via httpx) y Bitbucket (HTTP Basic via httpx) para obtener archivos. Los tokens se leen de DynamoDB cifrado con el mismo patrón que la Lambda `git-commit-files` (`github_access_token`, `bitbucket_api_token`).

**Alternativas descartadas**:
- `gitpython` + clone HTTPS/SSH: requiere SSH key management en ECS, disco para el clon completo, más lento para repos grandes. Descartado.
- MCP `git-commit-files`: el rag-indexer no tiene acceso al MCP gateway y queremos desacoplarlo. Descartado.

### 3. Dos modos de indexado

**Decisión**: El modo se determina por las variables de entorno del ECS task:
- **Full index** (`TITVO_BRANCH`): obtiene todos los archivos del HEAD de la rama, crea la DB desde cero. Usado la primera vez o para reindexar completo.
- **Delta index** (`TITVO_COMMIT_SHA`): descarga `latest/index.db` de S3, obtiene solo los archivos del diff via API de comparación, actualiza la DB. Usado para commits subsiguientes.

Si se pasan ambas variables, `TITVO_COMMIT_SHA` tiene precedencia (delta mode).

**API de comparación por proveedor**:
- GitHub: `GET /repos/{owner}/{repo}/compare/{base}...{head}` → campo `files[]` con `status`.
- Bitbucket: `GET /repositories/{ws}/{slug}/diffstat/{old_sha}..{new_sha}` → paginado.

### 4. Chunking: RecursiveCharacterTextSplitter de LangChain

**Decisión**: Usar `RecursiveCharacterTextSplitter.from_language()` con el `Language` enum de LangChain, inferido por extensión de archivo. `chunk_size` y `chunk_overlap` configurables desde DynamoDB.

### 5. Embeddings: configurable desde DynamoDB

**Decisión**: Proveedor y modelo de embeddings se leen de la tabla de configuración DynamoDB (`embedding_provider`, `embedding_model`). API key desde `get_secret()`. Mismo patrón que `src/agent`.

### 6. Idempotencia: verificación por `meta.json` en S3

**Decisión**: Antes de indexar, se verifica si `s3://<bucket>/<repo>/latest/meta.json` contiene el mismo SHA que el solicitado. Si coincide, se omite el proceso.

## Risks / Trade-offs

- **[Riesgo] Rate limits de REST API** → Mitigación: httpx con retry/backoff exponencial; para repos grandes implementar paginación con throttling.
- **[Riesgo] Tamaño de `index.db` en repos grandes** → Mitigación: filtrar por extensiones de código relevantes; la ECS task necesita suficiente almacenamiento efímero (`/tmp` en ECS tiene 20GB por defecto). `sqlite-vec` no tiene límite de vectores.
- **[Restricción] `sqlite-vec` debe cargarse en cada apertura de conexión** → Cualquier consumidor del `.db` (incluyendo el futuro `src/agent`) necesita `pip install sqlite-vec` y `sqlite_vec.load(conn)`. Documentar como prerequisito en `agent-rag-integration`.
- **[Riesgo] Escritura concurrente en S3** → Mitigación: S3 tiene consistencia fuerte (desde 2020); dos tareas para el mismo repo y commit producirían el mismo resultado (idempotente), el segundo simplemente sobreescribe.
- **[Trade-off] libSQL local vs. servicio vectorial gestionado**: sin hybrid search ni filtros complejos. Aceptable para búsqueda por similitud semántica de código.

## Migration Plan

1. Desplegar infraestructura: ECR → ECS task definition → SSM upsert.
2. Construir imagen Docker con libSQL y extensión vectorial, publicar en ECR.
3. Ejecutar modo full index manualmente sobre un repositorio de prueba.
4. Verificar DB en S3 y ejecutar búsqueda de prueba.
5. **Rollback**: eliminar objetos S3 del repositorio indexado; la tarea ECS es stateless.

## Open Questions

- ¿El bucket S3 para el índice RAG es el mismo que usa `src/agent` para reportes, o uno dedicado? (Recomendación: dedicado.)
- ¿Un bucket por stage (test/prod) o prefijo por stage dentro del mismo bucket?
