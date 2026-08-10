## ADDED Requirements

### Requirement: Selección de proveedor y credencial SSH

El sistema SHALL aceptar URLs HTTPS y SSH de GitHub y Bitbucket, SHALL validar el hostname exacto y SHALL desencriptar únicamente la llave privada asociada al proveedor seleccionado.

#### Scenario: Repositorio GitHub por URL HTTPS
- **WHEN** `TITVO_REPO_URL` es `https://github.com/acme/service`
- **THEN** el sistema usa el remoto SSH de GitHub y el parámetro cifrado `github_ssh_private_key`

#### Scenario: Repositorio Bitbucket por URL SSH
- **WHEN** `TITVO_REPO_URL` es `git@bitbucket.org:acme/service.git`
- **THEN** el sistema conserva un remoto SSH de Bitbucket y usa el parámetro cifrado `bitbucket_ssh_private_key`

#### Scenario: Host no soportado
- **WHEN** la URL no identifica exactamente `github.com` ni `bitbucket.org`
- **THEN** el sistema falla antes de desencriptar una llave o ejecutar Git

#### Scenario: Llave del proveedor ausente
- **WHEN** el parámetro SSH requerido no existe o está vacío
- **THEN** el sistema falla con un error que identifica el nombre del parámetro ausente y no intenta usar una API REST

### Requirement: Resolución SSH de ramas

El sistema SHALL resolver el SHA exacto de una rama remota mediante Git sobre SSH y SHALL conservar la semántica de idempotencia del full index.

#### Scenario: Rama existente
- **WHEN** se solicita full index para una rama existente
- **THEN** el sistema devuelve el SHA anunciado por `refs/heads/<branch>` del remoto SSH

#### Scenario: Rama inexistente
- **WHEN** el remoto no anuncia la rama solicitada
- **THEN** el sistema falla explícitamente sin seleccionar una coincidencia parcial, tag o rama distinta

#### Scenario: Commit ya indexado
- **WHEN** el SHA resuelto coincide con el último artefacto de la rama
- **THEN** el full index termina como idempotente y todos los recursos SSH temporales son liberados

### Requirement: Obtención de archivos desde objetos Git

El sistema SHALL traer por SSH el commit objetivo, SHALL enumerar sus blobs rastreados y SHALL devolver el contenido UTF-8 de los archivos no excluidos sin depender de un working tree.

#### Scenario: Full index de un commit
- **WHEN** el commit objetivo contiene archivos de código admitidos
- **THEN** el sistema devuelve sus rutas y contenidos desde los objetos Git de ese commit

#### Scenario: Archivo excluido
- **WHEN** la ruta pertenece a un directorio excluido o tiene una extensión binaria excluida
- **THEN** el archivo no se devuelve para indexación

#### Scenario: Blob no decodificable
- **WHEN** un blob admitido no puede decodificarse como UTF-8
- **THEN** el sistema registra y omite ese blob sin abortar la lectura de los demás archivos

#### Scenario: Symlink y submódulo
- **WHEN** el árbol contiene un symlink o gitlink de submódulo
- **THEN** el sistema no sigue rutas del filesystem ni clona el submódulo y solo procesa objetos blob de forma aislada

### Requirement: Cálculo delta con ambos commits

El sistema SHALL obtener por SSH tanto el SHA previamente indexado como el SHA objetivo dentro del mismo repositorio temporal y SHALL clasificar sus cambios en añadidos, modificados y eliminados.

#### Scenario: Delta con cambios comunes
- **WHEN** existen archivos añadidos, modificados y eliminados entre los dos commits
- **THEN** cada ruta aparece en la colección correspondiente del `DiffResult`

#### Scenario: Archivo renombrado
- **WHEN** Git detecta un rename entre los commits
- **THEN** la ruta anterior se reporta como eliminada y la ruta nueva como añadida

#### Scenario: Delta sin cambios indexables
- **WHEN** el diff está vacío o contiene únicamente rutas excluidas
- **THEN** el sistema devuelve un `DiffResult` vacío y conserva la terminación sin reindexación

#### Scenario: Reutilización del repositorio temporal
- **WHEN** el caso delta solicita posteriormente los archivos del SHA objetivo
- **THEN** el sistema reutiliza los objetos ya obtenidos y no crea un segundo clone o repositorio temporal

### Requirement: Ejecución SSH no interactiva y verificada

El sistema MUST ejecutar Git sin shell, MUST impedir prompts interactivos y MUST verificar la identidad del endpoint SSH mediante host keys fijadas para GitHub y Bitbucket.

#### Scenario: Ejecución normal
- **WHEN** el sistema invoca Git o SSH
- **THEN** usa argumentos estructurados, un entorno controlado, la llave temporal seleccionada, `BatchMode=yes` e `IdentitiesOnly=yes`

#### Scenario: Host key no coincide
- **WHEN** la identidad presentada por el endpoint no coincide con las host keys confiables
- **THEN** la conexión falla antes de transferir fuentes

#### Scenario: Autenticación requiere interacción
- **WHEN** la llave requiere passphrase o el servidor solicita una credencial interactiva
- **THEN** el job falla sin esperar entrada del usuario

### Requirement: Limpieza determinística de material temporal

El sistema MUST almacenar la llave privada temporal con permisos exclusivos para el usuario y MUST eliminar la llave y los datos Git en un cierre idempotente ejecutado para todo resultado del job.

#### Scenario: Indexación exitosa
- **WHEN** termina un full o delta index exitosamente
- **THEN** el archivo de llave y el repositorio temporal dejan de existir antes de finalizar el proceso

#### Scenario: Fallo durante Git o indexación
- **WHEN** ocurre una excepción después de crear recursos temporales
- **THEN** el sistema intenta eliminar todos los recursos y preserva el error original

#### Scenario: Cierre repetido
- **WHEN** la operación de cierre se invoca más de una vez
- **THEN** las invocaciones adicionales terminan sin error

### Requirement: Runtime preparado para Git SSH

La imagen de `rag-indexer` SHALL incluir versiones ejecutables de Git y OpenSSH junto con las host keys confiables requeridas por el adaptador.

#### Scenario: Verificación de imagen
- **WHEN** se inspecciona la imagen construida
- **THEN** `git`, `ssh` y el archivo versionado de host keys están disponibles

### Requirement: Ausencia total de obtención REST

`rag-indexer` MUST usar SSH como único transporte de fuentes para GitHub y Bitbucket y MUST eliminar los adaptadores, tokens, configuración, pruebas y dependencias directas que soportaban la obtención REST.

#### Scenario: Fallo de una operación SSH
- **WHEN** resolución, autenticación, fetch o lectura Git falla
- **THEN** la indexación falla explícitamente y no ejecuta ninguna solicitud REST

#### Scenario: Composición del servicio
- **WHEN** se construye el proveedor de repositorio
- **THEN** no existen adaptadores REST ni lecturas de `github_access_token` o `bitbucket_api_token`

#### Scenario: Dependencias y artefactos rastreados
- **WHEN** se inspeccionan `src`, `build/lib`, pruebas y dependencias directas de `rag-indexer`
- **THEN** no contienen implementaciones de obtención REST específicas de GitHub o Bitbucket
