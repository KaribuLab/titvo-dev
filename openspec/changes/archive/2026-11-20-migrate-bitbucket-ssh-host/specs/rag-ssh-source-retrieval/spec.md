# Spec Delta

## MODIFIED Requirements

### Requirement: Selección de proveedor y credencial SSH

El sistema SHALL aceptar URLs HTTPS y SCP SSH de GitHub y Bitbucket, SHALL validar el hostname exacto y SHALL desencriptar únicamente la llave privada del proveedor. Las entradas Bitbucket con `bitbucket.org` y las SCP con `ssh.bitbucket.org` SHALL producir el remoto `git@ssh.bitbucket.org:<workspace>/<repository>.git` sin modificar la URL de entrada usada como identidad de indexación.

#### Scenario: Repositorio GitHub por URL HTTPS
- **WHEN** `TITVO_REPO_URL` es `https://github.com/acme/service`
- **THEN** el sistema usa el remoto SSH de GitHub y el parámetro cifrado `github_ssh_private_key`

#### Scenario: Repositorio Bitbucket por URL SSH
- **WHEN** `TITVO_REPO_URL` es `git@bitbucket.org:acme/service.git`
- **THEN** el sistema usa `git@ssh.bitbucket.org:acme/service.git` y el parámetro cifrado `bitbucket_ssh_private_key`

#### Scenario: Repositorio Bitbucket por URL HTTPS
- **WHEN** `TITVO_REPO_URL` es `https://bitbucket.org/acme/service.git`
- **THEN** el sistema usa `git@ssh.bitbucket.org:acme/service.git` y mantiene la URL de entrada para los identificadores persistidos

#### Scenario: Nuevo hostname SSH de Bitbucket
- **WHEN** `TITVO_REPO_URL` es `git@ssh.bitbucket.org:acme/service.git`
- **THEN** el sistema usa ese remoto validado y `bitbucket_ssh_private_key`

#### Scenario: Host no soportado
- **WHEN** la URL no identifica exactamente `github.com`, `bitbucket.org` ni `ssh.bitbucket.org`, incluyendo sufijos engañosos como `ssh.bitbucket.org.example.com`
- **THEN** el sistema falla antes de desencriptar una llave o ejecutar Git

#### Scenario: Llave del proveedor ausente
- **WHEN** el parámetro SSH requerido no existe o está vacío
- **THEN** el sistema falla con un error que identifica el nombre del parámetro ausente y no intenta usar una API REST

### Requirement: Ejecución SSH no interactiva y verificada

El sistema MUST ejecutar Git sin shell, MUST impedir prompts interactivos y MUST verificar la identidad del endpoint SSH mediante host keys fijadas para GitHub y para `ssh.bitbucket.org` en Bitbucket.

#### Scenario: Ejecución normal
- **WHEN** el sistema invoca Git o SSH
- **THEN** usa argumentos estructurados, un entorno controlado, la llave temporal seleccionada, `BatchMode=yes` e `IdentitiesOnly=yes`

#### Scenario: Host key no coincide
- **WHEN** la identidad presentada por el endpoint no coincide con las host keys confiables
- **THEN** la conexión falla antes de transferir fuentes

#### Scenario: Autenticación requiere interacción
- **WHEN** la llave requiere passphrase o el servidor solicita una credencial interactiva
- **THEN** el job falla sin esperar entrada del usuario

#### Scenario: Confianza del nuevo hostname
- **WHEN** una operación Git contacta `ssh.bitbucket.org`
- **THEN** las host keys empaquetadas permiten verificar ese hostname con fingerprints oficiales de Atlassian y se mantiene `StrictHostKeyChecking=yes`
