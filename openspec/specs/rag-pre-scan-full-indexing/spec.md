# rag-pre-scan-full-indexing Specification

## Purpose

Verificación e indexación full de la rama antes del análisis LangGraph, con polling bloqueante y port de dominio para estado del índice RAG.

## Requirements

### Requirement: Agente verifica si la rama está indexada antes de analizar
Antes de ejecutar el grafo LangGraph, `AnalyseCodeUseCase` SHALL verificar si existe un índice RAG para `(repository_url, branch)` usando el port `IRagIndexStatusPort`. El campo `branch` es obligatorio; si no está presente el análisis SHALL fallar con error.

#### Scenario: Rama ya indexada
- **WHEN** `IRagIndexStatusPort.is_indexed(repo_url, branch)` retorna `True`
- **THEN** el agente continúa directamente a ejecutar el grafo LangGraph sin disparar indexación

#### Scenario: Rama no indexada
- **WHEN** `IRagIndexStatusPort.is_indexed(repo_url, branch)` retorna `False`
- **THEN** el agente dispara la indexación full via `RagIndexerBatchTrigger.trigger_full` y hace polling bloqueante hasta que el job termine

#### Scenario: Branch ausente
- **WHEN** `task.branch` es `None` o vacío
- **THEN** `AnalyseCodeUseCase` lanza una excepción y el análisis falla con error

### Requirement: Polling bloqueante de indexación full con timeout
El agente SHALL consultar el job cada 10 segundos, acortando la última espera al tiempo restante, hasta el timeout configurado por job. El presupuesto SHALL medir tiempo transcurrido desde el inicio de la espera, incluyendo estados de cola y ejecución. SHALL aplicarse tanto a la indexación full inicial como al delta bloqueante de un full scan, sin máximo fijo de intentos.

#### Scenario: Indexación completa antes del timeout
- **WHEN** el job de indexación termina con status `SUCCEEDED` y se observa antes de vencer el plazo
- **THEN** el agente continúa con el análisis

#### Scenario: Indexación falla
- **WHEN** el job de indexación termina con status `FAILED` y se observa antes de vencer el plazo
- **THEN** el análisis falla con un error que identifica el job

#### Scenario: Timeout de polling excedido
- **WHEN** vence el plazo sin observar éxito ni fallo terminal
- **THEN** el agente lanza un error de timeout con job ID, repositorio, rama o commit, timeout configurado y tiempo transcurrido, y no inicia el análisis
- **AND** no cancela automáticamente el job de indexación

#### Scenario: Indexación supera el antiguo máximo de intentos
- **WHEN** el timeout es 1800 segundos y el job sigue RUNNING a los 600 segundos
- **THEN** el agente continúa esperando y acepta un éxito observado a los 900 segundos

#### Scenario: Presupuesto independiente por job
- **WHEN** un full scan espera primero la indexación inicial y luego un delta de actualización
- **THEN** cada espera recibe el timeout completo configurado

#### Scenario: Timeout menor al intervalo o no múltiplo de diez
- **WHEN** quedan menos de 10 segundos de presupuesto
- **THEN** la siguiente espera no excede el tiempo restante y no comienza otra consulta de estado una vez vencido el plazo

#### Scenario: Consulta de estado cruza el deadline
- **WHEN** una consulta iniciada dentro del plazo devuelve su resultado después de su vencimiento
- **THEN** el agente reconoce el timeout antes de aceptar ese resultado y no inicia el análisis

### Requirement: Port IRagIndexStatusPort abstrae la verificación del índice
El dominio del agente SHALL definir el port `IRagIndexStatusPort` con los métodos:
- `is_indexed(repository_url: str, branch: str) -> bool` — verifica si la rama tiene índice (pre-scan full).
- `is_commit_indexed(repository_url: str, branch: str, commit_sha: str) -> bool` — verifica si un commit específico ya fue indexado (post-scan delta idempotente).

#### Scenario: Adaptador S3 confirma índice existente
- **WHEN** existe el objeto `{bucket}/{repo_slug}/branches/{branch}/latest/meta.json` en S3
- **THEN** `is_indexed` retorna `True`

#### Scenario: Adaptador S3 confirma índice ausente
- **WHEN** no existe el objeto `{bucket}/{repo_slug}/branches/{branch}/latest/meta.json` en S3
- **THEN** `is_indexed` retorna `False`

#### Scenario: Adaptador S3 confirma commit indexado
- **WHEN** existe el objeto `{bucket}/{repo_slug}/branches/{branch}/{commit_sha}/meta.json` en S3
- **THEN** `is_commit_indexed` retorna `True`

#### Scenario: Adaptador S3 confirma commit no indexado
- **WHEN** no existe el objeto `{bucket}/{repo_slug}/branches/{branch}/{commit_sha}/meta.json` en S3
- **THEN** `is_commit_indexed` retorna `False`

### Requirement: CLI no indexa Git
CLI tasks SHALL bypass Git RAG pre-indexing until snapshot-scoped indexing is supported.

#### Scenario: Snapshot local
- **WHEN** the task source is CLI
- **THEN** no pre-scan Git RAG job is submitted

### Requirement: Timeout RAG configurado exclusivamente en tabla
Para scans Git, el agente SHALL leer `rag_indexing_timeout_seconds` de la tabla al iniciar el scan y mantener el presupuesto para sus esperas. Si falta o está vacío/solo espacios, SHALL usar 600 segundos y registrar el default. Un valor no vacío SHALL ser un número finito positivo de segundos, validado antes de enviar jobs. No SHALL existir override por variable de entorno.

#### Scenario: Valor válido
- **WHEN** la tabla contiene `parameter_id=rag_indexing_timeout_seconds` y `value="1800"`
- **THEN** cada espera bloqueante de ese scan utiliza 1800 segundos

#### Scenario: Valor decimal válido
- **WHEN** el valor es `" 2.5 "`
- **THEN** se interpreta como 2.5 segundos

#### Scenario: Parámetro ausente o vacío en configuración antigua
- **WHEN** falta el parámetro o contiene vacío o solo espacios
- **THEN** el scan Git utiliza 600 segundos por job y registra que usó el default

#### Scenario: Parámetro no vacío inválido
- **WHEN** el parámetro contiene texto no numérico, cero, negativo, NaN o infinito
- **THEN** el scan Git falla con un error de configuración que identifica la clave antes de enviar cualquier job de indexación

#### Scenario: Error al leer la tabla
- **WHEN** no se puede leer la configuración
- **THEN** el error se propaga sin sustituir el timeout por un valor local

#### Scenario: Cambio operativo sin despliegue
- **WHEN** se modifica el valor en la tabla entre dos scans
- **THEN** el siguiente scan utiliza el nuevo valor sin recompilar ni cambiar el entorno
- **AND** un scan ya iniciado conserva el valor leído

#### Scenario: Variable de entorno no sustituye la tabla
- **WHEN** existe una variable de entorno de timeout RAG con un valor distinto
- **THEN** el agente utiliza únicamente el valor válido de la tabla

#### Scenario: Snapshot CLI no requiere timeout RAG
- **WHEN** se inicia una tarea CLI y el parámetro falta o es inválido
- **THEN** la tarea no consulta ni valida ese parámetro y mantiene su bypass de indexación Git

### Requirement: Diagnóstico de la espera configurada
El agente SHALL registrar al iniciar cada espera el job ID y timeout efectivo y, durante el polling, el estado del job y tiempo transcurrido. El diagnóstico no SHALL presentar un límite fijo de 60 intentos.

#### Scenario: Job en ejecución
- **WHEN** una consulta devuelve RUNNING dentro del plazo
- **THEN** el log permite identificar el job, su estado, tiempo transcurrido y timeout efectivo

### Requirement: Inicialización del parámetro sin sobrescribir ajustes
El bootstrap local SHALL crear el parámetro con valor inicial `"600"` únicamente si no existe. La guía de despliegue SHALL explicar el default compatible de 600 segundos y cómo configurar un plazo operativo distinto en la tabla.

#### Scenario: Primera inicialización local
- **WHEN** se ejecuta el bootstrap con el parámetro ausente
- **THEN** se crea `rag_indexing_timeout_seconds` con `value="600"` como dato inicial editable

#### Scenario: Inicialización repetida
- **WHEN** se ejecuta el bootstrap y el parámetro ya contiene `"1800"`
- **THEN** se conserva `"1800"`
