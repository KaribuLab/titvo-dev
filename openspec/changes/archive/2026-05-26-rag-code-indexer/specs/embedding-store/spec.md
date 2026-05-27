## ADDED Requirements

### Requirement: Generar embeddings de chunks de código
El sistema SHALL dividir los archivos de código fuente en chunks usando `RecursiveCharacterTextSplitter` de LangChain con soporte para múltiples lenguajes, y generar embeddings para cada chunk usando el proveedor configurado en DynamoDB.

#### Scenario: Chunking exitoso de archivo Python
- **WHEN** se procesa un archivo `.py` de 500 líneas
- **THEN** el sistema SHALL producir N chunks con `chunk_size` y `chunk_overlap` configurados, donde cada chunk contiene código Python sintácticamente coherente

#### Scenario: Modelo de embeddings leído desde configuración
- **WHEN** la tabla DynamoDB tiene `embedding_model` = `"text-embedding-3-small"` y `embedding_provider` = `"openai"`
- **THEN** el sistema SHALL usar ese modelo para generar los embeddings

#### Scenario: Filtrar archivos no relevantes
- **WHEN** el repositorio contiene directorios `node_modules/`, `.git/`, o archivos binarios
- **THEN** el sistema SHALL excluirlos del proceso de chunking y embedding

### Requirement: Persistir embeddings en libSQL embebido (SQLite local)
El sistema SHALL almacenar los embeddings generados en una base de datos libSQL creada localmente en el sistema de archivos del contenedor ECS. Cada registro SHALL incluir el chunk de texto, el vector de embedding, la ruta del archivo de origen, el SHA del commit y la URL del repositorio.

#### Scenario: Almacenamiento exitoso de embeddings
- **WHEN** se generan embeddings para 100 chunks de un repositorio
- **THEN** el sistema SHALL insertar los 100 registros en la tabla de vectores de la DB libSQL local

#### Scenario: Idempotencia por SHA de commit (full index)
- **WHEN** se solicita indexar el commit SHA que YA existe en S3 (`latest/meta.json` contiene el mismo SHA)
- **THEN** el sistema SHALL omitir el proceso de indexado y registrar un log `INFO` indicando que el repositorio ya está indexado

#### Scenario: Commit no indexado con historial existente (delta)
- **WHEN** se solicita indexar el commit N y en S3 existe `latest/meta.json` con el commit N-1 (pero no el N)
- **THEN** el sistema SHALL descargar `latest/index.db`, ejecutar el delta flow, y subir el DB actualizado como `{N}/index.db` y nuevo `latest/`

### Requirement: Búsqueda de similitud en el store de vectores
El sistema SHALL exponer el método `search` en `IVectorStorePort` para recuperar los K chunks más similares a una consulta de texto, operando sobre una DB libSQL previamente descargada de S3. Este método es el punto de entrada para que `src/agent` consuma el índice en el futuro cambio `agent-rag-integration`.

#### Scenario: Recuperar chunks relevantes
- **WHEN** se invoca `search(query="SQL injection vulnerability", k=5)` con el `index.db` cargado
- **THEN** el sistema SHALL retornar los 5 chunks con mayor similitud coseno al embedding de la query

#### Scenario: Repositorio sin índice
- **WHEN** no existe `latest/index.db` en S3 para el repositorio dado
- **THEN** el sistema SHALL retornar una lista vacía

### Requirement: Recuperar último commit indexado
El sistema SHALL exponer `get_latest_indexed_commit(repository_url) -> Optional[str]` leyendo `latest/meta.json` de S3, para que el orquestador pueda determinar si aplicar delta indexing o full indexing.

#### Scenario: Repositorio con commits indexados
- **WHEN** existe `latest/meta.json` en S3 para el repositorio dado
- **THEN** el sistema SHALL retornar el valor de `commit_sha` contenido en ese archivo

#### Scenario: Repositorio sin historial indexado
- **WHEN** no existe `latest/meta.json` en S3 para el repositorio dado
- **THEN** el sistema SHALL retornar `None`

### Requirement: Eliminar vectores de archivos obsoletos
El sistema SHALL eliminar de la DB libSQL local los vectores de archivos que fueron `modified` o `deleted` en el delta, antes de insertar los nuevos.

#### Scenario: Eliminar vectores de archivos modificados
- **WHEN** el diff indica que `src/auth.py` fue `modified` entre el commit N-1 y el N
- **THEN** el sistema SHALL eliminar todos los chunks cuyo `file_path` sea `src/auth.py` antes de insertar los nuevos chunks del archivo actualizado

#### Scenario: Eliminar vectores de archivos eliminados
- **WHEN** el diff indica que `src/legacy.py` fue `deleted`
- **THEN** el sistema SHALL eliminar todos los chunks de ese archivo sin insertar ninguno nuevo

### Requirement: Delta indexing
El sistema SHALL aplicar delta indexing cuando existe un commit previo indexado: descargar `latest/index.db` de S3, insertar vectores solo para archivos `added` y `modified`, y eliminar vectores para `deleted` y `modified` del commit anterior.

#### Scenario: Delta indexing exitoso
- **WHEN** se indexa el commit N con N-1 ya en S3, y el diff tiene 3 archivos `modified`, 2 `added`, 1 `deleted`
- **THEN** el sistema SHALL insertar vectores para los 5 archivos (3+2), eliminar vectores previos de los 4 (3 modified + 1 deleted), y dejar intactos todos los demás vectores

#### Scenario: Diff vacío — sin cambios a indexar
- **WHEN** el diff entre N-1 y N no produce archivos modificados
- **THEN** el sistema SHALL terminar sin modificar la DB y registrar un log `INFO`
