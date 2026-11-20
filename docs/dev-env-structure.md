# Estructura de ambiente de desarrollo

Las tools de MCP se encuentran en el directorio `src/mcp`. Las tools son las siguientes:

- [x] Git Commit Files `src/mcp/git-commit-files`: Obtiene los archivos del commit de un repositorio de Git y los sube a S3.
- [x] Issue Report `src/mcp/issue-report`: Genera un reporte HTML de issues de un repositorio de Git y lo carga en S3.
- [x] Bitbucket Code Insights `src/mcp/bitbucket-code-insights`: Genera un reporte de código de un repositorio de Bitbucket.
- [x] Github Issue `src/mcp/github-issue`: Genera un reporte de issues de un repositorio de Github.
- [x] MCP Gateway `src/mcp/gateway`: Gateway MCP para invocar las tools y exponerlos a través del protocolo MCP.

## Docker Compose

El archivo `docker-compose.yaml` es el archivo de configuración para el ambiente de desarrollo.
Este archivo define los servicios que se deben ejecutar para el ambiente de desarrollo.

## Localstack

El archivo `localstack/app/lib/app-stack.ts` es el archivo de configuración para el ambiente de desarrollo.
Este archivo define los servicios que se deben ejecutar para el ambiente de desarrollo.

### Versiones de CDK en uso

A partir del cierre del change `fix-fast-uri-advisories`, las versiones quedan pineadas así:

- `aws-cdk-lib@2.261.0` en `localstack/app` y en los 5 subdirectorios `cdklocal/` (`src/api/task/trigger/cdklocal`, `src/mcp/git-commit-files/cdklocal`, `src/mcp/bitbucket-code-insights/cdklocal`, `src/mcp/issue-report/cdklocal`, `src/mcp/github-issue/cdklocal`).
- `aws-cdk@2.1145.0` (CLI) en `devDependencies` de los mismos 6 paquetes.
- Imagen Docker del servicio `cdk`: `aws-cdk@2.1145.0` global (pinedo via `ARG CDK_VERSION` en `docker/cdk/Dockerfile`).
- `engines.node >= 20.0.0` lo satisfacen los Dockerfiles (`node:24-alpine3.21`) y CI (`node-version: "22"`).

### Llaves SSH de Git Commit Files

`git-commit-files` usa los parámetros cifrados `github_ssh_private_key` y
`bitbucket_ssh_private_key`. Para cargarlos en LocalStack sin guardar el material privado en el
repositorio, define las llaves codificadas en base64 antes de levantar el servicio `cdk`:

```bash
export GITHUB_SSH_PRIVATE_KEY_BASE64="$(base64 -w 0 ~/.ssh/titvo_github)"
export BITBUCKET_SSH_PRIVATE_KEY_BASE64="$(base64 -w 0 ~/.ssh/titvo_bitbucket)"
docker compose up cdk
```

Las variables son opcionales para el bootstrap general, pero la correspondiente al proveedor es
obligatoria para ejecutar un scan. Las llaves deben estar sin passphrase y sus públicas deben estar
registradas como deploy keys de solo lectura en GitHub o Bitbucket.

### Timeout de espera RAG en LocalStack

`localstack/app/setup.ts` llama al seed condicional de `configuration-seed.ts`
para insertar `rag_indexing_timeout_seconds` con string `"600"` en
`tvo-parameter-configuration-local`, solo si la clave no existe. Repetir el
bootstrap conserva valores personalizados; si la clave falta o está vacía, el
agente usa el default compatible de 600 segundos. No requiere agregar una
variable de entorno de timeout.

Para ajustar deliberadamente el dato a 30 minutos desde el host, usando
credenciales locales y región configuradas:

```bash
aws --endpoint-url http://localhost:4566 dynamodb update-item \
  --table-name tvo-parameter-configuration-local \
  --key '{"parameter_id":{"S":"rag_indexing_timeout_seconds"}}' \
  --update-expression 'SET #v = :v' \
  --expression-attribute-names '{"#v":"value"}' \
  --expression-attribute-values '{":v":{"S":"1800"}}'
```

Los próximos scans Git leerán el nuevo plazo; los ya iniciados conservan su
snapshot. Los ambientes existentes sin la clave siguen funcionando con 600
segundos; ver [guía operativa](rag-indexer.md#despliegue-y-ajuste).

Pruebas reproducibles (crean y eliminan sus propias tablas temporales):

```bash
docker compose up -d localstack
# Desde src/agent:
TITVO_TEST_DYNAMODB_ENDPOINT=http://localhost:4566 uv run pytest tests/integration/test_rag_timeout_localstack.py -q --log-cli-level=INFO
# Desde localstack/app (dependencias instaladas con npm ci):
TITVO_TEST_DYNAMODB_ENDPOINT=http://localhost:4566 npm test
```

La variable `TITVO_TEST_DYNAMODB_ENDPOINT` selecciona únicamente el emulador para
los tests, no configura el timeout del agente. Sin ella se omiten los smokes y se
ejecutan las pruebas unitarias habituales.

## Agentes

## Agente AWS Lambda Node.js

Las funciones lambda están programadas en Node.js versión 22.x y están construidas con Rspack. Cada función tiene su propio directorio `cdklocal` que contiene la infraestructura de CDKLocal.
Además cuenta con un directorio `aws` que contiene la infraestructura de AWS.
En cada función lambda se usa NestJS con TypeScript.

Debes seguir las siguientes reglas en el código de la función lambda:

- [ ] Usar el patrón de diseño de arquitectura hexagonal.
- [ ] Usar el patrón de diseño de responsabilidad única.
- [ ] Usar el patrón de diseño de inversión de dependencias.
- [ ] Usar el patrón de diseño de responsabilidad única.
