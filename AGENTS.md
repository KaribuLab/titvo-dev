## Descripción general

Este repositorio contiene el ambiente de desarrollo para el proyecto Titvo.
Cada uno de los repositorios son componentes desplegables en AWS, el cual es simulado con Localstack.
Los subproyectos son submodulos de git.

Las tools de MCP se encuentran en el directorio `src/mcp`. Las tools son las siguientes:

- [x] Git Commit Files `src/mcp/git-commit-files`: Obtiene los archivos del commit de un repositorio de Git y los sube a S3.
- [x] Issue Report `src/mcp/issue-report`: Genera un reporte HTML de issues de un repositorio de Git y lo carga en S3.
- [x] Bitbucket Code Insights `src/mcp/bitbucket-code-insights`: Genera un reporte de código de un repositorio de Bitbucket.
- [x] Github Issue `src/mcp/github-issue`: Genera un reporte de issues de un repositorio de Github.
- [x] MCP Gateway `src/mcp/gateway`: Gateway MCP para invocar las tools y exponerlos a través del protocolo MCP.

### Docker Compose

El archivo `docker-compose.yaml` es el archivo de configuración para el ambiente de desarrollo.
Este archivo define los servicios que se deben ejecutar para el ambiente de desarrollo.

### Localstack

El archivo `localstack/app/lib/app-stack.ts` es el archivo de configuración para el ambiente de desarrollo.
Este archivo define los servicios que se deben ejecutar para el ambiente de desarrollo.

### Commits

El proyecto usa conventional commits de Git.

- `feat`: Nueva funcionalidad.
- `fix`: Corrección de errores.
- `docs`: Cambios en la documentación.
- `refactor`: Refactorización de código.
- `test`: Agregación de tests.
- `chore`: Cambios en la configuración.
- `style`: Cambios en la forma de escribir el código.
- `perf`: Mejoras de rendimiento.
- `build`: Cambios en la construcción del proyecto.
- `ci`: Cambios en la configuración de CI.

Los prefijos de los commits se utilizan para semantic versioning, por lo que hay que considerar si efectivamente el prefijo corresponde a un incremento de versión: MAJOR, MINOR, PATCH.

- MAJOR: Cambios que afectan la compatibilidad con versiones anteriores.
- MINOR: Cambios que añaden funcionalidad pero no afectan la compatibilidad.
- PATCH: Cambios que arreglan errores o mejoras de rendimiento.

**Los mensajes de commit deben ser en español.**

## Agentes

### Agente AWS Lambda Node.js

Las funciones lambda están programadas en Node.js versión 22.x y están construidas con Rspack. Cada función tiene su propio directorio `cdklocal` que contiene la infraestructura de CDKLocal.
Además cuenta con un directorio `aws` que contiene la infraestructura de AWS.
En cada función lambda se usa NestJS con TypeScript.

Debes seguir las siguientes reglas en el código de la función lambda:

- [ ] Usar el patrón de diseño de arquitectura hexagonal.
- [ ] Usar el patrón de diseño de responsabilidad única.
- [ ] Usar el patrón de diseño de inversión de dependencias.
- [ ] Usar el patrón de diseño de responsabilidad única.
