## Why

El agente no detectó una API autenticada sólo con un token embebido en el frontend y una firma
calculada en el navegador. Las reglas anti-falso-positivo de los prompts ("variables de entorno no
son hallazgo") son correctas para servidor e **incorrectas para código cliente**, donde todo valor
termina en el bundle. Y cuando sí reporta (token de TalkCenter en `chat.js`) marca CRITICAL sin
saber qué otorga el token. Tras `fullscan-parity` cada archivo llega con su etiqueta
`[runtime: ...]`; falta que los prompts la usen.

## What Changes

- **Preámbulo común por runtime**: `system_prompt.md` (hoy huérfano) antecede a cada prompt de
  experto. Define cada `[runtime: X]` y sus reglas de confianza: en `browser`/`mobile` literales,
  `import.meta.env`, `VITE_*`, `REACT_APP_*` y claves de firma son **públicos**.
- **Autenticación cliente-servidor como hallazgo de diseño**: peticiones autenticadas sólo con
  credenciales de aplicación o firmas calculadas en cliente se reportan aunque el backend no esté
  en el repo.
- **Severidad de credenciales en cliente según lo que otorgan**: identificador público de widget de
  terceros → LOW/MEDIUM con "verificar restricción de dominio"; credencial contra backend propio →
  HIGH; clave de firma (HMAC) → CRITICAL.
- **Política de sospechas explícita**: prefijo `Sospecha:`, severidad MEDIUM máximo (garantizado
  por código), descripción con la pregunta a verificar. Fixtures placeholder en `test` → LOW.
- **Nuevos patrones A04/A07** en `owasp_api`, `owasp_web` y `owasp_mobile`: HMAC en cliente, API key
  estática como única auth, token en `localStorage` como única credencial, firma con `Date.now()`
  sin nonce de servidor, request sin credencial ligada al usuario.
- **Eliminar `orchestrator_prompt.md`** (muerto). **BREAKING** para `PromptRegistry`:
  `get_orchestrator_prompt()` desaparece.
- Consolidación L2: conserva el prefijo `Sospecha:` sólo si todas las fuentes fusionadas son sospechas.

## Capabilities

### New Capabilities
- `client-side-trust-boundary`: reglas de confianza por runtime y detección de autenticación
  basada en secretos del lado cliente, con escala de severidad por lo que otorga la credencial.
- `suspicion-reporting`: contrato de los hallazgos marcados como sospecha (prefijo, tope de
  severidad, pregunta a verificar, comportamiento en consolidación).

### Modified Capabilities
- `security-expert-agents`: el prompt efectivo de cada experto es preámbulo común + prompt de
  dominio; `orchestrator_prompt.md` deja de existir.
- `conservative-findings-policy`: las exclusiones de variables de entorno y nombres de variables
  quedan condicionadas al runtime; "incertidumbre → MEDIUM" pasa a "incertidumbre → sospecha
  marcada".

## Impact

- `prompts/`: `system_prompt.md` como preámbulo, `experts/*.md`, `findings_consolidation.md`,
  borrado de `orchestrator_prompt.md`, `__init__.py`.
- `nodes/base_expert_node.py`: composición del `SystemMessage` y tope de severidad para sospechas.
- Tests de prompts, expertos y merge. Sin cambios en MCP, API, `ExpertIssue` ni reporte.
- Más MEDIUM en frontends: esperado; el reporte los muestra como sospechas.

## Non-goals

- Campo `confidence` en el JSON de salida.
- Contexto cross-repo (ver el backend desde el scan del frontend).
- Cambios en clasificación de runtime, batching o consolidación L1 (change `fullscan-parity`).
- Reescribir `prompt_hardening.md` y `devsecops.md` más allá de recibir el preámbulo.
