# Proposal

## Why

Atlassian documenta `ssh.bitbucket.org` como hostname para Git sobre SSH. Tanto `rag-indexer` como `git-commit-files` construyen actualmente remotos con `bitbucket.org`; deben adoptar el endpoint nuevo sin romper las URLs existentes de los consumidores.

## What Changes

- Normalizar las entradas Bitbucket existentes y las nuevas URLs SCP con `ssh.bitbucket.org` al remoto `git@ssh.bitbucket.org:workspace/repository.git` en ambos componentes.
- Mantener la selección interna de `bitbucket_ssh_private_key` para ambos nombres.
- Actualizar las host keys versionadas de RAG para el hostname de transporte, conservando la verificación estricta.
- Actualizar pruebas, ejemplos, harness y documentación de ambos componentes.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `repository-ssh-access`: normalización del remoto y credenciales de Bitbucket en `git-commit-files`.
- `rag-ssh-source-retrieval`: selección de proveedor, destino SSH y confianza del endpoint nuevo en RAG.

## Impact

Submódulos `src/mcp/git-commit-files` y `src/rag-indexer`, sus factories/adaptadores, pruebas, harness y documentación; `docs/architecture.md` y `docs/rag-indexer.md`. No requiere nuevas credenciales ni dependencias.

## Non-goals

Cambiar endpoints HTTPS/REST, migrar GitHub, incorporar `altssh.bitbucket.org:443`, cambiar contratos MCP, identidades de indexación o modos de scan. Endurecer la política SSH actual de `git-commit-files` queda fuera de este cambio de hostname.

## References

- https://support.atlassian.com/bitbucket-cloud/docs/configure-ssh-and-two-step-verification/ — formatos SSH y fingerprints oficiales consultados durante la propuesta.
