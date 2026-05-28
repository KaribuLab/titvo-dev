## Why

El agente analiza commits sin contexto del código base completo del repositorio. Integrar el RAG indexer permite que el agente cuente con comprensión semántica del código existente (vectorizado por rama), mejorando la calidad del análisis de seguridad más allá de los archivos del commit puntual.

## What Changes

- **`src/api/task/trigger`**: recibe `branch` junto al `commit_sha`; todos los strategies (GitHub, Bitbucket, CLI) propagan el campo `branch`; se guarda `branch` en la tabla DynamoDB de scans.
- **`src/agent`**: antes de iniciar el grafo LangGraph, verifica si la rama ya está indexada en el vector store; si no lo está, dispara el rag-indexer en modo full (batch) y hace polling hasta que termine. Al finalizar el análisis, verifica si el commit ya está indexado; si no lo está, dispara el rag-indexer en modo delta (fire-and-forget). Los nodos del agente reciben el contexto del vector store como background, obteniendo los archivos del commit exclusivamente via MCP.
- **`src/agent` (nuevo servicio Python)**: implementación de `BatchService` equivalente al de TypeScript, con soporte para entorno local (HTTP hacia batch-runner) y AWS Batch.

## Capabilities

### New Capabilities

- `scan-branch-propagation`: Captura y propagación del campo `branch` desde el trigger API hasta el agente a través del job batch y la tabla DynamoDB de scans.
- `rag-pre-scan-full-indexing`: Verificación de índice RAG por rama antes del análisis; indexación full bloqueante con polling si la rama no está indexada.
- `rag-post-scan-delta-indexing`: Disparo asíncrono (fire-and-forget) del rag-indexer en modo delta al finalizar el análisis.
- `agent-batch-service`: Servicio Python para lanzar jobs batch (local vía HTTP y AWS Batch), equivalente al `BatchService` de TypeScript.
- `agent-rag-context`: Instrucción al agente de usar el índice vectorial como contexto de código base sin solapar con los archivos del commit (obtenidos por MCP).

### Modified Capabilities

- `langgraph-orchestration`: El grafo LangGraph incorpora un paso pre-análisis (verificación/indexación RAG) que no forma parte del flujo de nodos agénticos existentes.

## Impact

- **`src/api/task/trigger`**: `github.strategy.ts`, `bitbucket.strategy.ts`, `cli.strategy.ts`, `task.service.ts`, `task.entity.ts` (DynamoDB schema), `task.dynamo.ts`.
- **`src/agent`**: nuevo módulo `rag_indexer_trigger/` con `BatchService` en Python; `analyse_code_use_case.py`; `workflow.py` (LangGraph); `task_entity.py` (propiedad `branch`); prompts del agente.
- **DynamoDB**: nuevo campo `branch` en la tabla de scans.
- **Variables de entorno del job batch del agente**: `TITVO_BRANCH`, `TITVO_RAG_INDEXER_JOB_QUEUE`, `TITVO_RAG_INDEXER_JOB_DEFINITION`, `TITVO_BATCH_RUNNER_URL`.

## Non-goals

- No se implementa lógica de autenticación nueva para el vector store.
- No se modifica la lógica de chunking o embedding del rag-indexer.
- No se añade UI ni endpoint nuevo en la API para consultar el estado del índice RAG.
- No se implementa rollback del índice si falla la indexación full.
