## ADDED Requirements

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
El agente SHALL hacer polling del job de indexación full cada 10 segundos con un máximo de 60 intentos (10 minutos).

#### Scenario: Indexación completa antes del timeout
- **WHEN** el job de indexación termina con status `SUCCEEDED` dentro del límite de intentos
- **THEN** el agente continúa con el análisis

#### Scenario: Indexación falla
- **WHEN** el job de indexación termina con status `FAILED`
- **THEN** `AnalyseCodeUseCase` lanza una excepción y el análisis falla con error

#### Scenario: Timeout de polling excedido
- **WHEN** el job no termina dentro de los 60 intentos (10 minutos)
- **THEN** `AnalyseCodeUseCase` lanza una excepción con el jobId y el análisis falla con error

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
