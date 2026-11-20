# Design

## Context

See proposal.md — Why. Hoy `SubprocessGitRunner.run` en `ssh_git_repository_adapter.py` captura `CalledProcessError`, toma solo la última línea de stderr (o `"unknown error"`) y omite `returncode`. `fetch` usa `--quiet`, lo que frecuentemente deja stderr vacío. El test actual exige no filtrar argumentos del comando (URLs/secretos).

## Goals / Non-Goals

**Goals:**
- Hacer observables exit code + stderr de Git fallido en excepción y log.
- Mantener redacción de args sensibles.
- Permitir diagnóstico operativo en Batch/CloudWatch sin cambiar el transporte SSH.

**Non-Goals:**
- Cambiar semántica de éxito/fallo del job.
- Replicar el cambio en `git-commit-files`.
- Cambiar host keys, URLs o selección de proveedor.

## Decisions

### 1. Enriquecer el mensaje en el runner, no en cada caller
- **Choice:** Centralizar formato en `SubprocessGitRunner.run`.
- **Why:** Todos los caminos (`ls-remote`, `fetch`, `ls-tree`, `diff`, `cat-file`, `init`) pasan por el mismo wrapper.
- **Alt:** Log solo en adaptador superior — duplicaría lógica y dejaría callers inconsistentes.

### 2. Contenido del diagnóstico
- **Choice:** `git {args[0]}` + `exit={returncode}` + stderr decodificado (strip; truncar ~4 KiB si es muy largo; preferir cola del stderr si se trunca).
- **Why:** SSH/Git suelen poner la causa al final; el exit code evita `"unknown error"` cuando stderr está vacío.
- **Alt:** Dump completo sin truncar — riesgo de logs enormes; truncar al inicio pierde la causa típica.

### 3. Log explícito antes del raise
- **Choice:** `LOGGER.error(...)` con el mismo texto seguro, luego `raise RuntimeError(...) from error`.
- **Why:** Asegura visibilidad aunque el traceback superior se recorte o se reenvuelva.
- **Alt:** Solo excepción — ya llega al log del proceso, pero con menos control del mensaje.

### 4. Timeout
- **Choice:** Mensaje `Git command timed out: git {args[0]}` + stderr/stdout parciales de `TimeoutExpired` si existen (truncados igual).
- **Why:** Hoy el timeout no aporta salida capturada.

### 5. `--quiet` en fetch
- **Choice:** Quitar `--quiet` del `fetch` (u omitirlo solo no es opción intermedia útil: el quiet es el que vacía stderr).
- **Why:** Sin quiet, Git/SSH emiten la causa al fallar; el éxito sigue siendo ruido aceptable a nivel DEBUG o stdout no logueado (el runner solo retorna stdout).
- **Alt:** Mantener quiet y forzar `GIT_TRACE`/`GIT_SSH_COMMAND -v` solo en error — más complejo y ruidoso; fuera de alcance mínimo.

### 6. Seguridad de redacción
- **Choice:** Seguir omitiendo el resto de `args` del mensaje (URLs, SHAs de refs si vinieran como args, etc.). No loguear `clone_url` ni rutas de llave.
- **Why:** Cumple el escenario de no filtración y el test existente de no argumentos.
- **Alt:** Whitelist de flags seguros (`--depth=1`, `--no-tags`) en el mensaje — útil pero opcional; se puede añadir si el mensaje queda ambiguo entre subcomandos iguales.

## Risks / Trade-offs

- [Stderr con path temporal de llave] → Mitigation: redactar patrones conocidos (`rag-ssh-key-`, rutas bajo temp) si aparecen; baseline: no incluir args.
- [Logs más verbosos en fallos] → Mitigation: truncar ~4 KiB; solo en error path.
- [Quitar `--quiet` aumenta stderr en éxito] → Mitigation: runner no loguea stdout/stderr en éxito; impacto nulo en logs normales.
- [Tests frágiles por texto exacto de Git] → Mitigation: asertar presencia de exit code + substring controlada en fixture, no mensajes SSH reales.

## Migration Plan

1. Desplegar nueva imagen `rag-indexer`.
2. Sin migración de datos ni flags de feature.
3. Rollback: imagen anterior; comportamiento vuelve a mensajes pobres.

## Open Questions

- Ninguna bloqueante. Truncado exacto (4 KiB) y redacción de paths en stderr se fijan en implementación/tests.
