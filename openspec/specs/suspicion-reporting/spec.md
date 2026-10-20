# suspicion-reporting Specification

## Purpose

Reporte explícito de sospechas: cuando un experto no puede confirmar la explotabilidad, el hallazgo se reporta con prefijo `Sospecha:`, severidad acotada a MEDIUM (reforzado en código por `BaseExpertNode`) y una verificación concreta `Para confirmar:`; la consolidación L2 conserva el marcador solo cuando todas las fuentes son sospechas.

## Requirements

### Requirement: Suspicions are reported with an explicit marker

When an expert cannot confirm exploitability because the evidence lives outside the analysed
files (another repository, provider configuration, `unknown` runtime), it SHALL still report the
finding. The title MUST start with `Sospecha:`, the severity MUST be at most MEDIUM and the
description MUST end with a sentence starting with `Para confirmar:` naming the concrete check.

#### Scenario: Backend not in repository

- **WHEN** a `browser` file calls an API whose authorization cannot be verified from the repo
- **THEN** the issue title starts with `Sospecha:`, severity is MEDIUM or LOW and the description
  contains `Para confirmar:`

### Requirement: Suspicion severity is capped in code

`BaseExpertNode` SHALL downgrade to MEDIUM any parsed issue whose title starts with `Sospecha:`
(case and accent insensitive) and whose severity is HIGH or CRITICAL, recording
`metadata.severity_capped = true`.

#### Scenario: Model returns a HIGH suspicion

- **WHEN** the model answers `{"title": "Sospecha: token expuesto", "severity": "HIGH", ...}`
- **THEN** the resulting `ExpertIssue` has severity `MEDIUM` and `metadata.severity_capped` is `true`

#### Scenario: Confirmed finding is untouched

- **WHEN** the model answers a HIGH issue whose title does not start with `Sospecha:`
- **THEN** the severity stays HIGH and `severity_capped` is absent

### Requirement: Consolidation preserves the marker only for pure suspicions

The L2 consolidation prompt SHALL instruct the model to keep the `Sospecha:` prefix only when every
merged source is a suspicion; when a suspicion is merged with a confirmed finding the confirmed
title prevails and the severity is the maximum of the sources.

#### Scenario: Suspicion merged with confirmed finding

- **WHEN** a `Sospecha:` MEDIUM finding and a confirmed HIGH finding on the same root cause are
  consolidated
- **THEN** the output title has no `Sospecha:` prefix and the severity is HIGH

#### Scenario: Two suspicions merged

- **WHEN** two `Sospecha:` findings on the same root cause are consolidated
- **THEN** the output title keeps the `Sospecha:` prefix and the severity is at most MEDIUM
