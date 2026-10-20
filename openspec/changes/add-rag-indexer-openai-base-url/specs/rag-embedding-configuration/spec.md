# Spec Delta

## Purpose

Permitir configurar el servicio de embeddings del RAG indexer mediante los parámetros compartidos del componente, admitiendo endpoints compatibles con OpenAI y conservando las configuraciones existentes.

## ADDED Requirements

### Requirement: Resolución del endpoint desde la configuración del modelo
El RAG indexer SHALL obtener el parámetro opcional `embedding_base_url` de la misma fuente de configuración que `embedding_model`, como valor no secreto de la tabla de configuración existente.

#### Scenario: Parámetro disponible en DynamoDB
- **WHEN** la tabla de configuración contiene `parameter_id=embedding_base_url` con un `value` no vacío
- **THEN** el indexer utiliza ese valor como URL base del servicio de embeddings
- **AND** obtiene el modelo de `embedding_model` y la credencial de `embedding_api_key` por los mecanismos existentes

### Requirement: Solicitudes a un endpoint compatible con OpenAI
Con `embedding_provider=openai` y `embedding_base_url` configurado, el indexer SHALL enviar las solicitudes de embeddings al endpoint configurado, conservando el modelo y la credencial seleccionados. La URL base SHALL conservar su prefijo de ruta, sin añadir una versión fija.

#### Scenario: Proveedor compatible con prefijo de ruta
- **WHEN** se configura `embedding_base_url=https://embeddings.example.com/custom/v1` y un modelo admitido por ese servicio
- **THEN** las solicitudes se dirigen a la API de embeddings bajo ese prefijo con el modelo y la credencial configurados
- **AND** no es necesario registrar otro identificador de proveedor

#### Scenario: Embeddings por lotes y streaming
- **WHEN** se procesan textos por lotes o mediante streaming con una URL personalizada
- **THEN** ambos flujos utilizan el endpoint configurado y conservan el orden de los vectores y las políticas existentes de batching y reintentos

### Requirement: Compatibilidad con configuraciones existentes
Si `embedding_base_url` está ausente, vacío o contiene solo espacios, el indexer SHALL conservar la resolución del endpoint que existía antes de este cambio. Un fallo de lectura de configuración SHALL propagarse y no interpretarse como parámetro ausente.

#### Scenario: Parámetro ausente
- **WHEN** no existe el registro `embedding_base_url`
- **THEN** el indexer puede construir su cliente con la configuración previa sin exigir el nuevo parámetro

#### Scenario: Parámetro vacío
- **WHEN** el valor es una cadena vacía o contiene solo espacios
- **THEN** se aplica el mismo comportamiento que para un parámetro ausente

#### Scenario: Error de acceso a la configuración
- **WHEN** la lectura de `embedding_base_url` falla por un error de acceso a DynamoDB
- **THEN** la inicialización falla con el error correspondiente sin cambiar silenciosamente al endpoint por defecto

### Requirement: Configuración estable durante la vida del cliente
El indexer SHALL resolver la URL base al inicializar su cliente de embeddings y reutilizar ese cliente durante la vida de la instancia. Los cambios posteriores de configuración SHALL aplicarse a nuevas instancias.

#### Scenario: Cambio de URL después de inicializar
- **WHEN** se modifica `embedding_base_url` después de la primera solicitud de una instancia
- **THEN** las solicitudes siguientes de esa instancia conservan el endpoint inicial
- **AND** una nueva instancia utiliza el valor actualizado
