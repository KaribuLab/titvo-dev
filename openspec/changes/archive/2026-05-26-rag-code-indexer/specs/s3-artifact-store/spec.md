## ADDED Requirements

### Requirement: Persistir base de datos libSQL en S3 por commit
El sistema SHALL subir los archivos de la base de datos libSQL (`index.db`) a S3 usando la estructura `{repo_host}/{owner}/{repo}/{commit_sha}/`, junto con un archivo de metadatos `meta.json` que registra el SHA y la fecha de indexado.

#### Scenario: Subida exitosa tras full index
- **WHEN** se completa el full index del commit SHA `abc123` del repositorio `github.com/KaribuLab/titvo-test`
- **THEN** el sistema SHALL subir `index.db` y `meta.json` a `s3://<bucket>/github.com/KaribuLab/titvo-test/abc123/`

#### Scenario: Subida exitosa tras delta index
- **WHEN** se completa el delta index del commit N sobre una DB descargada del commit N-1
- **THEN** el sistema SHALL subir la DB actualizada a `s3://<bucket>/<repo>/N/index.db` sin modificar el prefijo `N-1/`

#### Scenario: Bucket configurado desde DynamoDB
- **WHEN** la tabla DynamoDB contiene la clave `rag_index_bucket`
- **THEN** el sistema SHALL usar ese bucket para el almacenamiento de los archivos del índice

### Requirement: Mantener puntero latest/
El sistema SHALL mantener actualizado el prefijo `latest/` en S3, copiando `index.db` y `meta.json` del commit recién indexado a `{repo}/latest/` tras cada indexado exitoso.

#### Scenario: Actualizar latest tras indexado
- **WHEN** se completa el indexado (full o delta) del commit N
- **THEN** el sistema SHALL copiar `{repo}/N/index.db` → `{repo}/latest/index.db` y `{repo}/N/meta.json` → `{repo}/latest/meta.json`

#### Scenario: latest siempre contiene el commit más reciente
- **WHEN** se indexa el commit N tras haber indexado N-1
- **THEN** `{repo}/latest/meta.json` SHALL contener `{"commit_sha": "<sha-de-N>", ...}` y el `index.db` de `latest/` SHALL corresponder al commit N

### Requirement: Descargar base de datos libSQL desde S3
El sistema SHALL descargar `latest/index.db` de S3 al sistema de archivos local del contenedor antes de ejecutar un delta index o una búsqueda de similitud.

#### Scenario: Descarga de latest exitosa
- **WHEN** existe `s3://<bucket>/<repo>/latest/index.db`
- **THEN** el sistema SHALL descargar el archivo a una ruta temporal y retornar esa ruta

#### Scenario: latest no existe (primera indexación)
- **WHEN** no existe el prefijo `{repo}/latest/` en S3
- **THEN** el sistema SHALL retornar `None` indicando que se requiere full index

### Requirement: Leer metadatos del último commit indexado
El sistema SHALL leer `latest/meta.json` de S3 para determinar el SHA del último commit indexado sin necesidad de descargar la DB completa.

#### Scenario: Lectura exitosa de meta.json
- **WHEN** existe `s3://<bucket>/<repo>/latest/meta.json`
- **THEN** el sistema SHALL parsear el JSON y retornar el valor de `commit_sha`

#### Scenario: meta.json no existe
- **WHEN** no existe `{repo}/latest/meta.json` en S3
- **THEN** el sistema SHALL retornar `None`
