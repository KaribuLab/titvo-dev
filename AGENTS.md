## Descripción general

Este repositorio contiene el ambiente de desarrollo para el proyecto Titvo.
Cada uno de los repositorios son componentes desplegables en AWS, el cual es simulado con Localstack.
Los subproyectos son submodulos de git.

Los proyectos de MCP se encuentran en el directorio `src/mcp`.

### Proyectos Lambda

Los proyectos lambda están desarrollados en Node.js versión 22.x y están construidos con Rspack. Cada proyecto tiene su propio directorio `cdklocal` que contiene la infraestructura de CDKLocal.
Además cuenta con un directorio `aws` que contiene la infraestructura de AWS. Cada proyecto tiene su propio directorio `aws` que contiene la infraestructura de AWS.
En cada función lambda NestJS.

- [x] Git Commit Files `src/mcp/git-commit-files`: Procesa los commits de un repositorio de Git y genera un reporte de commits.
- [x] Issue Report `src/mcp/issue-report`: Procesa los issues de un repositorio de Git y genera un reporte de issues.

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

Los mensajes de commit deben ser en español.