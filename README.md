# HOUSEGUARD — Defensive Smart-Home Security

HOUSEGUARD is the security and reliability layer for a local-first smart-home environment. The repository is intended to document and develop defensive monitoring, configuration validation and safe automation boundaries.

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
