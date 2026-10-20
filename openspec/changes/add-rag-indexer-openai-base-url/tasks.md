# Tasks

Cada tarea está acotada a un máximo de dos horas.

## 1. Configuración y cliente de embeddings

- [ ] 1.1 Usar el skill `find-docs` para validar la documentación actualizada de las versiones instaladas de LangChain/OpenAI: argumento de URL base, precedencia, tokenización de modelos externos y transporte de pruebas. Verificar dejando referencias y la opción elegida en `design.md`.
- [ ] 1.2 Leer `embedding_base_url` con `get_value` junto al modelo en `src/rag-indexer/src/rag_indexer/infra/adapters/langchain_embedding_adapter.py`, normalizar espacios y pasar el argumento al cliente solo si hay valor; conservar validaciones, credencial y caché. Añadir comentarios/docstrings de propósito al archivo y funciones modificadas. Verificar mediante tests de constructor para URL personalizada, ausente, vacía y espacios.
- [ ] 1.3 Generar o actualizar tests unitarios en `src/rag-indexer/tests/unit/test_langchain_embedding_adapter.py` para propagación de errores de configuración, conservación de modelo/credencial, reutilización del cliente y lectura del nuevo valor en una nueva instancia. Ajustar los dobles de configuración afectados y verificar que los tests pasan.
- [ ] 1.4 Añadir una prueba de solicitud mediante transporte HTTP simulado para comprobar host, prefijo de ruta, modelo, credencial y payload compatible con un modelo externo; cubrir `embed` y `embed_iter` sin red externa. Aplicar el ajuste de envío de texto si la documentación verificada lo requiere y comprobar que la rama sin URL mantiene su comportamiento.

## 2. Verificación de regresiones

- [ ] 2.1 Ejecutar la suite unitaria del RAG indexer, incluyendo batching, reintentos y streaming; verificar resultado exitoso y registrar el comando y resultado.
- [ ] 2.2 Ejecutar el linter correspondiente según la configuración del componente sobre los archivos afectados, corregir los hallazgos y verificar que no haya errores.

## 3. Documentation

- [ ] 3.1 Actualizar `docs/rag-indexer.md` con `embedding_base_url`, su obtención igual que `embedding_model`, ejemplos del registro DynamoDB para AWS/LocalStack, ausencia/vacío, uso de `embedding_provider=openai`, reinicio del job y coherencia del modelo con el consumidor. Verificar que los ejemplos y defaults coinciden con la implementación probada.
- [ ] 3.2 Actualizar `docs/architecture.md` y generar allí el diagrama de secuencia del spec: indexer → proveedor de configuración → DynamoDB → cliente → endpoint, incluyendo la rama sin URL y la reutilización del cliente. Verificar que el diagrama y los nombres corresponden al flujo implementado.
