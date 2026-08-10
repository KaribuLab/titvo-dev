## Context

`rag-indexer` implementa `IRepositoryProvider` con adaptadores REST separados para GitHub y Bitbucket. Ambos resuelven ramas, recorren árboles, descargan contenidos y calculan diffs, pero con contratos, paginación y límites propios de cada API. El caso de uso consume tres operaciones neutrales al proveedor: `resolve_branch_sha`, `get_files` y `get_changed_files`.

`git-commit-files` ya valida el patrón operativo base para SSH: llave cifrada en DynamoDB, archivo temporal `0600`, `GIT_SSH_COMMAND`, comandos Git sin shell y limpieza del clone. Su implementación es TypeScript y está acoplada a Bitbucket, por lo que `rag-indexer` reutilizará las decisiones y no el código.

El job corre una sola indexación en un contenedor AWS Batch efímero. En modo delta, el SHA previamente indexado puede no estar incluido en un clone shallow del SHA objetivo, por lo que ambos commits deben obtenerse explícitamente.

## Goals / Non-Goals

**Goals:**

- Usar exclusivamente Git sobre SSH para obtener fuentes de GitHub y Bitbucket.
- Mantener sin cambios el contrato funcional full/delta del caso de uso.
- Compartir una implementación entre proveedores y seleccionar una llave cifrada por host.
- Minimizar red y disco manteniendo solo los objetos Git necesarios para cada job.
- Evitar shell injection, env hijacking, traversal por symlinks y exposición de llaves.
- Liberar determinísticamente credenciales y datos temporales.

**Non-Goals:**

- Cambiar embeddings, chunking, vector store, artefactos S3 o disparo de jobs.
- Conservar código, configuración, pruebas, dependencias directas o fallback REST para GitHub o Bitbucket en `rag-indexer`.
- Soportar otros hosts Git, submódulos, descarga Git LFS o llaves protegidas por passphrase.
- Extraer una librería compartida entre los subproyectos Python y TypeScript.
- Modificar `src/rag-indexer/aws/batch/`, security groups, routing, NACLs u otra infraestructura Batch.

## Decisions

### Un adaptador SSH común con factory por host exacto

La factory parseará URLs HTTPS y SCP-like SSH, aceptará únicamente `github.com` y `bitbucket.org`, normalizará el remoto a SSH y elegirá el parámetro correspondiente:

| Host | Parámetro cifrado |
|---|---|
| `github.com` | `github_ssh_private_key` |
| `bitbucket.org` | `bitbucket_ssh_private_key` |

La llave se solicitará después de validar el host, de modo que cada job desencripte solo la credencial necesaria. Un parámetro ausente producirá un error explícito y no activará fallback REST.

**Alternativa descartada:** mantener dos adaptadores SSH. Repetiría ejecución, filtrado, diff y manejo de temporales sin diferencias funcionales entre proveedores.

### Repositorio temporal de objetos, sin working tree

El adaptador creará un repositorio temporal con `git init` y traerá por SSH únicamente los commits necesarios mediante fetch shallow. Esto conserva el enfoque clone-oriented de `git-commit-files`, pero evita clonar la rama por defecto y hacer checkout.

- Full: `ls-remote` resuelve la rama; si se requiere indexar, se trae el SHA objetivo.
- Delta: se traen el SHA previo y el SHA objetivo al mismo repositorio antes del diff.
- Archivos: `git ls-tree` enumera solo blobs y `git cat-file` obtiene su contenido por objeto.
- Diff: `git diff --name-status -z -M` entrega estados sin ambigüedad por espacios o caracteres especiales.

El repositorio se reutilizará entre `get_changed_files` y `get_files`, evitando una segunda descarga en delta. Los renames conservarán la semántica actual: ruta anterior eliminada y ruta nueva añadida.

**Alternativa descartada:** checkout y lectura directa del filesystem. Puede seguir symlinks controlados por el repositorio, introduce efectos de Git LFS y requiere más disco.

**Alternativa descartada:** clone completo. Simplifica el diff, pero transfiere historial innecesario y aumenta tiempo y almacenamiento para repositorios grandes.

### Ejecución Git endurecida

Los comandos se ejecutarán con argumentos estructurados y `shell=False`. El entorno hijo será mínimo y controlado, incluirá `GIT_TERMINAL_PROMPT=0`, deshabilitará configuración Git externa relevante y fijará `GIT_SSH_COMMAND` con la llave temporal, `IdentitiesOnly=yes`, `BatchMode=yes` y un archivo `known_hosts` mantenido por el servicio.

La verificación de host será estricta con claves públicas fijadas para los endpoints oficiales. No se copiará `StrictHostKeyChecking=no` desde la referencia. Las URLs se validarán antes de llegar a Git y los mensajes no incluirán contenido de llaves.

**Alternativa descartada:** `ssh-keyscan` en cada job. La clave obtenida por la misma red que se intenta autenticar no protege el primer contacto frente a MITM.

### Filtrado y decodificación conservan la conducta observable

Las exclusiones actuales de directorios y extensiones se centralizarán en el adaptador común. Solo blobs serán candidatos; los gitlinks de submódulos se omitirán. Cada blob se decodificará como UTF-8 de forma aislada: un archivo ilegible se registrará y omitirá sin abortar los demás, equivalente al aislamiento por archivo del adaptador GitHub actual.

### Cierre explícito desde la composición

El puerto de repositorio expondrá cierre idempotente, y `main.py` envolverá toda la ejecución en `try/finally`. El cierre eliminará el archivo de llave, su directorio y el repositorio temporal tanto en éxito como en error, incluyendo retornos por idempotencia. La terminación del contenedor no será el mecanismo primario de limpieza.

### Runtime y artefactos

La imagen instalará `git` y `openssh-client`. Se eliminarán ambos adaptadores REST, sus pruebas, las lecturas de tokens API y el uso directo de `httpx`; luego se regenerará `uv.lock`. Como `build/lib` está versionado y se mantiene como espejo de `src`, se actualizará en el mismo cambio sin conservar componentes REST. Su eventual eliminación requiere una propuesta separada.

## Risks / Trade-offs

- **[Fetch directo por SHA rechazado por el servidor]** → Cubrir el comando con pruebas unitarias e integración Git local; fallar explícitamente sin degradar a REST.
- **[Rotación de host keys]** → Mantener las claves fijadas como configuración versionada y verificarlas contra la publicación oficial de cada proveedor durante upgrades.
- **[Repositorios grandes consumen disco]** → Usar fetch shallow de uno o dos commits, sin checkout ni submódulos, y medir uso en el smoke test.
- **[Llave con passphrase bloquea el job]** → Exigir deploy keys de solo lectura sin passphrase y `BatchMode=yes`.
- **[Cambio incompatible de credenciales]** → Verificar ambos parámetros SSH antes de desplegar y comunicar que los tokens dejan de aplicar solamente a `rag-indexer`.

## Migration Plan

1. Cargar y validar `github_ssh_private_key` y `bitbucket_ssh_private_key` cifradas con acceso de solo lectura a los repositorios esperados.
2. Construir la imagen con Git/OpenSSH y ejecutar tests unitarios e integración Git local.
3. Desplegar la nueva imagen y ejecutar un full seguido de un delta por proveedor.
4. Confirmar artefactos S3, métricas de archivos y ausencia de temporales después del job.
5. Retirar de `rag-indexer` los tokens, adaptadores, pruebas, configuración y documentación REST; otros servicios pueden conservar sus propias integraciones.

Rollback: desplegar la versión anterior completa. La nueva implementación no contendrá una ruta de fallback. Los índices S3 son compatibles porque esta migración no cambia su formato ni sus rutas.

## Open Questions

Ninguna.
