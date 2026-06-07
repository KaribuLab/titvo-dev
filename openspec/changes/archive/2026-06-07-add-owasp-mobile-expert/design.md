## Context

The agent currently uses a LangGraph workflow that retrieves commit files, optionally enriches them with RAG context, runs five sequential expert nodes, and merges findings. The existing OWASP experts cover API and web risks, but mobile applications introduce security concerns that depend on platform-specific files and APIs.

Mobile coverage should fit the existing expert model: a concrete node class, a registered prompt loaded from package resources, file filtering by relevant patterns, structured JSON findings, and no direct MCP tool access from the expert.

## Goals / Non-Goals

**Goals:**

- Add `owasp_mobile` as a first-class expert alongside `owasp_api` and `owasp_web`.
- Ground the prompt in OWASP MASVS, MASTG, and MASWE for technical detection.
- Use OWASP Mobile Top 10 2024 as the reporting taxonomy when a finding maps cleanly to it.
- Cover native Android, native iOS, Flutter, and React Native source/configuration artifacts.
- Preserve the existing workflow style, prompt registry pattern, JSON output contract, RAG usage rules, and conservative severity policy.

**Non-Goals:**

- No runtime mobile testing, emulator execution, binary unpacking, APK/IPA decompilation, or dynamic instrumentation.
- No external prompt registry or runtime expert configuration.
- No changes to MCP retrieval, RAG indexing, report schema, merge behavior, or downstream API contracts.

## Decisions

### Decision: Name the expert `owasp_mobile`

Use `owasp_mobile` for the expert identifier, node suffix, prompt registry key, and prompt file name.

Rationale: the current expert names include `owasp_api` and `owasp_web`; `owasp_mobile` keeps the taxonomy consistent and predictable.

Alternative considered: `mobile_security`. This is technically broader, but less consistent with the existing OWASP expert naming line.

### Decision: Use MASVS/MASTG/MASWE for detection, Mobile Top 10 for reporting

The prompt should instruct the expert to detect mobile issues using OWASP MASVS, MASTG, and MASWE categories such as STORAGE, CRYPTO, AUTH, NETWORK, PLATFORM, CODE, RESILIENCE, and PRIVACY. Findings should map to OWASP Mobile Top 10 2024 categories when applicable.

Rationale: Mobile Top 10 is useful as a high-level risk taxonomy, but MASVS/MASTG/MASWE provide more actionable technical guidance for code/config review.

Alternative considered: base the prompt only on Mobile Top 10 2024. This would be simpler but too coarse for static code review.

### Decision: Add mobile file filtering with fallback

The expert should focus on mobile-specific paths and extensions, including Android manifests/config, Kotlin/Java, iOS plist/entitlements/Swift/Objective-C, Flutter/Dart, and React Native app/config files. The base fallback behavior remains: if no files match, analyze all files.

Rationale: targeted filtering keeps the prompt focused while still allowing analysis when path conventions are incomplete.

Alternative considered: analyze all files unconditionally. This maximizes recall but wastes context and increases overlap with generic experts.

### Decision: Place `owasp_mobile` after `owasp_web` and before `devsecops`

The updated sequence should be: prompt hardening, OWASP API, OWASP Web, OWASP Mobile, DevSecOps, code vulnerabilities.

Rationale: mobile is an application-domain expert like API and web. Running it before DevSecOps and generic code vulnerabilities helps preserve domain-specific findings before broader infrastructure/code review.

Alternative considered: put it last. This is simpler to append but makes mobile look like a generic afterthought rather than an OWASP peer.

## Risks / Trade-offs

- **Risk: Higher latency and token usage from a sixth expert** -> Mitigation: use mobile-specific file filtering and existing prompt truncation behavior.
- **Risk: False positives around missing mobile hardening controls** -> Mitigation: require concrete evidence in retrieved files, downgrade uncertain issues, and respect the conservative findings policy.
- **Risk: Duplicate findings with DevSecOps or code-vulnerabilities** -> Mitigation: use mobile-specific categories and rely on existing merge deduplication by path, line, and category.
- **Risk: Cross-platform framework files overlap with web analysis** -> Mitigation: focus `owasp_mobile` on mobile runtime implications such as local storage, platform bridges, deep links, permissions, and mobile network configuration.

## Migration Plan

Implement as an additive expert. Existing scans continue to use the same input/output envelope, with one additional expert contributing possible findings. Rollback is removing the expert registration, prompt registry entry, prompt file, and related tests.

## Open Questions

- Should React Native `.tsx` files always be included, or only when companion mobile config files such as `app.json`, `android/`, or `ios/` exist?
- Should resilience findings such as missing obfuscation/root detection be reported as findings by default, or only when the code explicitly disables protections?
