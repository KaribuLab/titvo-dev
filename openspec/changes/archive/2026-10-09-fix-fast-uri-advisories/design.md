## Context

`fast-uri` es una dependencia transitiva que entra al workspace por dos caminos independientes, y cada
camino exige una remediación distinta. El inventario levantado sobre los lockfiles versionados
(excluyendo `node_modules/` y `.opencode/`, que es tooling local) es:

**Grupo A — transitivo resoluble, `"dev": true`**

| Lockfile | `fast-uri` | Entra por |
|---|---|---|
| `src/api/task/trigger/package-lock.json` | 3.0.6 | `ajv-formats` / `schema-utils` → `ajv@8.17.1` |
| `src/mcp/git-commit-files/package-lock.json` | 3.0.6 | `ajv@8.17.1` |
| `src/mcp/bitbucket-code-insights/package-lock.json` | 3.0.6 | `ajv@8.17.1` |
| `src/mcp/issue-report/package-lock.json` | 3.0.6 | `ajv@8.17.1` |
| `src/mcp/gateway/package-lock.json` | 3.1.0 | `ajv@8.17.1` |
| `src/mcp/github-issue/package-lock.json` | 3.1.0 | `ajv@8.17.1` |

**Grupo B — bundleado (`inBundle: true`) dentro de `aws-cdk-lib@2.215.0`**

`src/api/task/trigger/cdklocal`, `src/mcp/git-commit-files/cdklocal`,
`src/mcp/bitbucket-code-insights/cdklocal`, `src/mcp/issue-report/cdklocal`,
`src/mcp/github-issue/cdklocal` y `localstack/app`. Los seis con `fast-uri` 3.1.0 en
`node_modules/aws-cdk-lib/node_modules/fast-uri`.

Los sub-paquetes de `src/api/task/trigger` (`trigger/`, `auth/`, `lib/aws/`, `shared/`) tienen lockfile
propio pero **no** contienen `fast-uri`.

Restricciones: cada directorio afectado vive en un submódulo git distinto, así que el cambio se
commitea por repo y después se mueven los punteros en `titvo-dev`.

**Alcance real de CDK**: `cdklocal/` y `localstack/app` sintetizan únicamente contra LocalStack.
Producción se despliega con Terragrunt (`aws/` + `.github/workflows/deploy-to-aws.yml`), que no usa
`aws-cdk-lib`. Esto acota el radio de daño del Grupo B: los stacks afectados son efímeros y se
reconstruyen en cada `docker compose up`, por lo que un cambio de logical ID no implica reemplazo de
ningún recurso de AWS real.

**Versiones de Node del entorno**: CI usa Node 22 (`node-version: "22"` en los `deploy-to-aws.yml`) y
`docker/cdk/Dockerfile`, `docker/lambda/node/Dockerfile` y `src/mcp/gateway/Dockerfile` usan
`node:24-alpine3.21`. Todos satisfacen `engines.node >= 20.0.0` de `aws-cdk-lib@2.26x`.

## Goals / Non-Goals

**Goals:**
- Llevar todo `fast-uri` del workspace a `>= 3.1.6` o eliminarlo del árbol.
- Elegir la remediación correcta según la naturaleza de la dependencia, no aplicar una receta única.
- Probar que el bump de `aws-cdk-lib` no altera la infraestructura sintetizada.
- Dejar el procedimiento escrito para el próximo advisory.

**Non-Goals:**
- Los repos del reporte que no son submódulos acá: `titvo-task-cli-files-aws`, `titvo-task-status-aws`,
  `titvo-auth-setup-aws`.
- Actualizar dependencias ajenas a la cadena de `fast-uri`, salvo `aws-cdk` CLI, que entra por
  compatibilidad de cloud assembly schema (ver D7).
- Automatizar `npm audit` en CI o adoptar Renovate.
- Migrar `docker/cdk/entrypoint.sh` de `npm install` a `npm ci`, aunque se documenta el hallazgo (ver
  riesgos).

## Decisions

### D1 — Grupo A: `npm update fast-uri`, sin `overrides` por defecto

`ajv@8.17.1` declara `fast-uri: ^3.0.1`, así que 3.1.6 entra dentro del rango ya declarado y basta
regenerar el lockfile. Se prefiere esto a `overrides` porque no introduce un pin permanente que
después hay que recordar quitar, y no altera `package.json`.

*Alternativas descartadas:* (a) `overrides: {"fast-uri": "^3.1.6"}` de entrada — añade deuda de
mantenimiento innecesaria mientras el rango upstream ya admita el parche; queda como plan B si el
lockfile regenerado vuelve a caer en el rango vulnerable. (b) `rm -rf node_modules package-lock.json &&
npm install` — regenera el árbol completo y mete ruido de versiones no relacionadas en el diff.
(c) `npm audit fix` — actúa sobre todo el árbol a la vez y no se puede acotar a `fast-uri`.

### D2 — Grupo B: subir `aws-cdk-lib` a `>= 2.261.0`, no parchear el bundle

`npm overrides` **no** reescribe dependencias con `inBundle: true`: el árbol viene resuelto dentro del
tarball publicado y npm lo instala tal cual. Verificado contra el registry: `aws-cdk-lib@2.261.0`
eliminó `table` de sus `dependencies`, y `table` era quien arrastraba `ajv` → `fast-uri`. La inspección
del tarball de 2.268.0 confirma que su `node_modules/` ya no incluye `fast-uri`, `ajv` ni `table`. El
upgrade por lo tanto **elimina** la copia vulnerable en vez de parchearla — es un fix estructural, no
un pin.

Se fija una versión exacta (misma convención que el `2.215.0` actual) coherente en los seis paquetes,
para que un `synth` no dependa de cuándo se corrió `npm install`.

*Alternativas descartadas:* (a) `overrides` sobre `fast-uri` — no funciona en bundled deps y daría una
falsa sensación de arreglo. (b) Parchear `node_modules` con `patch-package` — no se versiona el
resultado en el lock y la alerta de Dependabot sigue abierta porque lee el lockfile. (c) Descartar la
alerta como falso positivo por ser build-time — cierra el síntoma pero deja código vulnerable en el
árbol, y la ruta ya tiene un upgrade limpio disponible.

### D3 — Bump mínimo por sobre "última versión"

Se apunta a la primera versión que resuelve el problema (2.261.0) en lugar de saltar directo a la
última, para acotar la superficie de cambio de un salto que ya es de ~46 versiones menores. Si durante
la validación aparece un bug propio de 2.261.0, se sube al siguiente parche disponible.

### D4 — Validación por diff de plantilla sintetizada

Antes de tocar `aws-cdk-lib` se captura `cdk synth` de cada app afectada con 2.215.0; después del bump
se vuelve a sintetizar y se comparan. Es la única verificación que cubre el riesgo real de este cambio:
que CDK 2.26x genere recursos distintos. Los tests unitarios de los paquetes no ejercitan la síntesis,
así que no sustituyen esta comprobación.

### D5 — `constructs` sube junto con CDK

`aws-cdk-lib@2.26x` declara `peerDependencies.constructs: ^10.5.0` y el lock actual tiene 10.4.2. El
`^10.0.0` declarado en `package.json` ya admite 10.5.x, así que se resuelve al regenerar el lock sin
tocar el rango.

### D6 — Un commit por submódulo, punteros al final

Cada submódulo recibe su commit `fix(deps): ...` (conventional commits, mensaje en español) y al final
`titvo-dev` recibe un commit que mueve los seis punteros. Así cada repo cierra sus propias alertas de
Dependabot de forma independiente y el historial queda legible.

### D7 — Alinear el CLI `aws-cdk` con el nuevo cloud assembly schema

`aws-cdk-lib@2.215.0` depende de `@aws-cdk/cloud-assembly-schema: ^48.6.0`; `2.261.0` salta a
`^54.0.0`. El CLI de CDK valida la versión de schema del cloud assembly que lee: un CLI viejo rechaza
un assembly nuevo con *"This CDK CLI is not compatible with the CDK library used by your application"*.
El `aws-cdk` pineado en `devDependencies` es **2.1029.3 (2025-09-24)**, anterior a `aws-cdk-lib@2.261.0`
(2026-07-02), así que es muy probable que lo rechace.

Atenuante importante: `docker/cdk/Dockerfile:5` hace `npm install -g aws-cdk-local aws-cdk` **sin
pin**, por lo que el CLI que realmente ejecuta el flujo de `docker compose up cdk` es el más reciente
al momento de buildear la imagen — es decir, va *adelante* del lib, que es la dirección compatible. El
`aws-cdk` de `devDependencies` sólo se ejerce si alguien corre `npx cdk synth` fuera del contenedor.

Decisión: subir `aws-cdk` en `devDependencies` a una versión igual o posterior a la fecha de release
del `aws-cdk-lib` objetivo, de modo que el CLI local y el del contenedor queden en la misma dirección
de compatibilidad. No se pinea el CLI del Dockerfile en este cambio (queda como hallazgo documentado).

*Alternativas descartadas:* (a) Dejar el CLI en 2.1029.3 — deja `npx cdk synth` roto para quien
trabaje fuera de docker, que es justamente el comando de la validación D4. (b) Eliminar `aws-cdk` de
`devDependencies` y depender sólo del CLI global del contenedor — más limpio conceptualmente, pero
saca la capacidad de sintetizar en el host y hace la validación D4 dependiente de docker.

## Risks / Trade-offs

- **Incompatibilidad CLI ↔ lib por salto de cloud assembly schema `^48.6.0` → `^54.0.0`** → D7: se sube
  el `aws-cdk` de `devDependencies` junto con el lib. Es el modo de falla más probable de todo el
  cambio, y se manifiesta como error explícito del CLI, no como corrupción silenciosa.
- **El salto 2.215.0 → 2.261.0 cambia recursos sintetizados** → D4: diff de plantilla obligatorio por
  app antes de cerrar. Se **espera** diff distinto de cero (CDK bumpea los runtimes de las Lambdas de
  custom resources y defaults de propiedades entre versiones); el criterio no es diff vacío sino que
  ninguna diferencia quede sin explicar.
- **Cambios de logical ID al reconstruir stacks** → radio de daño acotado: los stacks CDK son sólo de
  LocalStack y efímeros; producción va por Terragrunt. Ningún recurso de AWS real se reemplaza.
- **Errores de compilación TypeScript por deprecaciones o cambios en L1 constructs** → se detectan en
  `npm run build` antes de cualquier síntesis o deploy; se corre en las 6 apps, no en una muestra.
- **`localstack/app` es el bootstrap del entorno de desarrollo; si su síntesis se rompe, se cae todo el
  ambiente local** → se deja de último en el orden de implementación y se valida con un `docker compose
  up cdk` completo, no sólo con `synth`.
- **Los seis paquetes del Grupo B quedan pineados a una versión exacta de CDK** → es la convención ya
  vigente en el repo; el costo es que el próximo bump también será manual.
- **Regenerar lockfiles arrastra actualizaciones de parche colaterales** → se acota el comando a
  `npm update fast-uri` en el Grupo A y se revisa el diff del lock antes de commitear.
- **`docker/cdk/entrypoint.sh:14` corre `npm install` y no `npm ci`, y el Dockerfile instala el CLI sin
  pin** → el lockfile remediado no se respeta estrictamente dentro del contenedor y la imagen no es
  reproducible. No invalida el fix (Dependabot audita el lockfile versionado, no el contenedor), pero
  queda documentado como hallazgo para un cambio posterior.
- **La alerta puede reaparecer si `ajv` publica un rango más laxo o `aws-cdk-lib` vuelve a bundlear
  `fast-uri`** → queda la guía documentada y el comando de auditoría de lockfiles para detectarlo.
- **Tres repos del reporte quedan sin arreglar y las alertas siguen abiertas a nivel de la org** → se
  declara explícitamente en Non-goals y se deja una tarea de seguimiento que registre el pendiente.

## Migration Plan

1. Capturar baseline: `cdk synth` de las seis apps del Grupo B con `aws-cdk-lib@2.215.0`.
2. Grupo A (bajo riesgo, sin dependencias entre sí): `npm update fast-uri` + verificar lock + tests.
3. Alinear el CLI `aws-cdk` en los seis paquetes del Grupo B (D7), antes del bump del lib, para que la
   validación por síntesis del paso siguiente corra con un CLI compatible.
4. Grupo B en los cinco `cdklocal/`: bump, regenerar lock, `build`, `synth`, diff contra baseline.
5. Grupo B en `localstack/app` al final, con `docker compose up cdk` como validación de extremo a extremo.
6. Auditoría final de lockfiles + documentación.
7. Commits por submódulo y actualización de punteros en `titvo-dev`.

**Rollback:** cada paso es un commit aislado de dependencias; revertir es `git revert` del commit del
submódulo y regenerar el lock. No hay migración de datos ni de estado, y ningún recurso desplegado en
AWS real cambia, porque CDK acá sólo alimenta LocalStack.

## Open Questions

- ¿Se abre issue de seguimiento en los tres repos fuera de alcance, o se los agenda como un change
  aparte en este workspace?
- ¿Se pinea el CLI en `docker/cdk/Dockerfile` y se migra `entrypoint.sh` a `npm ci` en un cambio
  aparte, para que la imagen del contenedor sea reproducible y respete el lockfile remediado?

**Resueltas:**
- ~~¿Hay algún pipeline que instale con `npm ci` y una versión de Node distinta?~~ No. CI usa Node 22 y
  los Dockerfiles Node 24; ambos satisfacen `engines.node >= 20.0.0`.
