# Design

## Context

Ver `proposal.md` para motivación y fuente oficial. El cambio cruza dos submódulos desplegables independientes:

- `git-commit-files`: `src/git-commit-files/respositories-handler/repo-factory.service.ts` usa `REPO_HOST_CONFIG` y construye el remoto con el hostname de entrada. Su cliente SSH y los harness usan actualmente `StrictHostKeyChecking=no`.
- `rag-indexer`: `src/rag_indexer/infra/adapters/ssh_git_repository_adapter.py` valida hosts con `_PROVIDER_SECRET_NAMES` y construye `RepositoryLocation`. El archivo vecino `known_hosts` fija llaves de `bitbucket.org`, pero aún no del hostname nuevo.

Ambos componentes ya seleccionan `bitbucket_ssh_private_key`. La documentación oficial publica `git@ssh.bitbucket.org:workspace/repo.git` y fingerprints para ese hostname.

## Goals / Non-Goals

**Goals:** separar host de entrada e identidad de proveedor del destino Git; hacer equivalente el transporte de entradas HTTPS históricas, SCP históricas y SCP nuevas; mantener la validación exacta y las credenciales existentes.

**Non-Goals:** introducir una librería compartida entre Python y TypeScript, ampliar a formatos `ssh://` actualmente no soportados, cambiar identidades persistidas, modificar endpoints HTTP o cambiar la política de confianza del cliente TypeScript.

## Decisions

### 1. Mapeo explícito de proveedor a destino SSH

En cada parser, reconocer exactamente `bitbucket.org` y `ssh.bitbucket.org` como Bitbucket y construir el destino con `ssh.bitbucket.org`; GitHub continúa con `github.com`. Conservar el hostname de entrada cuando sea parte del modelo existente y derivar separadamente el hostname de transporte. Mantener validación de rutas y protocolos, sin reemplazos globales de strings ni wildcard de dominios.

Alternativas: cambiar solo ejemplos no arregla el remoto generado; reemplazar todo `bitbucket.org` alteraría enlaces web/API; configurar `~/.ssh/config` dependería del entorno en lugar de los artefactos desplegados.

### 2. Credenciales e identidad independientes del transporte

Ambos aliases seleccionan el parámetro actual. La transformación se limita al remoto usado por Git; la URL original no se reescribe en payloads, claves S3 ni claves de indexación. No se promete deduplicar identidades cuando un consumidor cambia por su cuenta su URL de entrada.

### 3. Host keys de RAG bajo el hostname nuevo

Actualizar el archivo fuente `known_hosts` para reconocer `ssh.bitbucket.org`, verificando fingerprints contra la documentación oficial y material publicado en `https://bitbucket.org/site/ssh`. Preservar las entradas existentes si resulta útil para compatibilidad. No confiar únicamente en `ssh-keyscan` ni desactivar `StrictHostKeyChecking=yes`. Verificar que la imagen y los paquetes incluyan el archivo actualizado; regenerar `build/lib` solo si el proyecto lo rastrea y su proceso de build lo requiere.

Alternativa descartada: bypass de verificación para evitar el fallo por hostname. `git-commit-files` no tiene actualmente archivo de confianza; introducir uno sería un endurecimiento independiente.

### 4. Validación equivalente en ambos lenguajes

Probar entradas HTTPS antiguas, SCP antiguas y nuevas, remoto exacto, selección de secreto, host engañoso y regresión GitHub. En RAG validar también el hostname confiable empaquetado y que el runner conserve sus opciones estrictas. En TypeScript actualizar expectativas del cliente y los ejemplos de harness. Ejecutar suites relevantes y linters de cada submódulo; una prueba real autenticada depende de un repositorio y llave de prueba disponibles.

## Risks / Trade-offs

- [Remote nuevo sin host key correspondiente] → cambiar parser y archivo de confianza en la misma versión de RAG y comprobar el artefacto empaquetado.
- [Divergencia entre dos implementaciones] → misma matriz de casos y despliegue de ambos componentes.
- [Restricciones de red al nuevo dominio] → verificar DNS/egress del entorno de ejecución antes del rollout.
- [Confianza SSH desactivada en el cliente TypeScript] → registrar la condición existente; este cambio no la amplía ni resuelve.
- [Cambio involuntario de identidad RAG] → comprobar que el cambio de transporte no altera la URL original ni identificadores derivados.

## Migration Plan

### Referencias verificadas durante implementación

- https://bitbucket.org/site/ssh publica las mismas llaves para ambos hostnames. Contrastadas con los fingerprints oficiales: ED25519 `SHA256:ybgmFkzwOSotHTHLJgHO0QN8L0xErw6vd0VhFA9m3SM`, ECDSA `SHA256:FC73VB6C4OQLSCrjEayhMp9UMxS97caD/Yyi2bhW/J0`, RSA `SHA256:46OSHA1Rmj8E8ERTC6xkNcmGOw9oFxYr0WF6zWW8l1E`.
- `find-docs` / Context7 `/python/cpython`: https://github.com/python/cpython/blob/main/Doc/library/urllib.parse.rst confirma que `urlsplit` no valida entradas; se conserva la validación explícita de hostname y coordenadas. No se agregan APIs de librerías ni dependencias.

1. Implementar y verificar cada submódulo con pruebas unitarias, lint y empaquetado pertinente.
2. Actualizar ejemplos, documentación y diagrama de secuencia; mantener las entradas HTTPS de consumidores.
3. Publicar y desplegar versiones de ambos componentes mediante sus pipelines habituales cuando se solicite implementar/desplegar.
4. Verificar recuperación de archivos y full/delta indexing con Bitbucket en un entorno con credenciales; registrar cualquier verificación bloqueada.
5. Ante una regresión, restaurar la versión anterior del componente afectado solo si el endpoint anterior sigue disponible. Si ya no está disponible, corregir la nueva versión; no introducir fallback silencioso al host antiguo.
