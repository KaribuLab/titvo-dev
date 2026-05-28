## MODIFIED Requirements

### Requirement: LangGraphAgent implements AbstractAgent port
The `LangGraphAgent` SHALL be the only agent implementation wired in `main.py`. There is no legacy mode or feature flag switching.

The `AnalyseCodeUseCase` SHALL execute a pre-scan RAG indexing check and a post-scan delta trigger **outside** the LangGraph graph, before and after calling `self.agent.invoke()` respectively. These steps SHALL NOT be implemented as LangGraph nodes.

#### Scenario: Pre-scan RAG check is outside the graph
- **WHEN** `AnalyseCodeUseCase.execute()` is called
- **THEN** the RAG index check and full indexing (if needed) run BEFORE `self.agent.invoke()` is called, with no changes to the LangGraph node topology

#### Scenario: Post-scan delta trigger is outside the graph
- **WHEN** `self.agent.invoke()` returns
- **THEN** the fire-and-forget delta trigger runs AFTER the graph result is obtained, with no changes to the LangGraph node topology
