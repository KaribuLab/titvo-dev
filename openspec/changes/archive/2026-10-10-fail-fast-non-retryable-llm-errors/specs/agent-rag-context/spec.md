## ADDED Requirements

### Requirement: Un fallo no recuperable del proveedor de embeddings no se repite durante el scan

Cuando la generación del embedding de consulta falla con un error no recuperable (sin créditos o
cuota, 401, 403, 404, 400), el adapter RAG SHALL registrar un único `WARNING` con la causa y SHALL
responder sin contexto RAG a todas las consultas restantes del mismo scan sin volver a llamar al
proveedor de embeddings. El análisis SHALL continuar sin RAG. `configure()` SHALL limpiar ese
estado para el siguiente scan.

#### Scenario: Sin créditos en el primer embedding

- **WHEN** el primer `search` del scan falla con `429 insufficient_quota` y el nodo RAG consulta 10
  archivos
- **THEN** el proveedor de embeddings se llama exactamente una vez, `rag_chunks` es `[]` y los
  expertos se ejecutan

#### Scenario: Error transitorio no deshabilita el RAG

- **WHEN** un `search` falla con timeout
- **THEN** el siguiente `search` del mismo scan vuelve a llamar al proveedor de embeddings
