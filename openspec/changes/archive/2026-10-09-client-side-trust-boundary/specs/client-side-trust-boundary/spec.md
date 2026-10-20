## ADDED Requirements

### Requirement: Experts apply runtime-specific trust rules

The effective system prompt of every expert SHALL explain the `[runtime: <label>]` header and
SHALL state that in `browser` and `mobile` runtimes every value present in the code is public:
string literals, `import.meta.env.*`, `process.env.VITE_*`, `REACT_APP_*`, `NEXT_PUBLIC_*`,
`VUE_APP_*`, `EXPO_PUBLIC_*`, configuration constants and signing material. In `server`, `infra`
and `config` runtimes, references to environment variables or CI secrets by name MUST NOT be
reported as leaks. In `unknown` runtime the expert SHALL apply the stricter rule and mark the
finding as a suspicion when severity depends on the runtime.

#### Scenario: Environment variable in browser code is a finding

- **WHEN** a file labelled `[runtime: browser]` sends `import.meta.env.VITE_API_TOKEN` in an
  `Authorization` header
- **THEN** the expert reports the exposed credential instead of treating the env reference as safe

#### Scenario: Environment variable in server code is not a finding

- **WHEN** a file labelled `[runtime: server]` reads `process.env.API_KEY`
- **THEN** no expert reports it as a leak

#### Scenario: No expert prompt keeps the absolute env-var exclusion

- **WHEN** the expert prompts are loaded
- **THEN** none of them contains the sentence "Environment variable references for secrets → NOT a
  finding"

### Requirement: Client-side secret based authentication is reported without seeing the server

`owasp_api`, `owasp_web` and `owasp_mobile` SHALL report, for files in `browser`/`mobile` runtime,
HTTP requests whose only authentication is a static application credential, a signature computed
in the client with material present in the client, or a token stored in `localStorage`/
`AsyncStorage`, when no user-bound credential (session cookie, bearer obtained after login,
identity token) accompanies the request. The finding MUST be reported even when the server code is
not in the repository; its description SHALL state what should be verified server-side.

#### Scenario: Static token plus client-computed signature

- **WHEN** a `browser` file sends `Authorization: Bearer <constant>` and
  `X-Signature: hmac(payload, KEY_IN_BUNDLE)` and no cookie or login token
- **THEN** the expert reports "Autenticación basada en secretos del lado cliente" with severity
  CRITICAL (signing key exposed) and the description names the server-side check to verify

#### Scenario: Static token only

- **WHEN** a `browser` file authenticates its API calls solely with a constant token and no
  user-bound credential
- **THEN** the expert reports the finding with severity HIGH

#### Scenario: Session-bound request is not reported

- **WHEN** a `browser` file sends requests with `credentials: 'include'` or a bearer obtained from
  a login response
- **THEN** no client-side-authentication finding is reported for that request

### Requirement: Client credentials are rated by what they grant

For hardcoded or environment-provided credentials in `browser`/`mobile` runtime the expert SHALL
rate: a public identifier of a third-party embed (chat widget, analytics, maps, captcha site key)
as LOW when domain restriction is the expected control, or MEDIUM as a suspicion asking to verify
domain restriction and that the token does not grant the provider's API; a credential that
authenticates against the application's own backend or a metered third-party API as HIGH; a
signing key, JWT secret, private key or cloud provider credential as CRITICAL.

#### Scenario: Chat widget token

- **WHEN** a `browser` file contains `window.TalkCenter = { token: '<hex>' }` for an embedded chat
- **THEN** the finding is at most MEDIUM, its title starts with `Sospecha:` and the description asks
  to verify domain restriction and API scope in the provider

#### Scenario: HMAC key in bundle

- **WHEN** a `browser` file contains a constant used as key in an HMAC computation
- **THEN** the finding is CRITICAL

### Requirement: Test fixtures with placeholder secrets are LOW

In `test` runtime, secrets that look like placeholders (`test`, `dummy`, `example`, `changeme`,
`sk-test-…`, repeated characters) SHALL be rated LOW; secrets with a real format (AWS `AKIA…`,
signed JWT, PEM private key) SHALL be treated as in `server` runtime.

#### Scenario: Placeholder in fixture

- **WHEN** a `test` file contains `API_KEY = "test-key-123"`
- **THEN** the finding, if any, is LOW

#### Scenario: Real-looking key in fixture

- **WHEN** a `test` file contains `AKIAIOSFODNN7EXAMPLE` with a matching secret key
- **THEN** the finding is rated as a hardcoded credential (CRITICAL)
