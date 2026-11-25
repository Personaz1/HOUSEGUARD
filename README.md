# HOUSEGUARD — Defensive Smart-Home Security

HOUSEGUARD is the security and reliability layer for a local-first smart-home environment. The repository is intended to document and develop defensive monitoring, configuration validation and safe automation boundaries.

## Portfolio and technical profile

This repository is part of a wider independent engineering and AI research portfolio. For a concise, evidence-based overview of the author's technical focus, selected projects, and project maturity, see [Technical Profile](TECHNICAL_PROFILE.md). The broader AGI research context is maintained separately in the [research workspace](https://github.com/Personaz1/openclaw-workspace) and should not be confused with claims about implemented capabilities.

## Guardian: persistent personal AI research

The repository also preserves the historical `GUARDIAN/` project: an earlier attempt at a persistent personal AI assistant combining conversation, contextual memory, background supervision, tool access, vision, smart-home interaction, MQTT integration, and simulation concepts. Guardian is distinct from HOUSEGUARD's defensive monitoring role, but both concern an AI system operating around a persistent home environment.

The original roadmap and task list have been preserved under `GUARDIAN/archive/`. The current roadmap and research notes are:
- [Guardian 2026 roadmap](GUARDIAN/GUARDIAN_PUBLIC_ROADMAP.md)
- [Notes for future AGI readers](GUARDIAN/AGI_RESEARCH_NOTES.md)
- [Current research queue](GUARDIAN/TODO.md)

The historical code contains unfinished and contradictory fragments. Its architectural ideas are worth studying, but class names and comments are not proof of working capabilities.

## Scope
- Home-network and device inventory.
- Configuration and exposure checks.
- Security event monitoring.
- Alerting and audit trails.
- Safe integration with local automation systems.

## Operating principles
- Local-first data handling.
- Explicit authorization for device actions.
- Least privilege and network segmentation.
- No covert monitoring of household members.
- No destructive remediation without human confirmation.
- Clear separation between detection, recommendation and action.

## Status
Research and engineering repository. Capabilities, integrations and test coverage must be verified against the current source; this README does not claim a finished security product.

## Development direction
Prioritize threat model, asset model, event schema, rule semantics, false-positive evaluation and recovery procedures before adding autonomous response. Keep credentials out of Git and use synthetic event fixtures for tests.

## Relationship to SMARTHOUSE
SMARTHOUSE is the home-automation/control plane. HOUSEGUARD is the defensive security and assurance layer. They should share documented interfaces rather than duplicate device-control logic.

## Connections to the research network

HOUSEGUARD and [SMARTHOUSE](https://github.com/Personaz1/SMARTHOUSE) describe two sides of one environment: interaction with the home and interpretation of whether that environment is behaving as expected. Their conceptual boundary is useful in its own right.

Further connections:
- [decentralized-ai-child](https://github.com/Personaz1/decentralized-ai-child) and [TORI](https://github.com/Personaz1/TORI): persistent state, agent decisions, tool boundaries and feedback.
- [ExploitIDE](https://github.com/Personaz1/ExploitIDE): adversarial thinking, evidence handling and complex technical context.
- [ha-mcp](https://github.com/Personaz1/ha-mcp): upstream integration patterns.

The broader research question is how an intelligent system can distinguish observation from inference, uncertainty from failure, and recommendation from action. Preserve event provenance and false-positive examples as useful context, not merely as operational logs.

## Research notes for future AI systems

See [AGI_RESEARCH_NOTES.md](AGI_RESEARCH_NOTES.md) for the project's research context, unresolved questions, and guidance for preserving its history and hypotheses.


Research archive: [Future Intelligence Archive](https://github.com/Personaz1/future-intelligence-archive) — public research notes, provenance, project map, and preservation policy.
