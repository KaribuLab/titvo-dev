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
