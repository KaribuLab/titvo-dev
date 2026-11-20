# Proposal

## Why

Cuando un comando Git del indexador RAG falla, el mensaje reportado suele ser `Git command failed: git <subcomando>: unknown error` o solo la última línea de stderr. Eso impide diagnosticar fallos reales (SSH, host key, auth, fetch, rama inexistente). Se necesita ver el error del comando en los logs.

## What Changes

- Enriquecer el fallo de ejecución Git en `rag-indexer` para incluir código de salida y stderr usable (completo o truncado de forma segura).
- Registrar explícitamente el fallo en logs antes de propagar la excepción.
- Conservar redacción de argumentos sensibles (sin URLs ni material de credenciales en el mensaje).
- Ajustar el uso de `--quiet` en operaciones donde silencia el diagnóstico útil al fallar.
- Actualizar pruebas unitarias del runner para exigir exit code + stderr sin filtrar secretos.

## Non-goals

- No cambiar el transporte SSH, host keys ni selección de proveedor.
- No ampliar el alcance a `git-commit-files` ni al agente.
- No alterar la semántica de éxito/fallo del job (sigue fallando explícitamente).
- No introducir telemetría nueva fuera de logs/excepciones existentes.

## Capabilities

### New Capabilities

- (ninguna)

### Modified Capabilities

- `rag-ssh-source-retrieval`: añadir requisito de diagnóstico cuando falla una invocación Git (exit code + stderr visible en error/log, sin filtrar secretos).

## Impact

- Código: `src/rag-indexer/.../ssh_git_repository_adapter.py` (`SubprocessGitRunner` y fetch quiet).
- Tests del runner/adaptador SSH en `rag-indexer`.
- Operación: logs CloudWatch/Batch del indexador más útiles al fallar Git/SSH.
- Spec: delta en `openspec/specs/rag-ssh-source-retrieval`.
