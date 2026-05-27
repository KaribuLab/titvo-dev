## ADDED Requirements

### Requirement: Índice S3 segmentado por rama

El sistema SHALL almacenar y recuperar el índice RAG en S3 usando siempre el prefijo `{repo}/branches/{branch}/latest/`. `TITVO_BRANCH` es un parámetro obligatorio en todos los modos de operación.

#### Scenario: Full-index sube al prefijo de rama

- **WHEN** el indexer ejecuta en modo full con `TITVO_BRANCH=feature/my-pr`
- **THEN** el índice se sube a `{repo}/branches/feature/my-pr/latest/index.db` y `{repo}/branches/feature/my-pr/latest/meta.json`

#### Scenario: Delta-index lee el prefijo correcto de rama

- **WHEN** el indexer ejecuta en modo delta con `TITVO_COMMIT_SHA` y `TITVO_BRANCH=feature/my-pr`
- **THEN** el `latest/meta.json` leído para obtener el SHA base proviene de `{repo}/branches/feature/my-pr/latest/meta.json`

#### Scenario: Ejecución sin rama lanza error

- **WHEN** el indexer ejecuta sin `TITVO_BRANCH` (solo `TITVO_COMMIT_SHA` o ninguna variable de rama)
- **THEN** el sistema lanza `ValueError` indicando que `TITVO_BRANCH` es requerido

### Requirement: Verificación de índice existente por rama antes del análisis

El sistema SHALL, antes de disparar un análisis delta sobre un commit, verificar si existe `{repo}/branches/{branch}/latest/meta.json` en S3.

Si el objeto no existe, el sistema SHALL ejecutar primero un full-index de la rama usando el HEAD del repositorio hasta el commit analizado, y esperar su finalización exitosa antes de continuar con el análisis.

#### Scenario: Índice de rama existe

- **WHEN** se solicita analizar un commit de `feature/my-pr` y `{repo}/branches/feature/my-pr/latest/meta.json` existe en S3
- **THEN** el sistema procede directamente al análisis delta sin ejecutar un full-index adicional

#### Scenario: Índice de rama no existe

- **WHEN** se solicita analizar un commit de `feature/my-pr` y `{repo}/branches/feature/my-pr/latest/meta.json` no existe en S3
- **THEN** el sistema dispara un full-index para la rama `feature/my-pr`, espera su finalización exitosa, y solo entonces continúa con el análisis

#### Scenario: Full-index previo falla

- **WHEN** el full-index pre-análisis falla o se interrumpe
- **THEN** el análisis NO se ejecuta y el sistema reporta error indicando que el índice no pudo ser creado

### Requirement: El rag-indexer acepta rama en modo delta

El rag-indexer SHALL aceptar `TITVO_BRANCH` junto con `TITVO_COMMIT_SHA` en modo delta, usando la rama exclusivamente para determinar el prefijo S3 correcto, sin alterar el commit objetivo del análisis.

#### Scenario: Delta con rama y commit

- **WHEN** el indexer recibe `TITVO_COMMIT_SHA=abc123` y `TITVO_BRANCH=feature/my-pr`
- **THEN** ejecuta delta-index del commit `abc123` leyendo y escribiendo en `{repo}/branches/feature/my-pr/latest/`
