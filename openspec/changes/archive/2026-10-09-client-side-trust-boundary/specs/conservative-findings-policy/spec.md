## MODIFIED Requirements

### Requirement: CRITICAL and HIGH severity require explicit evidence

All experts SHALL classify findings as CRITICAL or HIGH only when the vulnerability is confirmed,
exploitable with the code as written, and backed by concrete evidence visible in the retrieved file
contents. What counts as "exposed" depends on the file runtime: in `server`, `infra` and `config`
runtimes a reference to an environment variable or CI secret by name is not evidence; in `browser`
and `mobile` runtimes any value present in the code, including environment references resolved at
build time, is exposed.

#### Scenario: Variable name is not a vulnerability

- **WHEN** code contains a variable named `apiKey` or `password` without an actual secret value and
  without an exposed build-time environment reference
- **THEN** no expert reports it as CRITICAL or HIGH

#### Scenario: Environment variable reference in server code is not a leak

- **WHEN** a `server` file references `os.environ["SECRET_KEY"]` or `process.env.API_KEY`
- **THEN** no expert reports it as CRITICAL or HIGH

#### Scenario: Build-time environment reference in browser code is exposed

- **WHEN** a `browser` file sends `import.meta.env.VITE_API_TOKEN` as its only API credential
- **THEN** the relevant expert reports it as a client-side exposed credential

#### Scenario: Confirmed hardcoded secret

- **WHEN** code contains a visible hardcoded signing key, cloud credential or backend API secret
- **THEN** the relevant expert reports it as CRITICAL with the evidence snippet

### Requirement: Uncertain findings are downgraded

When an expert lacks sufficient context to confirm exploitability, it SHALL still report the
finding as a suspicion: title prefixed `Sospecha:`, severity MEDIUM at most (enforced in code),
description ending with `Para confirmar:` and the concrete check. It MUST NOT escalate uncertain
findings to CRITICAL or HIGH and MUST NOT omit them.

#### Scenario: Missing external configuration context

- **WHEN** a potential vulnerability depends on external configuration not visible in the code
- **THEN** the expert reports it as `Sospecha:` with severity MEDIUM at most and names what to verify

#### Scenario: Suspicions are never dropped

- **WHEN** an expert identifies a risk it cannot confirm
- **THEN** the risk appears in the output as a suspicion instead of being omitted
