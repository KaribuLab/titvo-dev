## Why

Un proyecto debe poder analizarse desde su copia local sin pipeline ni acceso Git desde Titvo. El agente actual no consume los paquetes CLI existentes y el shrink global pierde contexto en fullscan.

## What Changes

- CLI Python con Rich/Typer: preview, fullscan, status y reporte JSON/HTML.
- Snapshot tar.gz con manifiesto de hashes, exclusiones y soporte de submódulos inicializados.
- Recuperación CLI por batch_id desde DynamoDB/S3, reutilizando el contrato existente.
- Batching por experto sin reducción proporcional, fallos explícitos y cobertura reportada.
- MiniStack simula S3/DynamoDB; Docker ejecuta realmente el mismo grafo LangGraph.
- RAG remoto omitido para CLI para no mezclar versiones.

## Capabilities

### New Capabilities
- `cli-snapshot-analysis`: selección local, envío, integridad y reporte.

### Modified Capabilities
- `langgraph-orchestration`: fuente CLI inyectable, lotes y cobertura incompleta.
- `agent-rag-context`: fuente CLI sin consulta MCP ni índice remoto.
- `rag-pre-scan-full-indexing`: CLI omite indexación Git.
- `rag-post-scan-delta-indexing`: CLI omite delta Git.

## Impact

Repos titvo-agent-aws y titvo-dev. El laboratorio usa S3/DynamoDB directamente y Docker, sin desplegar la API pública ni simular una ejecución Batch exitosa. Se mantienen las APIs existentes de Git.

## Non-goals

RAG sobre snapshots, rediseño de clasificación runtime, despliegue AWS, ejecución de código del proyecto, publicación de issues y envío del código real a IA en esta entrega.
