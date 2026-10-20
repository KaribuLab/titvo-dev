## MODIFIED Requirements

### Requirement: Expert file filtering by relevance

Each expert SHALL select a file when the intersection between the file's `runtimes` and the
expert's runtime set is non-empty. Path or extension patterns MUST NOT be used. The mapping SHALL
be:

| Expert | Runtimes |
|---|---|
| `prompt_hardening` | all |
| `code_vulnerabilities` | all |
| `owasp_api` | `server`, `browser`, `unknown`, `config` |
| `owasp_web` | `browser`, `server`, `unknown` |
| `owasp_mobile` | `mobile` |
| `devsecops` | `infra`, `config`, `test` |

If the selection yields no files, the expert MUST NOT run and MUST record
`expert_metadata[<name>] = {"files_analyzed": 0, "skipped": true}`. There is no fallback to all
files.

#### Scenario: DevSecOps expert file filtering

- **WHEN** the devsecops expert is invoked and files with runtime `infra`, `config` or `test` exist
- **THEN** it receives only those files

#### Scenario: Frontend HTTP client is analyzed by owasp_api in both scan modes

- **WHEN** a commit scan contains only `src/services/apiClient.ts` (runtimes `["browser"]`) and a
  full scan contains that file plus 200 server files
- **THEN** `owasp_api` receives `src/services/apiClient.ts` in both scans

#### Scenario: Multi-runtime file reaches every matching expert

- **WHEN** a file has runtimes `["mobile", "browser"]`
- **THEN** both `owasp_mobile` and `owasp_web` receive it

#### Scenario: No fallback when nothing matches

- **WHEN** the owasp_mobile expert is invoked and no file has runtime `mobile`
- **THEN** it performs no LLM call and `expert_metadata.owasp_mobile.skipped` is `true`

### Requirement: OWASP mobile expert filters mobile-relevant files

The `owasp_mobile` expert SHALL analyze only files whose `runtimes` include `mobile`, as produced
by the runtime classifier from Android, iOS, Flutter and React Native signals and from the project
profile. If no file has runtime `mobile`, the expert SHALL be skipped.

#### Scenario: Android files are selected

- **WHEN** retrieved files include `AndroidManifest.xml`, `network_security_config.xml`, `*.kt`,
  `*.java` with Android imports, or Gradle files
- **THEN** they are classified `mobile` and the `owasp_mobile` expert receives them

#### Scenario: iOS files are selected

- **WHEN** retrieved files include `Info.plist`, `*.entitlements`, `*.swift`, `*.m`, `*.mm`,
  `Podfile`, or `Package.swift`
- **THEN** they are classified `mobile` and the `owasp_mobile` expert receives them

#### Scenario: Cross-platform mobile files are selected

- **WHEN** retrieved files include `pubspec.yaml`, `*.dart`, or `*.tsx`/`*.jsx` that import
  `react-native`/`expo` or belong to a `mobile_js` project profile
- **THEN** they are classified `mobile` and the `owasp_mobile` expert receives them

#### Scenario: Web React files are not sent to the mobile expert

- **WHEN** a `*.tsx` file imports `react` but not `react-native` and the profile is not `mobile_js`
- **THEN** it is classified `browser` and the `owasp_mobile` expert does not receive it
