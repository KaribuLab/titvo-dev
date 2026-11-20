# Tasks

## 1. Confirmar contratos externos

- [x] 1.1 Usar el skill `find-docs` para validar la documentación actual de las librerías utilizadas y la referencia oficial Atlassian del hostname SSH; verificar dejando las fuentes pertinentes en el diseño o documentación del componente.
- [x] 1.2 Obtener las host keys oficiales de Bitbucket y contrastar fingerprints publicados; verificar que las llaves propuestas para `ssh.bitbucket.org` coinciden antes de incorporarlas.

## 2. git-commit-files

- [x] 2.1 Actualizar el mapeo y normalización en `repo-factory.service.ts` para usar `ssh.bitbucket.org` con ambas entradas Bitbucket y la misma credencial; verificar casos HTTPS antiguo, SCP antiguo y SCP nuevo con tests unitarios de factory.
- [x] 2.2 Generar o actualizar tests unitarios del cliente SSH y factory: remoto exacto, secreto, falta de llave, rechazo de host engañoso y regresión GitHub; verificar que las suites afectadas pasan y el linter del submódulo no reporta errores.
- [x] 2.3 Actualizar ejemplos de los harness SSH y documentación del componente, añadiendo comentarios explicativos a código nuevo o modificado; verificar que los ejemplos de clonación usan el nuevo host y los ejemplos HTTPS conservan `bitbucket.org`.

## 3. rag-indexer

- [x] 3.1 Actualizar `parse_repository_url` y mapeo de proveedor para derivar el destino SSH nuevo sin reescribir la URL de identidad; verificar tests unitarios para ambas variantes SCP, HTTPS histórico, secreto y regresión GitHub.
- [x] 3.2 Incorporar `ssh.bitbucket.org` al archivo fuente `known_hosts` con las llaves verificadas y revisar su empaquetado; verificar con `ssh-keygen -F ssh.bitbucket.org` sobre el archivo empaquetado y contrastar sus fingerprints oficiales.
- [x] 3.3 Generar o actualizar tests unitarios de parser/runner para hosts engañosos, identidad de entrada preservada y opciones SSH estrictas; verificar suites relevantes y linter Python sin errores. Comprobar si `build/lib` está rastreado y regenerarlo únicamente mediante el build correspondiente cuando aplique.
- [x] 3.4 Actualizar `src/rag-indexer/README.md` y comentarios del código modificado; verificar que se distingue URL de entrada de destino SSH y que el procedimiento documenta confianza para el hostname nuevo.

## 4. Verificación integrada

- [x] 4.1 Comparar la matriz de normalización y credenciales de ambos componentes; verificar que todos los formatos comprometidos por las specs producen el mismo remoto y secreto, y que las URLs web/API e identidades persistidas no fueron reemplazadas globalmente.
- [x] 4.2 Verificar el recorrido real de recuperación de archivos y full/delta indexing en un entorno con repositorio y credencial de prueba disponibles; registrar resultados y cualquier bloqueo de acceso de forma explícita si no se puede ejecutar el smoke test.

Evidencia y limitación del smoke test: ver `verification.md`. La tarea 4.2 se cierra por registro explícito del bloqueo, no por una ejecución autenticada exitosa.

## 5. Documentation

- [x] 5.1 Actualizar `docs/architecture.md` con la separación entre host de entrada y transporte de ambos componentes y generar el diagrama de secuencia del spec; verificar que muestra selección de llave, destino `ssh.bitbucket.org` y verificación de host en RAG.
- [x] 5.2 Actualizar `docs/rag-indexer.md` con formatos aceptados, hostname de transporte y confianza SSH; verificar coherencia con README, tests y specs, manteniendo URLs HTTPS existentes.
