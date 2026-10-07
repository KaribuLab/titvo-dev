## 1. Agente
- [x] 1.1 Fuente CLI y validación de snapshots con tests.
- [x] 1.2 Integración en LangGraph/main/use-case, omitir RAG para CLI.
- [x] 1.3 Batching estable, errores de parseo y cobertura incompleta con tests.
- [x] 1.4 Consolidación conservadora y preservación de entradas.
## 2. Laboratorio y CLI
- [x] 2.1 Preview, selección local y paquetes con hashes; tests de ignore/submódulos.
- [x] 2.2 Upload, tareas DynamoDB, ejecución Docker, progreso y status.
- [x] 2.3 Reportes JSON/HTML y modelo mock explícito.
- [x] 2.4 Docker Compose MiniStack, worker y fixture.
## 3. Validación
- [x] 3.1 Tests unitarios/regresión y linter.
- [x] 3.2 Smoke con MiniStack y mock, corrupción y múltiples lotes.
- [x] 3.3 Preview de proyecto de ejemplo sin envío a proveedor IA.
- [x] 3.4 Validar OpenSpec y documentación oficial; skill find-docs no disponible, usar fuentes primarias.
## 4. Documentation
- [x] 4.1 Actualizar docs/architecture.md.
- [x] 4.2 Documentar comandos, límites y alcance del laboratorio.
- [x] 4.3 Generar diagrama de secuencia.
## 5. Sesión interactiva
- [x] 5.1 Menú con flechas, proyecto/alcance, modelo y credenciales temporales.
- [x] 5.2 Navegar reportes y distinguir hallazgos de errores de ejecución.
- [x] 5.3 Actualizar tests unitarios, validar linter y documentación oficial de Questionary (find-docs no disponible).
- [x] 5.4 Actualizar documentación del componente, docs/architecture.md y diagrama de secuencia.
## 6. Experiencia guiada y mascota
- [x] 6.1 Integrar robot compacto y dashboard con acción principal y ajustes secundarios.
- [x] 6.2 Guiar proyecto/alcance/modelo, recordar preferencias no secretas y confirmar una vez.
- [x] 6.3 Explorar hallazgos en terminal y mostrar progreso sin ruido Docker.
- [x] 6.4 Generar tests, validar linter y OpenSpec, actualizar documentación y diagrama de secuencia.
## 7. Recuperación de hallazgos inválidos
- [x] 7.1 Contrato común, normalización segura y motivos concretos de validación.
- [x] 7.2 Corrección acotada de registros rechazados con IDs y preservación de hallazgos válidos.
- [x] 7.3 Tests de recuperación/omisiones/evidencia/límites y regresión del Agent.
- [x] 7.4 Mostrar diagnóstico, actualizar documentación/diagrama, validar linter y reconstruir worker.
## 8. Resumen y dashboard local
- [x] 8.1 Contabilizar llamadas y tokens sync/async, caché y costo estimado/ausente/parcial.
- [x] 8.2 Persistir duración y mostrar resumen en CLI, HTML y frontend existente.
- [x] 8.3 Adaptador MiniStack de lectura, paginación y comando dashboard en loopback.
- [x] 8.4 Tests unitarios/integración/UI, build y linter; validar OpenSpec.
- [x] 8.5 Actualizar documentación del componente, docs/architecture.md y diagrama de secuencia.
- [x] 8.6 Documentación oficial: find-docs no disponible; OpenAI pricing y Vite verificados con fuentes primarias.
## 9. Identidad visual y navegación
- [x] 9.1 Paleta índigo de Titvo compartida entre Rich y Questionary.
- [x] 9.2 Pantalla alternativa, reemplazo de menús/formularios y teclas Vim/flechas.
- [x] 9.3 Mascota con poses acotadas y movimiento desactivable.
- [x] 9.4 Dashboard ordenado, hallazgos expandibles, filtros y paginación.
- [x] 9.5 Tests de navegación real, regresión, linter, build y validación UI/OpenSpec.
- [x] 9.6 Actualizar documentación del componente, docs/architecture.md y diagrama de secuencia.
- [x] 9.7 find-docs no disponible; documentación oficial de Rich/Questionary/prompt_toolkit y web Titvo verificada.

## 10. Corrección de salida y retorno
- [x] 10.1 Preservar los valores de salida/retorno frente al fallback de Choice(None).
- [x] 10.2 Probar selección real con Enter/l y cancelación con h/Esc/Ctrl+C; validar linter.
- [x] 10.3 Actualizar documentación del componente, arquitectura, spec y diagrama de secuencia.
- [x] 10.4 find-docs no disponible; contrato verificado en el código instalado de Questionary.

## 11. Estados independientes
- [x] 11.1 Separar ejecución, hallazgos y errores técnicos en CLI y dashboard.
- [x] 11.2 Agregar ejecución medida al adaptador local y usarla en listas/estadísticas sin modificar evaluación.
- [x] 11.3 Generar tests unitarios y validar linter/build.
- [x] 11.4 Actualizar documentación del componente, arquitectura y diagrama de secuencia.
- [x] 11.5 find-docs no disponible; se utilizan contratos locales y bibliotecas existentes.

## 12. Preparación de ramas y AWS
- [x] 12.1 Integrar sobre main actualizado sin revertir runtime, chunking ni fan-out.
- [x] 12.2 Configurar bucket/tabla CLI en AWS Batch y registrar consumo/duración en el Agent.
- [x] 12.3 Propagar ejecución medida por BFF y permitir cantidad/reporte externo en dashboard.
- [x] 12.4 Documentar instalación portable y alcance del laboratorio frente a AWS.
- [x] 12.5 Completar regresión y preparar publicación de ramas sin crear PR ni desplegar.

## 13. Destino configurable
- [x] 13.1 Agregar elección y persistencia no secreta de MiniStack/AWS.
- [x] 13.2 Usar API existente para subida, inicio y consulta con clave Titvo aislada.
- [x] 13.3 Mantener estado/costo medidos y conteo/reporte externo sin inventar hallazgos.
- [x] 13.4 Abrir dashboard del destino seleccionado con autenticación productiva intacta.
- [x] 13.5 Actualizar pruebas de contratos, autorización, navegación y regresión.
- [x] 13.6 Generar diagrama y actualizar README/arquitectura.
- [x] 13.7 Validar Ruff, OpenSpec e integración MiniStack; preparar actualización de rama.
- [x] 13.8 find-docs no disponible; contratos revisados en código y urllib en documentación oficial.
