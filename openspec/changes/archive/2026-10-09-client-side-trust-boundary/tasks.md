## 1. Preámbulo común y registro de prompts

- [x] 1.1 Reescribir `prompts/system_prompt.md` como preámbulo común: Security Boundary y Anti-Fabrication (sin cambios), sección "Runtime semantics" con la tabla de D2, Severity + Suspicion policy (D4), formato `{"issues": [...]}`, RAG como contexto de fondo, español neutro; eliminar las secciones de `status`/`scaned_files`
- [x] 1.2 `prompts/__init__.py`: agregar `get_common_preamble()` y `compose_expert_prompt(name)`; eliminar `get_orchestrator_prompt()`; borrar `prompts/orchestrator_prompt.md`
- [x] 1.3 `nodes/base_expert_node.py`: usar `compose_expert_prompt(self.expert_name)` como `SystemMessage`
- [x] 1.4 `langgraph_agent.py` y `main.py`: dejar de pasar `system_prompt` a `LangGraphAgent` (el adaptador legado `langchain_agent_adapter.py` sigue usando `get_system_prompt()`)
- [x] 1.5 Tests `test_prompts.py`: preámbulo contiene "[runtime:", "Sospecha:", "Para confirmar:"; `compose_expert_prompt` empieza con el preámbulo y contiene el prompt del experto; `get_orchestrator_prompt` ya no existe; ningún prompt de experto contiene "Environment variable references for secrets → NOT a finding"

## 2. Reglas por runtime y patrones nuevos en expertos

- [x] 2.1 `experts/owasp_api.md`: reescribir "False Positive Rules" remitiendo al preámbulo; agregar sección "Client-side authentication (browser/mobile)" con patrones: API key estática como única auth, HMAC en cliente, `Authorization` con constante, request sin credencial de usuario, `Date.now()` como nonce; escala de severidad D3
- [x] 2.2 `experts/owasp_web.md`: idem para A04/A07/A02: token en `localStorage` como única credencial, clave de firma en bundle, `import.meta.env` con secretos, widget keys con la escala D3
- [x] 2.3 `experts/owasp_mobile.md`: equivalentes MASVS-AUTH/CRYPTO con `AsyncStorage`, `SharedPreferences`, `UserDefaults`, claves embebidas
- [x] 2.4 `experts/code_vulnerabilities.md`: "False Positive Rules" remitiendo al preámbulo; regla de fixtures placeholder → LOW en runtime `test`
- [x] 2.5 Revisar `experts/prompt_hardening.md` y `experts/devsecops.md`: sin cambios de dominio, sólo quitar frases que contradigan el preámbulo si las hubiera
- [x] 2.6 Test de regresión de prompts: cada experto incluye la referencia a `[runtime:` y los tres de D5 contienen "secretos del lado cliente"

## 3. Política de sospechas en código y consolidación

- [x] 3.1 `base_expert_node.py::_parse_response`: si el título empieza con `Sospecha:` (normalizado) y severidad HIGH/CRITICAL → MEDIUM y `metadata.severity_capped = true`
- [x] 3.2 `prompts/findings_consolidation.md`: regla "conservar `Sospecha:` sólo si todas las fuentes son sospechas; si se fusiona con confirmado, prevalece el título confirmado"
- [x] 3.3 Tests: `test_base_expert_node.py` (sospecha HIGH → MEDIUM con `severity_capped`; confirmado HIGH intacto; prefijo con/sin acento y mayúsculas); `test_prompts.py` (prompt de consolidación contiene la regla)

## 4. Verificación y cierre

- [x] 4.1 `ruff check` y `pytest` en verde en `src/agent`
- [ ] 4.2 Fixture de prueba manual: archivo `browser` con `Authorization: Bearer <const>` + `X-Signature: hmac(...)` y sin cookie; correr el experto `owasp_api` contra el proveedor real y verificar que reporta "Autenticación basada en secretos del lado cliente" CRITICAL con la verificación server-side en la descripción
- [ ] 4.3 Re-escanear el repo del primer fullscan de prod: el token de TalkCenter debe salir como `Sospecha:` MEDIUM con "verificar restricción de dominio"; comparar conteo de MEDIUM antes/después y anotar en `design.md`
- [x] 4.4 Actualizar `src/agent/README.md`: composición preámbulo + experto, política de sospechas
