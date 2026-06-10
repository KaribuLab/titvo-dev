## MODIFIED Requirements

### Requirement: Agente verifica si la rama está indexada antes de analizar
Antes de ejecutar el grafo LangGraph, `AnalyseCodeUseCase` SHALL verificar el estado del índice RAG usando el port `IRagIndexStatusPort`. El campo `branch` es obligatorio; si no está presente el análisis SHALL fallar con error. En modo `commit`, el agente SHALL conservar el comportamiento de verificar si existe un índice RAG para `(repository_url, branch)`. En modo `full`, el agente SHALL verificar además si el commit/ref objetivo está indexado para `(repository_url, branch, commit_hash)` y SHALL esperar indexación cuando el índice no esté fresco para ese commit/ref.

#### Scenario: Rama ya indexada en modo commit
- **WHEN** `scan_mode` es `commit` y `IRagIndexStatusPort.is_indexed(repo_url, branch)` retorna `True`
- **THEN** el agente continúa directamente a ejecutar el grafo LangGraph sin disparar indexación full

#### Scenario: Rama no indexada en modo commit
- **WHEN** `scan_mode` es `commit` y `IRagIndexStatusPort.is_indexed(repo_url, branch)` retorna `False`
- **THEN** el agente dispara la indexación full via `RagIndexerBatchTrigger.trigger_full` y hace polling bloqueante hasta que el job termine

#### Scenario: Full scan con commit ya indexado
- **WHEN** `scan_mode` es `full` y `IRagIndexStatusPort.is_commit_indexed(repo_url, branch, commit_hash)` retorna `True`
- **THEN** el agente continúa a ejecutar el grafo LangGraph con RAG fresco para el commit/ref objetivo

#### Scenario: Full scan con RAG stale
- **WHEN** `scan_mode` es `full` y `IRagIndexStatusPort.is_commit_indexed(repo_url, branch, commit_hash)` retorna `False`
- **THEN** el agente dispara indexación y espera hasta que el commit/ref objetivo quede indexado antes de ejecutar el grafo LangGraph

#### Scenario: Branch ausente
- **WHEN** `task.branch` es `None` o vacío
- **THEN** `AnalyseCodeUseCase` lanza una excepción y el análisis falla con error
