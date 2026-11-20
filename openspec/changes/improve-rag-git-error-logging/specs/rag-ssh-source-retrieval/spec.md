# Spec Delta

## ADDED Requirements

### Requirement: Diagnóstico de fallos de comandos Git

Cuando una invocación Git del indexador RAG termina con error o timeout, el sistema SHALL exponer en el error propagado y en el log el subcomando, el código de salida (si aplica) y el stderr del proceso (completo o truncado de forma segura). El mensaje MUST omitir URLs remotas, rutas de llaves y material de credenciales.

#### Scenario: Fallo Git con stderr disponible
- **WHEN** un comando Git termina con código distinto de cero y stderr no vacío
- **THEN** el error y el log incluyen el subcomando, el código de salida y el contenido de stderr usable para diagnóstico

#### Scenario: Fallo Git sin stderr
- **WHEN** un comando Git termina con código distinto de cero y stderr vacío
- **THEN** el error y el log incluyen el subcomando y el código de salida, sin sustituir el diagnóstico por un mensaje genérico que oculte el exit code

#### Scenario: Timeout de comando Git
- **WHEN** un comando Git excede el timeout configurado
- **THEN** el error identifica timeout del subcomando y, si existen, incluye fragmentos de stderr/stdout capturados hasta el corte

#### Scenario: Sin filtración de secretos en el diagnóstico
- **WHEN** el comando fallido incluye URL remota, ruta de llave privada o argumentos sensibles
- **THEN** el mensaje de error y el log no contienen esos valores
