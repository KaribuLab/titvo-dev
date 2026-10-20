## Why

Dependabot reporta alertas abiertas por `fast-uri` en los `package-lock.json` de los repos de Titvo.
La librería acumula 8 advisories **high** (CVE-2026-6322, 13676, 16221, 18446, 75899, 75931, 75975,
76172) de *host confusion* y *SSRF* por normalización incorrecta de autoridad/IDN; el rango 3.x
afectado es `>= 3.0.0 < 3.1.6`. En este workspace hay 12 lockfiles con `fast-uri` 3.0.6 o 3.1.0, es
decir todos vulnerables. Siendo Titvo un producto de ciberseguridad, no podemos arrastrar alertas
high abiertas en nuestro propio árbol de dependencias.

## What Changes

- **Grupo A — `fast-uri` transitivo (dev-only, vía `ajv`)**: actualizar a `>= 3.1.6` en los 6
  lockfiles raíz de `src/api/task/trigger`, `src/mcp/git-commit-files`,
  `src/mcp/bitbucket-code-insights`, `src/mcp/issue-report`, `src/mcp/gateway` y
  `src/mcp/github-issue`. `ajv@8.17.1` declara `fast-uri: ^3.0.1`, así que se resuelve sin tocar
  `package.json`; se agrega un `overrides` sólo si el lock vuelve a caer a una versión vulnerable.
- **Grupo B — `fast-uri` *bundled* dentro de `aws-cdk-lib@2.215.0`**: subir `aws-cdk-lib` a
  `>= 2.261.0` en los 5 `cdklocal/` y en `localstack/app`. `npm overrides` no reescribe dependencias
  bundleadas (`inBundle: true`), y 2.261.0 eliminó la dependencia `table` que arrastraba
  `ajv` → `fast-uri`, por lo que el upgrade borra la copia vulnerable en lugar de parchearla.
- Verificación de que `cdk synth` produce plantillas equivalentes antes/después del bump de CDK.
- Documentar el procedimiento de remediación para que la próxima alerta se resuelva sin re-investigar.

## Capabilities

### New Capabilities
- `npm-advisory-remediation`: cómo el workspace mantiene sus lockfiles libres de dependencias
  transitivas con advisories conocidos, distinguiendo dependencias resolubles de dependencias
  bundleadas, y qué verificación se exige antes de cerrar una alerta.

### Modified Capabilities
<!-- Ninguna: no cambia el comportamiento especificado de ninguna capability existente. -->

## Impact

- **Lockfiles (12)**: 6 raíz del Grupo A + `src/{api/task/trigger,mcp/git-commit-files,mcp/bitbucket-code-insights,mcp/issue-report,mcp/github-issue}/cdklocal` y `localstack/app`.
- **`package.json` (6)**: sólo los del Grupo B, para el pin de `aws-cdk-lib`.
- **CDK**: salto 2.215.0 → 2.26x. `engines` exige Node `>= 20` (CI usa Node 22 y los Dockerfiles Node
  24, ambos cumplen), `peerDependencies.constructs` sube a `^10.5.0` desde el `10.4.2` actual, y el
  cloud assembly schema salta de `^48.6.0` a `^54.0.0`, lo que arrastra al CLI `aws-cdk`.
- **Alcance de CDK**: `cdklocal/` y `localstack/app` sintetizan **sólo** para LocalStack; producción se
  despliega con Terragrunt vía `aws/` y `.github/workflows/deploy-to-aws.yml`. Ningún recurso de AWS
  real se ve afectado por este cambio.
- **Exposición real**: baja. Todas las instancias del Grupo A están marcadas `"dev": true` y las del
  Grupo B viven en tooling de síntesis, no en el bundle de runtime de Lambda. El objetivo es cerrar
  las alertas, no contener un incidente activo.
- **Submódulos**: los cambios se commitean en cada repo submódulo y luego se actualizan los punteros
  en `titvo-dev`.
- **Docs**: `docs/dev-env-structure.md` y `docs/troubleshooting.md`.

## Non-goals

- No se remedian los repos del reporte de Dependabot que **no** son submódulos de este workspace:
  `titvo-task-cli-files-aws`, `titvo-task-status-aws` y `titvo-auth-setup-aws`. Requieren el mismo
  tratamiento en sus propios repos.
- No se actualiza ninguna dependencia que no participe en la cadena de `fast-uri`, con **una
  excepción**: `aws-cdk` (CLI) queda dentro del alcance porque el bump de `aws-cdk-lib` sube el cloud
  assembly schema de `^48.6.0` a `^54.0.0` y el CLI pineado en `devDependencies` (2.1029.3, sep-2025)
  es anterior a esa versión del schema.
- No se introduce Dependabot/Renovate automatizado ni gates de `npm audit` en CI.
- No se refactoriza código de aplicación: es un cambio exclusivamente de dependencias.
