## 1. rag-indexer: Puerto y adaptador S3

- [x] 1.1 Actualizar el puerto `ArtifactStorePort` para que `branch: str` sea parámetro obligatorio en `upload_db`, `get_latest_commit_sha` y `download_latest_db`
- [x] 1.2 Actualizar `S3ArtifactStoreAdapter` para construir el prefijo `{repo}/branches/{branch}/latest/` usando el `branch` recibido (sin fallback)
- [x] 1.3 Actualizar tests unitarios del adaptador S3: verificar prefijo correcto con branch válido; verificar que ausencia de branch lanza error
- [x] 1.4 Ejecutar ruff sobre los archivos modificados y corregir todo lo que reporte

## 2. rag-indexer: Use case y main.py

- [x] 2.1 Actualizar `main.py`: `TITVO_BRANCH` es obligatorio; si solo viene `TITVO_COMMIT_SHA` sin `TITVO_BRANCH` → error explícito; si vienen ambos → modo delta; si solo `TITVO_BRANCH` → modo full
- [x] 2.2 Actualizar `IndexRepositoryUseCase.execute()` para recibir y propagar `branch` obligatorio a `_execute_full` y `_execute_delta`
- [x] 2.3 Eliminar el fallback interno delta→full cuando no hay índice previo en S3 — si no hay `latest/meta.json` para la rama, delta debe fallar con error explícito
- [x] 2.4 Actualizar tests unitarios del use case: (a) delta con branch+SHA, (b) full con branch, (c) solo SHA sin branch → error, (d) delta sin índice previo → error (sin fallback)
- [x] 2.5 Ejecutar ruff sobre los archivos modificados y corregir todo lo que reporte

## 3. Validación de librerías (usar find-docs / ctx7)

- [x] 3.1 Revisar `pyproject.toml` del rag-indexer e identificar la versión exacta de cada librería usada en los archivos modificados (`boto3`, `botocore`, y cualquier otra)
- [x] 3.2 Usar `ctx7` para resolver y consultar la documentación actualizada de `boto3`: verificar que `head_object`, `get_object`, `put_object` y el manejo de `ClientError` (NoSuchKey / 404) corresponden a la versión instalada y no están deprecados
- [x] 3.3 Usar `ctx7` para consultar cualquier otra librería que se modifique o importe en los archivos tocados; si un método o patrón no aparece en la doc actual, buscar el reemplazo antes de usarlo

## 4. Tests

- [x] 4.1 Ejecutar la suite de tests unitarios completa del rag-indexer y verificar que todos pasan
- [x] 4.2 Corregir cualquier test roto por los cambios de firma (branch obligatorio)

## 5. Documentación

- [x] 5.1 Actualizar `docs/rag-indexer.md`: reemplazar descripción del esquema S3 con el nuevo prefijo por rama
- [x] 5.2 Agregar diagrama de secuencia (mermaid) para el flujo full-index con branch
- [x] 5.3 Agregar diagrama de secuencia (mermaid) para el flujo delta-index con branch + SHA
- [x] 5.4 Actualizar `src/rag-indexer/rag-indexer.http`: reemplazar ejemplos de delta/full con los nuevos que incluyen `TITVO_BRANCH` siempre

## DIFERIDO — Iteración 2 (flujo task→agent)

> No implementar en esta iteración.

- [ ] D.1 Verificación S3 pre-análisis en `src/api`
- [ ] D.2 Full-index automático si falta índice de rama
- [ ] D.3 `is_delta` + `delta_paths` en estado LangGraph (`src/agent`)
- [ ] D.4 Precedencia MCP sobre RAG en nodos experto
