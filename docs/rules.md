# Reglas

## Implementación

Cada vez que implementes código debes seguir estas reglas:

- COMENTARIOS QUE INDIQUEN PARA QUE SIRVE CADA FUNCIÓN Y ARCHIVO DE CÓDIGO.
- Cuando implementes un spec, AL FINAL GENERA UN DIAGRAMA DE SECUENCIA para que alguien pueda mantener esto sin IA.
- SIEMPRE implementa pruebas unitarias

## Commits

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