# Titvo CLI · MiniStack

Cliente para analizar el working tree con el grafo real de Titvo, eligiendo
MiniStack local o la API del servicio AWS. En MiniStack, el modo predeterminado es
`mock`: prueba la integración, **no evalúa la seguridad**. El modo `real` llama al
proveedor de IA configurado y requiere aceptación explícita del envío.

## Preparación en otro equipo

Requiere Git, Python 3.13+, Docker Compose y Node.js/npm para el dashboard.
Clonar los tres repositorios como carpetas hermanas (sin copiar `.titvo`, claves
ni entornos virtuales de otro equipo):

```sh
git clone --branch feat/cli-fullscan-aws git@github.com:KaribuLab/titvo-dev.git
git clone --branch feat/cli-fullscan-aws git@github.com:KaribuLab/titvo-agent-aws.git
git clone --branch feat/scan-dashboard git@github.com:KaribuLab/titvo-admin-web.git
cd titvo-dev
```

Después de integrar las ramas, usar `main` en los tres clones. La instalación
editable mantiene el laboratorio junto a su compose; no es un paquete global
independiente de estos repositorios.


Ejecutar desde `titvo-dev`, con Python 3.13 o superior y Docker disponibles.
El build espera el clon hermano `../titvo-agent-aws`, como en este workspace.
No es necesario inicializar los submódulos de titvo-dev para este laboratorio.

```bash
python3 -m venv .venv-cli
.venv-cli/bin/pip install -e tools/cli
docker compose -f docker-compose.ministack.yaml up -d ministack
docker compose -f docker-compose.ministack.yaml build worker
.venv-cli/bin/titvo
```

MiniStack usa el puerto local 4566. Si otro stack lo ocupa, no levantar ambos
simultáneamente. No se modifica el compose original de LocalStack. MiniStack
está fijado por digest y el Agent utiliza su uv.lock. Los datos permanecen en el
contenedor MiniStack hasta eliminarlo; descargar los reportes antes de `down`.

## Preview de un proyecto

```bash
.venv-cli/bin/titvo preview \
  RUTA_DEL_PROYECTO \
  --include src/frontend --include src/backend --include src/infra
```

`--files` muestra las rutas; `--json` devuelve el manifiesto. Preview no sube
archivos ni contacta IA. Se analiza el working tree, incluyendo modificaciones
y archivos nuevos no ignorados. Se respetan los ignores de cada submódulo Git
inicializado. Si un submódulo falta, el scan aborta antes de subir.

Sin `--include`, se incluyen archivos UTF-8 de la carpeta completa, con las
exclusiones predeterminadas. Se excluyen dependencias, builds, entornos Python,
metadatos Git, herramientas de asistentes, `.tmp`, `.titvo`, archivos `.env*`,
lockfiles, enlaces y binarios. Cada exclusión se registra con su motivo. El
límite por archivo es 2 MiB y por snapshot seleccionado 90 MiB; estos límites
son de transporte, no el cap de contexto del modelo.

## Fullscan con IA simulada

```bash
.venv-cli/bin/titvo scan tools/cli/fixtures/demo --yes
.venv-cli/bin/titvo scan \
  RUTA_DEL_PROYECTO \
  --include src/frontend --include src/backend --include src/infra --yes
.venv-cli/bin/titvo status IDENTIFICADOR --json
```

Los reportes JSON y HTML se descargan a `.titvo/reports/`; `--output` cambia el
destino. HTML incluye evidencia escapada, cobertura de ejecución, archivos
excluidos y truncados. `FAILED` puede significar hallazgos HIGH/CRITICAL o
ejecución incompleta; el campo `coverage.complete` distingue ambos casos.
Exit 0 significa ejecución completa, no ausencia de vulnerabilidades. Exit 2
indica un error o análisis incompleto. El mock reconoce sólo un marcador de
fixture sintético y nunca debe interpretarse como un detector de seguridad.

## Modelo real

Elegir proveedor/modelo y cargar la clave mediante variables de entorno. No
guardar la clave en Git. La clave se pasa al worker y no se incluye en reportes.

```bash
export TITVO_AI_PROVIDER=openai
export TITVO_AI_MODEL=MODELO_ELEGIDO
export TITVO_AI_API_KEY=CLAVE_DEL_PROVEEDOR
.venv-cli/bin/titvo scan RUTA_DEL_PROYECTO --model real --allow-remote-ai
```

Se mantienen los proveedores del Agent: OpenAI, OpenRouter, Anthropic y Google.
`TITVO_AI_BASE_URL` admite los endpoints HTTPS soportados por su fábrica actual.
Esta entrega no implementa modelos locales. Nunca se ejecuta código del
proyecto analizado. El laboratorio no publica GitHub Issues ni Code Insights.

## Contexto y batching

`TITVO_EXPERT_FILE_CAP_CHARS=30000` limita contenido por archivo;
`TITVO_EXPERT_BATCH_BUDGET_CHARS=200000` acota el mensaje contando prompt,
encabezados y contexto, con una reserva de 2000 caracteres. Son límites de
caracteres, no garantía de tokens para cualquier modelo: deben ajustarse al
modelo elegido. El Agent actual particiona archivos grandes en chunks con
solapamiento y contexto estructural, conservando líneas originales. Se conserva
la clasificación runtime y el fan-out de expertos de main; sus lotes usan la
concurrencia acotada del Agent (por defecto 4). Los errores y lotes incompletos
quedan explícitos en cobertura. No se vuelve al truncamiento de la versión inicial.

Para CLI se desactiva RAG remoto. Agregar RAG requiere indexar el mismo snapshot,
no descargar otra versión del proyecto por Git.

## Pruebas

```bash
# Entorno de pruebas: instalar Agent, CLI y herramientas en un venv separado.
pip install -e ../titvo-agent-aws -e tools/cli pytest pytest-asyncio ruff 'moto[s3,dynamodb]'
pytest tools/cli/tests ../titvo-agent-aws/tests/unit
TITVO_MINISTACK_TESTS=1 pytest tools/cli/tests/test_ministack.py
ruff check tools/cli
```

Los tests opt-in ejecutan Docker contra MiniStack y comprueban lotes múltiples y
un paquete corrupto. Los tests con moto sólo simulan SDK en memoria y se reportan
por separado. Para regresiones exactas del Agent usar las versiones de uv.lock.

## Alcance de la simulación

S3 y DynamoDB usan APIs AWS contra MiniStack. La ejecución es un contenedor
Docker real: MiniStack Batch actualmente marca jobs SUCCEEDED sin ejecutar su
código. El laboratorio evita depender de ese estado. No despliega API Gateway,
autenticación, Lambda ni infraestructura productiva; reutiliza directamente
el contrato de paquetes/batch_id y el grafo del Agent.

Fuentes verificadas: [MiniStack](https://github.com/ministackorg/ministack),
[Boto3 Query](https://docs.aws.amazon.com/boto3/latest/reference/services/dynamodb/client/query.html),
[Typer Context](https://typer.tiangolo.com/tutorial/commands/context/) y
[Rich Console](https://rich.readthedocs.io/en/latest/console.html).

## Sesión guiada de terminal

La CLI está instalada en `.venv-cli`. Para escribir simplemente `titvo`:

```zsh
cd titvo-dev
source .venv-cli/bin/activate
titvo
```

Un robot de cuatro líneas y un panel compacto muestran los pasos listos o
pendientes. Usa ↑/↓ y Enter. «Revisar proyecto» completa automáticamente los
pasos que falten: proyecto, alcance y modelo. «Ajustar análisis» permite cambiar
cualquiera de esas opciones o revisar la selección. Las carpetas se marcan con
Espacio. Desde otra carpeta de proyecto, Titvo la toma como selección inicial.

Se recuerdan proyecto, alcance y proveedor/modelo en el laboratorio
`titvo-dev/.titvo/ui.json`, fuera del snapshot y excluido de Git. Al entrar desde
un proyecto diferente, su carpeta actual tiene prioridad sobre la recordada.
Las claves no se serializan: usa las variables de entorno o la entrada oculta
para esa sesión. La configuración de IA heredada se restaura al salir. Cambiar
de proveedor requiere su propia clave. `TITVO_AI_BASE_URL` conserva el valor
exportado; debe corresponder al proveedor elegido.

La primera revisión solicita elegir IA simulada o real. Antes de subir se
muestra la selección de archivos y una única confirmación. Para IA real esa
confirmación autoriza también el envío al proveedor. «Credencial configurada»
no significa conexión verificada: eso se comprueba al ejecutar el modelo.

El avance usa los contadores reales del worker y tiempo transcurrido, sin
porcentajes estimados. El detalle técnico se guarda junto al reporte como
`TASK_ID.log`, ocultando la clave configurada si aparece en el diagnóstico.
Después de analizar puedes explorar cada hallazgo: archivo, línea, explicación,
evidencia y recomendación, o abrir el reporte HTML. Enter regresa al proyecto.
Ctrl+C en un selector cancela la selección; en el menú principal cierra la sesión.
El menú no ofrece cancelación ni reanudación de un worker ya iniciado.

«Reportes anteriores» consulta `.titvo/reports` de la carpeta desde la que
abriste Titvo, incluso sin MiniStack. «Consultar tarea en curso» recupera su
estado mediante el identificador. Los resultados distinguen análisis completado
con hallazgos de análisis incompleto, aunque ambos puedan tener evaluación
`FAILED`. Los comandos `scan`, `preview` y `status` siguen disponibles para scripts.

La interacción usa [Questionary](https://questionary.readthedocs.io/en/stable/pages/types.html)
y sus [estilos documentados](https://questionary.readthedocs.io/en/stable/pages/advanced.html);
Rich renderiza el robot, el panel de sesión y el avance.

## Recuperación de respuestas inválidas

El Agent normaliza diferencias de formato seguras y pide una corrección acotada
para los hallazgos JSON que no cumplen el contrato. El progreso muestra
«Corrigiendo respuesta» y el resumen indica los lotes recuperados. Los motivos
concretos de rechazo quedan en `coverage.experts.*.batch_diagnostics`; errores
sin resolver mantienen cobertura incompleta. El resultado previo no se altera.
No existe todavía reanudación de tareas anteriores; iniciar otro scan vuelve a
analizar la selección. Tras cambios del Agent reconstruye el worker con
`docker compose -f docker-compose.ministack.yaml build worker`.

## Probar CLI y dashboard juntos

El frontend existente es `../titvo-admin-web`. El comando nuevo lo conecta a los
mismos reportes S3 y tareas DynamoDB de MiniStack mediante un adaptador **local,
solo lectura**. No requiere login ni API key para visualizar resultados; la
identidad de laboratorio no prueba la autenticación del BFF de producción.
El modo normal del frontend sigue apuntando al BFF `localhost:3001`.

Desde `titvo-dev`:

```sh
docker compose -f docker-compose.ministack.yaml up -d ministack
# Instalar una vez las dependencias del frontend:
npm --prefix ../titvo-admin-web ci
.venv-cli/bin/titvo dashboard
```

Abre `http://127.0.0.1:5173`. El adaptador usa `127.0.0.1:8787` y rechaza escrituras.
Cambia los puertos con `--port` y `--api-port` si están ocupados. Ctrl+C cierra
ambos procesos; conserva MiniStack y sus reportes. En otra terminal puedes abrir
el menú con `.venv-cli/bin/titvo`, o ejecutar:

```sh
.venv-cli/bin/titvo scan tools/cli/fixtures/demo --model mock --yes
# Para un proyecto con el proveedor real configurado en esa terminal:
.venv-cli/bin/titvo scan RUTA_DEL_PROYECTO \
  --model real --allow-remote-ai
```

Recarga el dashboard y entra al repositorio → historial → análisis. Muestra el
resumen y los hallazgos, con evidencia y recomendación. El mock prueba transporte,
no seguridad. `FAILED` conserva el estado original de evaluación: para saber si
la ejecución terminó, consulta **Cobertura de ejecución**.

## Resumen final y costo de IA

Los reportes nuevos incluyen `metrics` y `usage`. La duración total se mide desde
el registro de la tarea hasta finalizar el análisis (incluye arranque Docker);
la duración del agente mide lectura del snapshot y ejecución del grafo. No
incluyen selección/confirmación inicial ni visualización/descarga del reporte.
También se muestran archivos, lotes, hallazgos, exclusiones y truncamientos.

Un wrapper por tarea cuenta llamadas sync/async de expertos, correcciones y
consolidación. Suma los tokens devueltos por el proveedor: entrada, entrada en
caché (subconjunto de entrada) y salida. No estima tokens a partir de caracteres.
Las llamadas fallidas o sin telemetría hacen incompleto el consumo registrado.

El costo es **estimado**, en USD, de las llamadas al modelo; no es factura y no
incluye AWS, impuestos ni embeddings (RAG está desactivado). Tarifas estándar
[OpenAI GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini)
verificadas el 2026-10-06: por millón de tokens, entrada US$0.40, entrada en caché
US$0.10 y salida US$1.60. El reporte guarda tarifas, fuente y fecha de verificación.
No se aplican a otros modelos ni endpoints personalizados. Para ellos configura
las tres tarifas en USD por millón antes de iniciar el scan:

```sh
export TITVO_PRICE_INPUT_PER_MILLION=0.40
export TITVO_PRICE_CACHED_PER_MILLION=0.10
export TITVO_PRICE_OUTPUT_PER_MILLION=1.60
```

Sin tarifa o sin consumo, muestra «No registrado»; con consumo parcial muestra
«parcial», nunca pretende ser costo total. Mock muestra cero explícito. Los
reportes antiguos se conservan sin inventarles costo ni duración.

Los scans nuevos identifican el proyecto por hash de su ruta local para evitar
mezclar carpetas con el mismo nombre; no guardan la ruta absoluta en el snapshot.
Los históricos solo tenían nombre y se agrupan con esa identidad anterior.

## Navegación y apariencia Titvo

El resumen separa **Ejecución**, **Seguridad** y **Errores técnicos**. Cobertura
completa significa `Completado`, incluso si la evaluación técnica es `FAILED`
por hallazgos. Cobertura parcial significa `Incompleto`; cero lotes completados
con error explícito significa `Fallido`. Sin cobertura registrada no se infiere
un resultado. El dashboard aplica esta ejecución medida a listas y detalle;
el valor original de evaluación se conserva en los datos técnicos.

La CLI usa índigo/violeta de [titvo.com](https://www.titvo.com/) con tonos más
claros para contraste sobre terminales oscuras. Rich y Questionary comparten
`theme.py`. En una terminal compatible, `titvo` abre una pantalla alternativa:
cada submenú y formulario reemplaza el anterior, y al salir restaura el shell.
Los comandos explícitos `scan`, `preview` y `status` siguen funcionando en su
salida normal; el menú no se activa en tuberías.

- `↑/k` y `↓/j`: mover selección.
- `Enter/l`: elegir o confirmar carpetas.
- `Esc/h` o `Ctrl+C`: volver; en el menú principal, salir.
- Seleccionar `Salir` con `Enter/l` cierra la sesión y restaura la terminal;
  muestra `¡Hasta pronto! 👋` y recuerda que los reportes quedan guardados.
  Seleccionar `Volver` retorna al menú padre.
- `Espacio`: marcar carpetas.
- En campos de texto/ruta/API key se escribe normalmente; no se interceptan letras.

La mascota cambia de pose al navegar y parpadea/mueve los pies mientras trabaja,
sin modificar contadores ni tiempos. `TITVO_NO_ANIMATION=1` deja la mascota estática.
`NO_COLOR` se respeta y también desactiva el movimiento. Terminales `TERM=dumb`
no admiten la pantalla alternativa ni colores; para ver la UI completa usa una
terminal ANSI normal. La animación se actualiza con el Live existente, sin
procesos extra ni llamadas de IA. En el explorador puedes abrir el resumen
completo, evidencia de cada hallazgo y el HTML guardado.

En el dashboard, el detalle prioriza duración/costo/archivos/hallazgos y cobertura.
Los hallazgos se ordenan por severidad, archivo y línea; hay búsqueda, filtro y
paginación de 20 por página. Cada hallazgo despliega explicación, evidencia y
recomendación. Consumo detallado, metadatos y JSON se mantienen plegados hasta
que los abras. Un reporte incompleto no se presenta como un análisis terminado
solo porque tenga cero hallazgos.


## Integración con AWS

MiniStack es el laboratorio de desarrollo. La CLI permite elegir ese laboratorio
o conectarse al API productivo desde el menú y los comandos.
El Agent sí recibe tareas `cli` desde el flujo AWS existente: lee `batch_id`
de DynamoDB y descarga los paquetes de S3; las tareas Git conservan MCP y RAG.
AWS Batch recibe las variables del bucket y tabla CLI desde los parámetros SSM
existentes. Se mantiene el pipeline de despliegue del Agent y la autenticación
normal del frontend/BFF. No activar `VITE_TITVO_LAB` en producción.

Ramas para revisión: Agent `feat/cli-fullscan-aws`, BFF
`feat/scan-execution-summary`, frontend `feat/scan-dashboard` y laboratorio
`titvo-dev/feat/cli-fullscan-aws`. Integrar Agent/BFF antes del frontend.
El laboratorio no necesita desplegarse en AWS. Revisar y desplegar con los
mecanismos existentes; subir estas ramas no despliega infraestructura.

El Agent productivo registra duración, consumo medido y costo estimado de
llamadas al modelo. No incluye embeddings ni costos AWS. Los históricos sin
telemetría muestran «No registrado». En AWS se conserva el reporte HTML
externo y la cantidad de hallazgos; el laboratorio además entrega los hallazgos
JSON completos al dashboard local.


## Elegir MiniStack o AWS

En la primera apertura de `titvo` se elige el destino. Luego puede cambiarse
con **Ajustar análisis → Cambiar destino**. El menú y la confirmación muestran
si se usará MiniStack o AWS. Se recuerda el destino y sus URLs, nunca las claves.
Una falla no cambia de destino automáticamente.

**MiniStack:** conserva el Agent Docker, el modelo mock/real y el dashboard local.
**AWS:** no requiere ejecutar MiniStack ni Docker. Configura el endpoint de la
API Titvo y una clave Titvo, normalmente `tvok…`. No uses la clave de OpenAI:
el modelo/proveedor se configura en el servicio. La entrada de clave es oculta
y dura solo esa sesión; también puede heredarse de `TITVO_API_KEY`.

En AWS la CLI solicita `POST /cli-files`, sube el tar.gz a la URL prefirmada
mediante PUT (sin enviar la clave Titvo a S3), inicia `POST /run-scan` con
`source=cli` y `scan_mode=full`, y consulta `POST /scan-status`.
Se acepta el mapa de URLs del use-case actual y el formato de lista documentado.
Los endpoints API y subida deben usar HTTPS; no se siguen redirecciones.
La API y el Agent de las ramas correspondientes deben estar desplegados para
utilizar este flujo; publicar ramas no los despliega.

La URL Git y rama identifican el historial; el código analizado sigue siendo
el snapshot del working tree, no una descarga del repositorio. La CLI usa
`origin` y la rama activa cuando están disponibles; permite indicarlos para
carpetas sin Git o detached HEAD. Las URLs con credenciales son rechazadas.

```zsh
export TITVO_API_ENDPOINT=https://API_DE_TU_INSTANCIA
read -rs 'TITVO_API_KEY?Clave Titvo y Enter: '
echo
export TITVO_API_KEY
# Opcional, para abrir el dashboard productivo desde la CLI:
export TITVO_DASHBOARD_URL=https://DASHBOARD_DE_TU_INSTANCIA

titvo scan ./proyecto --target aws
# Si no hay origin o rama activa:
titvo scan ./proyecto --target aws \
  --repository-url https://github.com/ORGANIZACION/REPOSITORIO --branch main

titvo status IDENTIFICADOR --target aws
titvo dashboard --target aws
# Volver a pruebas locales:
titvo scan ./proyecto --target ministack --model mock
```

También existen `--api-endpoint`, `--dashboard-url` y `--wait-timeout` (segundos,
predeterminado 1800). Los comandos explícitos usan MiniStack por defecto salvo
`--target` o `TITVO_TARGET`; la preferencia del menú no cambia scripts. `--yes`
acepta explícitamente la subida y ejecución en el destino indicado. AWS no
admite `--model`: se usa la configuración del servicio.

Durante la espera se muestra el estado remoto sin inventar lotes ni porcentajes.
Ctrl+C interrumpe la consulta, no el trabajo AWS. El identificador se imprime
antes de esperar; permite consultar más tarde sin crear otro análisis. Al
terminar se guarda el resumen JSON/HTML local con el costo/tiempo registrados.
Si AWS entrega `issues_count` y un reporte externo, se muestran ambos sin
pretender tener evidencia inline ni inventar cero hallazgos.

**Abrir dashboard** lanza el frontend local para MiniStack o abre la URL AWS
configurada. El dashboard productivo mantiene su propio login. La CLI no
convierte su clave Titvo en una sesión de administrador del dashboard.
