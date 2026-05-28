# scan-branch-propagation Specification

## Purpose

Propagación del campo `branch` desde el trigger API hasta DynamoDB y el batch job del agente, para habilitar indexación RAG por rama.

## Requirements

### Requirement: Trigger API acepta campo branch por SCM
El trigger API SHALL aceptar el campo `branch` en el payload de cada fuente SCM:
- GitHub: campo `github_branch` (string, requerido).
- Bitbucket: campo `bitbucket_branch` (string, requerido).
- CLI: campo `branch` (string, requerido).
Cada strategy SHALL validar que `branch` esté presente y lanzar error si falta.

#### Scenario: GitHub trigger con branch válido
- **WHEN** se recibe un payload GitHub con `github_branch: "main"`
- **THEN** el strategy retorna los args incluyendo `branch: "main"`

#### Scenario: GitHub trigger sin branch
- **WHEN** se recibe un payload GitHub sin el campo `github_branch`
- **THEN** el trigger retorna error 400 con mensaje descriptivo

#### Scenario: Bitbucket trigger con branch válido
- **WHEN** se recibe un payload Bitbucket con `bitbucket_branch: "develop"`
- **THEN** el strategy retorna los args incluyendo `branch: "develop"`

#### Scenario: CLI trigger con branch válido
- **WHEN** se recibe un payload CLI con `branch: "feature/my-feature"`
- **THEN** el strategy retorna los args incluyendo `branch: "feature/my-feature"`

### Requirement: Branch se guarda en DynamoDB como campo top-level
La tabla DynamoDB de scans SHALL almacenar el campo `branch` como atributo de primer nivel (no dentro de `args`).

#### Scenario: Scan creado con branch
- **WHEN** se crea un nuevo scan en DynamoDB
- **THEN** el item contiene el campo `branch` con el valor recibido del strategy

#### Scenario: Agente lee branch desde DynamoDB
- **WHEN** el agente carga la tarea desde DynamoDB por `task_id`
- **THEN** `task.branch` contiene la rama correcta

### Requirement: Branch se propaga como variable de entorno al batch job del agente
El trigger SHALL incluir `TITVO_BRANCH` en las variables de entorno del job batch del agente.

#### Scenario: Variables de entorno del job incluyen TITVO_BRANCH
- **WHEN** se lanza el job batch del agente
- **THEN** la variable de entorno `TITVO_BRANCH` contiene el valor de la rama del scan

#### Scenario: Variables de entorno en localstack incluyen TITVO_BRANCH
- **WHEN** se lanza el job batch en entorno localstack
- **THEN** el array de environment variables enviado al batch-runner incluye `TITVO_BRANCH`
