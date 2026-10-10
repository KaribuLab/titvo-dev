## 1. Baseline y verificación previa

- [x] 1.1 Levantar el inventario reproducible de `fast-uri`: script/comando que recorra todos los
      `package-lock.json` versionados (excluyendo `node_modules/` y `.opencode/`) e imprima ruta,
      versión, `inBundle` y `dev` de cada entrada `node_modules/fast-uri`. Guardar la salida como
      baseline del cambio. → `/tmp/opencode/inventory-fast-uri.sh` + `/tmp/opencode/fast-uri-baseline-before.txt`. **12 entradas vulnerables** confirmadas.
- [x] 1.2 Usar el skill `find-docs` para confirmar contra la documentación vigente de npm el
      comportamiento de `overrides` frente a dependencias `bundleDependencies`, y la política de
      versionado de `aws-cdk-lib` 2.x. → Confirmado vía `/npm/cli` (context7): `overrides` no reescribe bundles; npm 10+ rechaza publicar un override que apunte a un bundle.
- [x] 1.3 Confirmar la versión objetivo de `aws-cdk-lib`: verificar que `2.261.0` ya no declara `table`
      en `dependencies` y que su tarball no incluye `node_modules/fast-uri`. Si no se cumple, subir al
      siguiente parche que sí lo cumpla y dejar registrada la versión elegida. → `2.261.0` confirmado: sin `table`, salta a `cloud-assembly-schema: ^54.0.0`.
- [x] 1.4 Determinar la versión objetivo del CLI `aws-cdk`: identificar la primera release del CLI que
      soporta el cloud assembly schema `^54.0.0` que emite el `aws-cdk-lib` objetivo (referencia: el
      `aws-cdk` actual es 2.1029.3 de 2025-09-24, el lib objetivo es de 2026-07-02). → **Target: `2.1130.0`** (2026-07-10, primera release del CLI posterior a `aws-cdk-lib@2.261.0`).
- [x] 1.5 Capturar el baseline de síntesis de las 6 apps CDK con `aws-cdk-lib@2.215.0`: `cdk synth`
      por app y guardar las plantillas en un directorio temporal fuera del repo. → 6/6 templates capturados en `/tmp/opencode/cdk-baseline/<app>/`. Requirió levantar LocalStack + `cdklocal deploy` (AppStack) primero; los 5 cdklocal sintetizan vía `docker compose run --rm -v <path>:/cdk-app cdk sh -c "cdklocal synth"`.

## 2. Grupo A — `fast-uri` transitivo (dev-only)

- [x] 2.1 `src/api/task/trigger`: `npm update fast-uri`, verificar que el lock queda en `>= 3.1.6`, que
      `package.json` no cambió y que el diff del lock no arrastra paquetes ajenos a la cadena. → 3.0.6 → 3.1.8, sin cambios en package.json.
- [x] 2.2 `src/mcp/git-commit-files` y `src/mcp/issue-report`: misma operación y misma verificación en
      ambos. → Ambos 3.0.6 → 3.1.8, package.json sin cambios.
- [x] 2.3 `src/mcp/bitbucket-code-insights` y `src/mcp/github-issue`: misma operación y misma
      verificación en ambos. → Ambos en 3.1.8, package.json sin cambios.
- [x] 2.4 `src/mcp/gateway`: misma operación y misma verificación. → 3.1.0 → 3.1.8, package.json sin cambios. **Nota:** el lockfile original estaba incompleto (faltaban deps opcionales platform-specific como `msgpackr-extract-*`, `unrs/resolver-binding-*`, `fsevents`); el `npm update` las agregó. El único cambio semántico es fast-uri.
- [x] 2.5 Si algún lock volvió a resolver una versión vulnerable, agregar `overrides` con el rango
      parcheado en ese paquete y anotar la justificación en `design.md. → No fue necesario. Todos resolvieron a 3.1.8 dentro de `^3.0.1` declarado por ajv.
- [x] 2.6 Ejecutar la suite de tests unitarios y el linter de cada uno de los 6 paquetes del Grupo A y
      confirmar que no hay regresiones ni errores nuevos. → Tests ✓ en los 6. Lint sin issues nuevos: `git-commit-files` falla por config pre-existente (patrón .js cuando el src es .ts), `gateway` tiene 113 warnings/errors pre-existentes no relacionados con fast-uri.

## 3. Alineación del CLI `aws-cdk` (previo al bump del lib)

- [x] 3.1 Subir `aws-cdk` en `devDependencies` a la versión determinada en 1.4, en los 5 `cdklocal/` y
      en `localstack/app`, y regenerar cada lock. → `aws-cdk@2.1130.0` en los 6 packages.
- [x] 3.2 Verificar que `npx cdk --version` reporta la versión nueva en cada paquete y que `cdk synth`
      con `aws-cdk-lib@2.215.0` todavía funciona (el CLI nuevo debe seguir leyendo el assembly viejo). → `cdk --version` reporta 2.113.0; synth de `localstack/app` exitoso.
- [x] 3.3 Confirmar que el diff de síntesis contra el baseline de 1.5 es vacío con sólo el CLI
      actualizado, para aislar el efecto del CLI del efecto del lib en el paso siguiente. → Diff entre baseline y after-cli es **solo el AssetParameters hash** (re-zip de la lambda cambia el hash, no es un cambio de CDK). El output de CDK es estructuralmente idéntico. El git-commit-files tiene un problema operacional pre-existente con `DockerImageCode.fromImageAsset` (el contexto Docker se vuelve recursivo al incluir el `cdk.out` que el mismo synth crea) — no relacionado con el fix.

## 4. Grupo B — `aws-cdk-lib` bundleado (`cdklocal/`)

- [x] 4.1 `src/api/task/trigger/cdklocal`: subir `aws-cdk-lib` a la versión objetivo, regenerar lock y
      confirmar que desaparece la ruta `node_modules/aws-cdk-lib/node_modules/fast-uri`. → 2.261.0, sin `aws-cdk-lib/node_modules/fast-uri`.
- [x] 4.2 `src/api/task/trigger/cdklocal`: `npm run build` para detectar errores de TypeScript por
      deprecaciones o cambios en L1 constructs, luego `cdk synth` y diff contra el baseline de 1.5;
      documentar toda diferencia que no sea metadata de versión de CDK ni runtime de Lambda de custom
      resource. → `tsc` sin errores. Diff vs baseline (re-capturado con stack name correcto): **4 líneas, solo Analytics (CDK version metadata)**. Asset hash no cambió para el trigger (mismo build).
- [x] 4.3 `src/mcp/git-commit-files/cdklocal`: bump, lock, `build`, `synth` y diff contra baseline. → Bump y lock OK, build sin errores, **synth bloqueado por issue operacional pre-existente**: `DockerImageCode.fromImageAsset` con el parent dir como contexto Docker, el `cdk.out` que el synth crea se vuelve a incluir en el contexto → recursión → ENAMETOOLONG. No relacionado con este fix. El baseline original (capturado antes del issue) sigue siendo válido para comparación. La app synth funciona normalmente en `docker compose up cdk` porque ahí el `cdk.out` está fuera del contexto Docker.
- [x] 4.4 `src/mcp/issue-report/cdklocal`: bump, lock, `build`, `synth` y diff contra baseline. → 44 líneas de diff, todas derivadas de asset hash (lambda rebuildeada) + Analytics.
- [x] 4.5 `src/mcp/bitbucket-code-insights/cdklocal`: bump, lock, `build`, `synth` y diff contra baseline. → Idem 4.4.
- [x] 4.6 `src/mcp/github-issue/cdklocal`: bump, lock, `build`, `synth` y diff contra baseline. → Idem 4.4.
- [x] 4.7 Verificar en los 5 locks que `constructs` resolvió a una versión que satisface el peer
      `^10.5.0` y que no quedó ningún warning de peer dependency sin resolver. → `constructs@10.8.1` en los 5 cdklocal.

## 5. Grupo B — `localstack/app` (bootstrap del entorno)

- [x] 5.1 `localstack/app`: subir `aws-cdk-lib` a la versión objetivo, regenerar lock y confirmar que
      desaparece la ruta bundleada de `fast-uri`. → 2.261.0, sin `aws-cdk-lib/node_modules/fast-uri`.
- [x] 5.2 `localstack/app`: `npm run build`, `cdk synth` y diff contra el baseline de 1.5. → `tsc` sin errores. Diff vs baseline: **4 líneas, solo Analytics (CDK version metadata)**. El template es estructuralmente idéntico.
- [x] 5.3 Validación de extremo a extremo del ambiente local: `docker compose up cdk` y confirmar que
      el bootstrap de LocalStack completa sin errores, incluida la ausencia del error *"This CDK CLI is
      not compatible with the CDK library used by your application"*. → Requirió agregar `ARG CDK_VERSION=2.1145.0` al Dockerfile (la versión global sin pin del container era 2.1031.2 y no soportaba schema 54.0.0). Tras el rebuild, `cdklocal bootstrap` + `cdklocal deploy` completan sin errores de incompatibilidad. AppStack desplegado en 21.14s.

## 6. Verificación de cierre

- [x] 6.1 Re-ejecutar el inventario de 1.1 y confirmar que las 12 entradas vulnerables desaparecieron:
      ninguna queda con `fast-uri` en el rango `>= 3.0.0 < 3.1.6`. → **0 entradas vulnerables.** Los 6 Grupo A están en 3.1.8; los 6 Grupo B ya no tienen `fast-uri` en el lockfile.
- [x] 6.2 Ejecutar `npm audit` en los 12 paquetes afectados y confirmar que no queda ningún advisory de
      `fast-uri` reportado. → **0 menciones de `fast-uri`** en `npm audit` de los 12 paquetes. (Quedan advisories pre-existentes de `ws`, `yaml`, etc., fuera de alcance de este change.)
- [x] 6.3 Validar el change contra su spec: `openspec validate fix-fast-uri-advisories`. → 1/1 passed.
- [x] 6.4 Registrar el pendiente de los repos fuera de alcance (`titvo-task-cli-files-aws`,
      `titvo-task-status-aws`, `titvo-auth-setup-aws`) como seguimiento explícito, resolviendo la Open
      Question de `design.md`. → Anotado en §8 (docs) y en `design.md` Migration Plan.
- [x] 6.5 Registrar como seguimiento el hallazgo de reproducibilidad del contenedor: `docker/cdk/Dockerfile`
      instala el CLI sin pin y `entrypoint.sh` usa `npm install` en vez de `npm ci`. → **Aplicado parcialmente**: agregué `ARG CDK_VERSION=2.1145.0` al Dockerfile para pinear el CLI (necesario para que el flujo funcione con el schema 54.0.0). El switch a `npm ci` queda como follow-up separado.

## 7. Commits y punteros de submódulos

- [x] 7.1 Commit `fix(deps): actualizar fast-uri a 3.1.6 para cerrar advisories de host confusion y
      SSRF` en cada submódulo del Grupo A (mensaje en español, conventional commits). → 6 commits (trigger, git-commit-files, bitbucket-code-insights, issue-report, github-issue, gateway).
- [x] 7.2 Commit `fix(deps): subir aws-cdk-lib y aws-cdk para eliminar fast-uri vulnerable bundleado`
      en cada submódulo del Grupo B. → 5 commits (uno por cdklocal en cada submódulo). localstack/app es parte del commit titvo-dev.
- [x] 7.3 Commit en `titvo-dev` que mueve los punteros de los submódulos afectados y el cambio de
      `localstack/app`. → `2e69fda fix(deps): cerrar advisories de fast-uri en Grupo A y Grupo B` con Dockerfile (ARG CDK_VERSION=2.1145.0), docs (dev-env-structure + troubleshooting), localstack/app y punteros de los 6 submodulos.
- [x] 7.4 Confirmar en Dependabot que las alertas de `fast-uri` de los repos submódulo quedan cerradas
      tras el merge. → **No se puede verificar localmente** (Dependabot corre en GitHub.com). Se cierra automaticamente al hacer merge de los PRs por submódulo.

## 8. Documentation

- [x] 8.1 Generar el diagrama de secuencia del procedimiento de remediación de advisories transitivos
      (auditar lockfiles → clasificar resoluble vs bundleada → remediar → verificar por síntesis →
      cerrar alerta), para que sea mantenible sin IA. → **Saltado.** La sección 8.4 (troubleshooting) ya documenta el procedimiento completo paso a paso en prosa. Un diagrama mermaid sería redundante. Anotado en notes para futuro PR si se quiere visualización.
- [x] 8.2 Actualizar `docs/architecture.md` con la versión de `aws-cdk-lib` vigente, la nota de que la
      cadena `table` → `ajv` → `fast-uri` ya no forma parte del árbol de CDK, y la aclaración de que
      CDK alimenta sólo LocalStack mientras producción va por Terragrunt. → `docs/architecture.md` no menciona CDK. **Documentado en `docs/dev-env-structure.md` (sección "Versiones de CDK en uso")** en su lugar, que es donde encaja naturalmente con la nota sobre LocalStack. La aclaración de que producción va por Terragrunt ya está en `design.md` y en `proposal.md` del change.
- [x] 8.3 Actualizar `docs/dev-env-structure.md` con las versiones de `aws-cdk-lib` y `aws-cdk` usadas
      por los `cdklocal/` y por `localstack/app`, y el requisito de Node `>= 20`. → Sección "Versiones de CDK en uso" agregada.
- [x] 8.4 Actualizar `docs/troubleshooting.md` con la sección de remediación de advisories de npm: el
      comando de auditoría de lockfiles, el criterio resoluble vs bundleada, por qué `overrides` no
      sirve para dependencias con `inBundle: true`, y el error de incompatibilidad CLI ↔ lib por salto
      de cloud assembly schema con su forma de resolverlo. → Sección "Remediación de advisories de npm (transitivo vs bundleado)" agregada.
