## Context

MiniStack Batch marca SUCCEEDED sin ejecutar contenedores. El runner debe ejecutar el agente real y comprobar su exit code. El contrato existente registra file_key en DynamoDB batch_id_gsi y guarda tar.gz en S3. No se encontró el cliente CLI antiguo.

## Decisions

1. Cliente local nuevo dentro de tools/cli; no modifica el proyecto analizado. Lee working tree y Git ignore en cada submódulo. Preview antes de subir; JSON para automatización. Credenciales test y endpoint loopback en el laboratorio.
2. Paquete tar leído sin extracción; rechaza traversal, links, duplicados, binarios y hashes incorrectos. Manifiesto contiene rutas, tamaños, hashes y exclusiones. Subida completa antes de registrar tarea.
3. CliRetrievalNode inyectable conserva el grafo de expertos existente. main.py conecta la fuente según TaskSource.CLI. El laboratorio usa el mismo constructor de grafo, no un detector alternativo.
4. Conservar expertos paralelos, reducers, clasificación runtime y concurrencia acotada de lotes del Agent actualizado. Retry y corrección acotados. Presupuesto del mensaje completo, cap estable, contexto RAG acotado. Consolidación conservadora por archivo en grupos acotados, procedencia verificada y sin dedupe destructivo previo.
5. IA mock siempre marcada en reportes: valida transporte, no seguridad. Modo real explícito requiere clave y aceptación de envío. Las pruebas de integración usan fixtures públicos y modelos simulados.
6. CLI sin RAG; nunca consulta ni actualiza Git remoto. Primer objetivo integración confiable.

## Validation

Tests unitarios de selección/ignore/submódulos, archivos corruptos y tar malicioso, batches/JSON inválido, cobertura incompleta y reporte HTML escapado. Smoke real sobre MiniStack con fixture vulnerable y modelo mock, corrupción y lotes múltiples. Preview de fixtures sin transmitir código a proveedores externos. Lint y regresiones del agente.

## Risks

Compatibilidad del emulador se verifica con SDK real. El laboratorio omite API Gateway/auth/Lambda/notificaciones, por tanto no es una prueba de despliegue completa. Límites de transporte y chunks quedan visibles; se conserva la partición sin truncamiento del Agent actualizado.

## Interactive session refinement

Rich renders the dashboard and result summaries; Questionary handles arrows, directory completion, checkboxes and password input. No full-screen alternate terminal buffer is used, so scan logs remain available in terminal scrollback. A process-local Session retains project/scope/mode. Commands remain scriptable and unchanged. Provider secrets are inherited or entered with masked input, passed to the worker through existing environment configuration, and never persisted by the menu. FAILED evaluation and incomplete execution are displayed separately. Local report browsing is independent of MiniStack uptime.

## Guided review and visual identity

A four-line block robot anchors a compact screen. The home menu promotes review, with setup under Adjustments. First-run review completes project, scope and model in sequence; subsequent runs restore non-secret choices from the laboratory `.titvo` directory. Credentials remain environment-only. One explicit confirmation follows actual snapshot preview, before resource writes. Rich progress uses real worker counters; technical worker output is saved separately with configured API key redaction. Saved reports expose navigable findings with escaped evidence. Interactive redraw is confined to a TTY; script commands retain normal output.

## Local dashboard and task cost accounting
Use the existing admin frontend with an explicitly scoped read-only Python lab
adapter rather than start the production BFF authentication/deployment stack.
Preserve its default BFF proxy and raw evaluation status. A per-task model wrapper
counts successful response usage across async experts and sync consolidation,
including repairs; missing telemetry/failures prevent a complete cost claim.
Known standard GPT-4.1-mini pricing is snapshotted; custom rates support other
models without guesses. The Agent also records usage and duration in its existing AWS entry point.

## Presentation refinement
Keep the current Rich/Questionary implementation instead of adding a second TUI
framework. Rich manages one alternate terminal screen, redraw applies to all
nested menus/forms, and Questionary owns keyboard input. Apply Vim bindings only
to lists to preserve literal credential input. Reuse Live refresh for bounded
mascot animation; honor reduced motion. In the existing frontend, sort/filter/page
only the presentation of findings and collapse technical details by default.


## Selectable execution destination

Keep snapshot collection, the terminal workspace and outcome presentation shared.
MiniStack uses the existing SDK/Docker transport; AWS uses a separate CloudClient
for the deployed /cli-files, /run-scan and /scan-status contracts. API credentials
are scoped to the API endpoint, never sent to signed S3 URLs or persisted. The
cloud model is configured by the service. API settings and repository identity
are remembered without secrets. Script commands retain a local default unless
--target or TITVO_TARGET selects AWS. Destination is shown before confirmation;
there is no fallback between local and remote on failure. Polling has a deadline
and interruption leaves the task available for later status consultation.
The existing AWS HTML report carries full findings; missing inline issues are
presented using recorded issues_count, not as zero. Dashboard opens the selected
local launcher or a configured HTTPS production URL with its normal login.
