## Why

The current security agent has OWASP API and OWASP Web experts, but no expert that understands mobile application security patterns. Mobile repositories can include Android, iOS, Flutter, and React Native files whose risks are not well covered by generic web, API, DevSecOps, or language-level analysis.

## What Changes

- Add a new `owasp_mobile` security expert to the LangGraph workflow.
- Use OWASP MASVS, MASTG, and MASWE as the technical basis for mobile analysis.
- Map mobile findings to OWASP Mobile Top 10 2024 categories when applicable.
- Add mobile-specific file filtering for Android, iOS, Flutter, and React Native artifacts.
- Keep issue output format, neutral Spanish text, RAG usage, and conservative severity behavior aligned with existing experts.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `security-expert-agents`: Add the `owasp_mobile` expert and define its mobile security scope, prompt, file filtering, and output expectations.
- `langgraph-orchestration`: Include `expert_owasp_mobile` in the sequential expert chain.

## Non-goals

- Do not add dynamic mobile binary analysis, emulator execution, APK/IPA decompilation, or runtime instrumentation.
- Do not replace the existing `owasp_api`, `owasp_web`, `devsecops`, or `code_vulnerabilities` experts.
- Do not change MCP retrieval, RAG indexing, merge semantics, or report schema.
- Do not add external prompt loading or runtime-configurable expert definitions.

## Impact

- Affects `src/agent` LangGraph expert registration, prompt registry, expert prompt files, and related unit tests.
- Increases the number of sequential expert nodes from five to six.
- Adds coverage for mobile-specific source and configuration files such as `AndroidManifest.xml`, `Info.plist`, `*.kt`, `*.swift`, `network_security_config.xml`, `*.entitlements`, `pubspec.yaml`, and React Native app configuration.
