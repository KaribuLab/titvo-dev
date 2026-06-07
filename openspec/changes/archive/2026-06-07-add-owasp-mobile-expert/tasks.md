## 1. Expert Registration

- [x] 1.1 Add `OwaspMobileNode` in `src/agent/src/code_analysis/infra/adapters/langgraph/nodes/expert_nodes.py` with `expert_name` set to `owasp_mobile`.
- [x] 1.2 Define mobile file patterns for Android, iOS, Flutter, and React Native artifacts in `OwaspMobileNode.get_file_patterns()`.
- [x] 1.3 Add `owasp_mobile` to `EXPERT_CLASSES` and `create_expert_nodes()` in the sequence after `OwaspWebNode` and before `DevSecOpsNode`.

## 2. Prompt Registry And Prompt Content

- [x] 2.1 Register `owasp_mobile` in `src/agent/src/code_analysis/prompts/__init__.py` so `PromptRegistry.get_expert_prompt()` and `list_experts()` include it.
- [x] 2.2 Create `src/agent/src/code_analysis/prompts/experts/owasp_mobile.md` with MASVS, MASTG, MASWE, and OWASP Mobile Top 10 2024 guidance.
- [x] 2.3 Include false-positive and severity guidance in the mobile prompt so CRITICAL/HIGH findings require concrete static evidence.
- [x] 2.4 Include RAG context usage rules in the mobile prompt consistent with the existing expert prompts.

## 3. Workflow And Behavior Verification

- [x] 3.1 Update workflow expectations so LangGraph compiles with six experts including `expert_owasp_mobile`.
- [x] 3.2 Verify the expert chain order is `prompt_hardening -> owasp_api -> owasp_web -> owasp_mobile -> devsecops -> code_vulnerabilities -> merge`.
- [x] 3.3 Verify the mobile expert consumes formatted file contents and optional RAG chunks without direct MCP tool access.

## 4. Tests

- [x] 4.1 Update expert node unit tests to cover `OwaspMobileNode.expert_name`, mobile file patterns, matching Android files, matching iOS files, and matching cross-platform mobile files.
- [x] 4.2 Update factory tests to expect six experts and include `owasp_mobile`.
- [x] 4.3 Update prompt registry tests to expect six prompts and validate the `owasp_mobile` prompt loads with OWASP mobile content.
- [x] 4.4 Update LangGraph workflow tests to expect the six-expert workflow and mobile expert ordering.
- [x] 4.5 Run the `src/agent` unit test suite and fix failures related to the new expert.

## 5. Documentation

- [x] 5.1 Update `docs/adding-experts.md` with the `owasp_mobile` expert registration and prompt pattern.
- [x] 5.2 Update `docs/prompts.md` with the mobile prompt scope and OWASP MASVS/MASTG/MASWE basis.
- [x] 5.3 Update `docs/architecture.md` with the six-expert LangGraph sequence.
