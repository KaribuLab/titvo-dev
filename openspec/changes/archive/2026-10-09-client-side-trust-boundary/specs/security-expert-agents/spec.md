## MODIFIED Requirements

### Requirement: Expert prompts are embedded in agent code

Expert system prompts SHALL be stored as markdown files inside
`src/agent/src/code_analysis/prompts/experts/` and loaded at runtime via `PromptRegistry` using
`importlib.resources`. The effective system message of every expert SHALL be the common preamble
(`prompts/system_prompt.md`: security boundary, anti-fabrication, runtime trust rules, severity
and suspicion policy, output format) followed by the expert's domain prompt, composed by
`PromptRegistry.compose_expert_prompt(name)`. Prompts MUST NOT be loaded from DynamoDB or external
configuration. `orchestrator_prompt.md` SHALL NOT exist.

#### Scenario: Prompt loaded from codebase

- **WHEN** the agent starts
- **THEN** the owasp-api expert uses the composition of `prompts/system_prompt.md` and
  `prompts/experts/owasp_api.md` bundled with the agent package

#### Scenario: Preamble precedes every expert

- **WHEN** any expert builds its `SystemMessage`
- **THEN** the message starts with the common preamble and contains the expert's domain prompt

#### Scenario: Prompt changes require deploy

- **WHEN** an expert prompt is modified
- **THEN** the change is versioned in the agent repository and deployed with the agent code

#### Scenario: Orchestrator prompt removed

- **WHEN** `PromptRegistry` is inspected
- **THEN** it exposes no `get_orchestrator_prompt` and the package has no `orchestrator_prompt.md`
