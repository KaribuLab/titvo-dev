# rag-post-scan-delta-indexing Specification

## Purpose

Indexación delta del rag-indexer disparada por el agente al finalizar el análisis, con idempotencia por commit y comportamiento fire-and-forget.

## Requirements

### Requirement: Agente dispara indexación delta al finalizar el análisis
Después de que `self.agent.invoke()` retorna exitosamente, `AnalyseCodeUseCase` SHALL disparar la indexación delta del rag-indexer vía `RagIndexerBatchTrigger.trigger_delta` de forma fire-and-forget, **solo si el commit aún no está indexado**.

#### Scenario: Delta disparado con branch y commit_hash
- **WHEN** el análisis del agente termina (con cualquier status: COMPLETED, FAILED, WARNING) y `IRagIndexStatusPort.is_commit_indexed(repo_url, branch, commit_hash)` retorna `False`
- **THEN** se llama `trigger_delta(repo_url, branch, commit_hash)` con los datos del task

#### Scenario: Delta omitido si el commit ya está indexado
- **WHEN** el análisis del agente termina y `IRagIndexStatusPort.is_commit_indexed(repo_url, branch, commit_hash)` retorna `True`
- **THEN** el agente NO dispara `trigger_delta`, loguea que el commit ya está indexado y continúa el flujo normalmente

#### Scenario: Delta no bloquea el resultado del análisis
- **WHEN** se dispara el delta
- **THEN** el resultado del análisis se retorna al llamador sin esperar que el job delta termine

#### Scenario: Error al disparar delta no interrumpe el flujo
- **WHEN** `trigger_delta` lanza una excepción (ej. AWS no disponible)
- **THEN** el agente loguea el error pero retorna el resultado del análisis normalmente

#### Scenario: Error al verificar idempotencia no interrumpe el flujo
- **WHEN** `is_commit_indexed` lanza una excepción (ej. S3 no disponible)
- **THEN** el agente loguea el error y NO dispara el delta (fail-safe: evitar jobs duplicados ante incertidumbre)

### Requirement: Idempotencia del delta en el agente
Antes de disparar el delta, el agente SHALL verificar si el commit del scan ya fue indexado para esa rama, usando el mismo criterio de paths S3 que el rag-indexer.

#### Scenario: Commit indexado vía meta.json por commit
- **WHEN** existe el objeto `{bucket}/{repo_slug}/branches/{branch}/{commit_sha}/meta.json` en S3
- **THEN** `is_commit_indexed` retorna `True`

#### Scenario: Commit no indexado
- **WHEN** no existe el objeto `{bucket}/{repo_slug}/branches/{branch}/{commit_sha}/meta.json` en S3
- **THEN** `is_commit_indexed` retorna `False`

#### Scenario: rag-indexer mantiene idempotencia como defensa en profundidad
- **WHEN** el agente dispara un delta y el rag-indexer recibe un commit que ya es el `latest` de la rama
- **THEN** el rag-indexer omite la indexación (comportamiento existente en `_execute_delta`) sin error
