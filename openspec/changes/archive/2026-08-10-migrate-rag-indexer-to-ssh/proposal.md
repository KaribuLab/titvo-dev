## Why

El `rag-indexer` obtiene árboles, contenidos y diffs mediante las APIs REST de GitHub y Bitbucket, lo que duplica lógica por proveedor y expone la indexación masiva a paginación, rate limits y múltiples solicitudes por archivo. Git sobre SSH permite obtener las mismas fuentes con un flujo único, reutilizando el patrón ya validado en `git-commit-files` y las credenciales cifradas existentes.

## What Changes

- **BREAKING**: eliminar completamente los adaptadores, configuración, tokens, pruebas y dependencias directas de obtención REST para GitHub y Bitbucket en `rag-indexer`; SSH será el único transporte y no existirá fallback.
- Incorporar un adaptador Git SSH común para repositorios de GitHub y Bitbucket, compatible con URLs HTTPS y SSH.
- Seleccionar y desencriptar únicamente la llave del proveedor correspondiente mediante `github_ssh_private_key` o `bitbucket_ssh_private_key`.
- Resolver ramas, obtener archivos de un commit y calcular deltas mediante comandos Git sobre un repositorio temporal reutilizable durante el job.
- Garantizar la eliminación de la llave privada y del repositorio temporal al completar o fallar la indexación.
- Incorporar Git, OpenSSH y verificación de identidad de host al runtime del contenedor.
- Reemplazar pruebas y documentación orientadas a REST por cobertura y operación SSH.

## Capabilities

### New Capabilities

- `rag-ssh-source-retrieval`: Obtención segura de fuentes y diffs de GitHub y Bitbucket mediante Git sobre SSH, con selección de credenciales, filtrado de archivos y limpieza de recursos temporales.

### Modified Capabilities

Ninguna.

## Impact

- Código: `src/rag-indexer` en composición, factory, adaptadores, puerto de repositorio y pruebas.
- Runtime: `src/rag-indexer/Dockerfile`, dependencias Python y artefactos rastreados bajo `build/lib`.
- Configuración: tabla DynamoDB cifrada con las dos nuevas llaves SSH; `rag-indexer` deja de leer `github_access_token` y `bitbucket_api_token`.
- Documentación: `src/rag-indexer/README.md` y `docs/rag-indexer.md`.

## Non-goals

- Cambiar chunking, embeddings, SQLite, estructura S3 o la selección entre indexación full y delta.
- Añadir soporte para proveedores Git distintos de GitHub y Bitbucket.
- Clonar submódulos, descargar objetos Git LFS o administrar/rotar las llaves SSH.
- Modificar la implementación SSH de `git-commit-files`.
- Modificar `src/rag-indexer/aws/batch/` o cualquier otra infraestructura de red de AWS Batch.
