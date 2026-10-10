# Spec: npm-advisory-remediation

## Purpose
Define how this workspace keeps its `package-lock.json` files free of dependencies with
known security advisories, distinguishing resolvable transitive dependencies from bundled
ones, and what verification is required before closing an alert.

## Requirements

### Requirement: Ningún lockfile resuelve `fast-uri` a una versión vulnerable
Todo `package-lock.json` versionado en este workspace y en sus submódulos MUST resolver `fast-uri` a
una versión `>= 3.1.6` o no contenerlo en absoluto. El rango `>= 3.0.0 < 3.1.6` está afectado por
CVE-2026-6322, CVE-2026-13676, CVE-2026-16221, CVE-2026-18446, CVE-2026-75899, CVE-2026-75931,
CVE-2026-75975 y CVE-2026-76172 (*host confusion* y SSRF, severidad high).

#### Scenario: Auditoría de los lockfiles del workspace
- **WHEN** se inspeccionan todas las entradas cuya clave termina en `node_modules/fast-uri` en los
  `package-lock.json` versionados, excluyendo `node_modules/` y `.opencode/`
- **THEN** cada entrada encontrada declara `version >= 3.1.6`, y no queda ninguna entrada con 3.0.6 ni
  con 3.1.0

#### Scenario: Alertas de Dependabot cerradas
- **WHEN** se revisan las alertas de Dependabot de `fast-uri` en los repos que son submódulos de este
  workspace, después de mergear los cambios de dependencias
- **THEN** ninguna queda en estado open para un lockfile de este workspace

### Requirement: Las dependencias transitivas resolubles se remedian sin cambiar `package.json`
Cuando la dependencia vulnerable es transitiva y el rango declarado por su dependiente ya admite la
versión parcheada, la remediación MUST hacerse regenerando el lockfile, sin modificar `package.json`.
Un bloque `overrides` MUST agregarse únicamente si el lockfile regenerado vuelve a resolver una
versión vulnerable, y en ese caso MUST documentarse por qué fue necesario.

#### Scenario: `fast-uri` transitivo vía `ajv`
- **WHEN** se remedia un lockfile donde `fast-uri` entra por `ajv@8.17.1`, que declara `fast-uri: ^3.0.1`
- **THEN** el lockfile queda con `fast-uri >= 3.1.6` y el `package.json` del paquete no registra
  cambios en `dependencies` ni en `devDependencies`

#### Scenario: `overrides` como último recurso
- **WHEN** tras regenerar el lockfile la versión resuelta sigue dentro del rango vulnerable
- **THEN** se agrega `overrides` con el rango parcheado y se registra la justificación en el diseño
  del cambio

### Requirement: Las dependencias bundleadas se remedian actualizando el paquete que las empaqueta
Una dependencia marcada `"inBundle": true` en el lockfile MUST NOT remediarse con `npm overrides`,
porque npm no reescribe el árbol bundleado publicado en el tarball. La remediación MUST ser actualizar
el paquete contenedor a una versión que empaquete la dependencia parcheada o que ya no la empaquete.

#### Scenario: `fast-uri` bundleado dentro de `aws-cdk-lib`
- **WHEN** un lockfile declara `node_modules/aws-cdk-lib/node_modules/fast-uri` con `inBundle: true`
- **THEN** la remediación eleva `aws-cdk-lib` a `>= 2.261.0`, versión que eliminó la dependencia
  `table` (`table` → `ajv` → `fast-uri`), y el lockfile regenerado ya no contiene ninguna ruta
  `aws-cdk-lib/node_modules/fast-uri`

#### Scenario: Compatibilidad del entorno con la versión objetivo
- **WHEN** se eleva `aws-cdk-lib` a `>= 2.261.0`
- **THEN** el runtime de Node del entorno satisface `engines.node >= 20.0.0` y `constructs` resuelve
  a una versión que satisface el peer `^10.5.0`

#### Scenario: Compatibilidad del toolchain con el cloud assembly schema
- **WHEN** la versión objetivo del paquete contenedor eleva la versión del cloud assembly schema que
  emite, como el salto de `@aws-cdk/cloud-assembly-schema` de `^48.6.0` a `^54.0.0`
- **THEN** el CLI que lee ese assembly se actualiza a una versión que soporta el schema nuevo, y la
  síntesis no falla con un error de incompatibilidad entre CLI y librería

### Requirement: El upgrade de infraestructura se valida por equivalencia de plantilla
Un upgrade de `aws-cdk-lib` motivado por seguridad MUST verificarse comparando la plantilla
CloudFormation sintetizada antes y después del cambio, en cada aplicación CDK afectada. Cualquier
diferencia MUST quedar explicada antes de dar el cambio por cerrado. El criterio de aceptación NO es
un diff vacío, sino que ninguna diferencia quede sin justificar.

#### Scenario: Diferencias esperables aceptadas
- **WHEN** se ejecuta `cdk synth` sobre una app afectada con la versión anterior y con la nueva
- **THEN** las diferencias limitadas a metadata de versión de CDK y a runtimes de las funciones Lambda
  de custom resources se aceptan como esperables, y quedan registradas como tales

#### Scenario: Diferencia no trivial detectada
- **WHEN** la comparación revela un cambio en un recurso de negocio o en una propiedad funcional de un
  recurso
- **THEN** el cambio no se cierra hasta que la diferencia esté explicada y aceptada explícitamente

#### Scenario: Compilación previa a la síntesis
- **WHEN** se eleva la versión del paquete de infraestructura en una app afectada
- **THEN** la app compila sin errores antes de sintetizar, de modo que las deprecaciones o cambios en
  constructs L1 se detecten en build y no en deploy

### Requirement: El procedimiento de remediación queda documentado
El workspace MUST documentar cómo diagnosticar y remediar un advisory de una dependencia transitiva
de npm, incluyendo cómo distinguir una dependencia resoluble de una bundleada y cómo verificar el
resultado, de modo que la siguiente alerta no exija repetir la investigación.

#### Scenario: Documentación disponible para el siguiente advisory
- **WHEN** alguien recibe una nueva alerta de Dependabot sobre una dependencia transitiva en este
  workspace
- **THEN** encuentra en `docs/` el procedimiento con el criterio de decisión resoluble vs bundleada,
  el comando de auditoría de lockfiles y el paso de verificación por síntesis
