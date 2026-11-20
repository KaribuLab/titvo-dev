# Tasks

## 1. Diagnóstico en SubprocessGitRunner

- [x] 1.1 En `SubprocessGitRunner.run`, al capturar `CalledProcessError`, construir mensaje con subcomando, `returncode` y stderr (completo o truncado ~4 KiB por la cola); verificar con test unitario que exit code y stderr aparecen y que args sensibles no se filtran
- [x] 1.2 En el mismo runner, ante `TimeoutExpired`, incluir en el error fragmentos de stderr/stdout si existen; verificar con test de timeout
- [x] 1.3 Emitir `LOGGER.error` con el mensaje seguro antes del `raise`; verificar que el test captura el log en nivel error

## 2. Fetch sin silenciar diagnóstico

- [x] 2.1 Quitar `--quiet` del `git fetch` en el adaptador SSH; verificar que el test de fetch espera la nueva lista de args y que un fallo simulado de fetch expone stderr/exit en el mensaje

## 3. Documentation

- [x] 3.1 Actualizar `docs/rag-indexer.md` con la semántica de errores Git (exit code + stderr en log/excepción, sin secretos) y verificar que el texto coincide con el comportamiento implementado
- [x] 3.2 Actualizar `docs/architecture.md` solo si describe el flujo SSH/Git del indexador y omite el diagnóstico de fallos; verificar que no contradice el delta de `rag-ssh-source-retrieval`

## Workflow follow-up

- Archive el change tras review e implementación.
- Verificar el resultado archivado en specs principales.
