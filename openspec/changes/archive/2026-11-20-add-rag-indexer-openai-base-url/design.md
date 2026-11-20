# Design

## Context

Ver `proposal.md` para la motivación. `LangChainEmbeddingAdapter._get_embeddings_client` obtiene `embedding_provider` y `embedding_model` mediante `IConfigurationProvider.get_value`, y `embedding_api_key` mediante `get_secret`. `AwsConfigurationAdapter` consulta DynamoDB por `parameter_id` y devuelve `None` cuando falta el registro. El cliente se crea de forma lazy y se conserva en `_embeddings`; `embed` y `embed_iter` comparten ese cliente.

La inicialización actual de `OpenAIEmbeddings` pasa únicamente modelo y credencial. Las pruebas de batching inyectan directamente un cliente falso, por lo que no cubren la construcción real del cliente.

## Goals / Non-Goals

**Goals:**
- Incorporar la URL en el punto único de construcción del cliente usando el puerto existente.
- Mantener la resolución actual del endpoint cuando no se configure el parámetro.
- Verificar tanto la construcción como el flujo de solicitudes sin depender de servicios externos.

**Non-Goals:**
- Cambiar interfaces de dominio o el adapter de DynamoDB.
- Recargar parámetros dentro de cada batch.
- Modificar automáticamente índices existentes o la configuración del agente consumidor.

## Decisions

1. **Leer `get_value("embedding_base_url")` junto al modelo.** El registro usa `parameter_id=embedding_base_url` y `value=<URL>`. Es un parámetro ordinario, no un secreto. Esto cumple el mecanismo solicitado sin introducir variables de entorno ni acoplar el adapter de embeddings a AWS. Se descarta leer directamente DynamoDB o usar una nueva fuente de configuración.

2. **Pasar la URL únicamente cuando esté configurada.** Normalizar espacios exteriores; `None`, cadena vacía o espacios equivalen a ausencia. Incluir el argumento de URL base admitido por la versión instalada de `OpenAIEmbeddings`, verificándolo con documentación actualizada antes de implementar. No hardcodear el endpoint OpenAI ni añadir `/v1`: omitir el argumento preserva la resolución previa del SDK, incluidas las opciones de entorno que ya pudiera admitir. Los errores de lectura se propagan; no envolverlos en un fallback general.

3. **Mantener `embedding_provider=openai` para endpoints compatibles.** Este identificador selecciona el protocolo existente. Crear identificadores para cada vendor duplicaría lógica innecesariamente. Mantener modelo, credencial, validaciones actuales y caché del cliente.

4. **Verificación en dos niveles.** Tests del constructor con mocks para comprobar lectura del parámetro, omisión del argumento, preservación de modelo/credencial y reutilización del cliente. Añadir una prueba con transporte HTTP simulado que inspeccione destino y payload de una solicitud real del SDK, sin red externa. Esto detecta diferencias entre aceptar el argumento y enviar una solicitud compatible. Verificar en la documentación de la versión instalada el tratamiento de tokenización de modelos externos; si exige un ajuste para enviar texto a endpoints compatibles, aplicarlo solo a la rama de URL personalizada y cubrirlo con esa prueba.

5. **Provisionamiento mediante el mecanismo de parámetros existente.** Documentar cómo crear o actualizar el registro en la misma tabla que `embedding_model`, tanto en AWS como LocalStack. No se requiere un cambio de esquema, permisos o bootstrap obligatorio: el registro es opcional.

## Risks / Trade-offs

- [Un servicio compatible puede tener límites o modelos distintos] → Probar el payload con transporte simulado y documentar que el endpoint debe admitir la API de embeddings y el modelo elegido; no prometer compatibilidad universal.
- [Cambiar el modelo altera el espacio vectorial del índice] → Documentar que el consumidor debe usar el mismo modelo/espacio y que un cambio de modelo requiere reindexación; no automatizar esta migración.
- [El SDK puede resolver un endpoint desde variables de entorno existentes] → Con parámetro ausente omitir el argumento, preservando el comportamiento previo; con valor explícito comprobar que prevalece.
- [Una instancia conserva su endpoint después de cambiar DynamoDB] → Documentar que el nuevo valor se aplica al crear otra instancia/job.

## Referencias verificadas

- Documentación oficial consultada mediante `find-docs`/Context7: https://reference.langchain.com/python/langchain-openai/embeddings/base/OpenAIEmbeddings
- Versiones instaladas verificadas: `langchain-openai 1.2.2`, `openai 2.38.0`, `httpx 0.28.1`. Los campos instalados admiten `base_url` (alias de `openai_api_base`), `http_client` y `check_embedding_ctx_length`.
- Decisión confirmada: pasar `base_url` y `check_embedding_ctx_length=False` con URL personalizada para enviar texto sin tokenización OpenAI. Sin URL se omiten ambos argumentos. Las pruebas usan `httpx.MockTransport` inyectado por `http_client` y comprueban la precedencia frente al endpoint del entorno.

## Migration Plan

1. Desplegar el adapter actualizado; los despliegues sin el registro siguen funcionando.
2. Para habilitar un servicio compatible, guardar `embedding_base_url` y configurar modelo y credencial compatibles en los parámetros existentes.
3. Iniciar un nuevo job para cargar los valores y verificar una indexación controlada.
4. Para revertir, restaurar la configuración anterior de URL/modelo/credencial e iniciar otro job. Eliminar la URL restaura la resolución anterior del SDK; si cambió el modelo, utilizar un índice compatible o regenerarlo.
