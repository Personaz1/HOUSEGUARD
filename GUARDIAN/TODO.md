# Guardian — Current Research Queue

**Reviewed:** 2026-11-25  
This is a research and reconstruction queue, not a promise that every item will be implemented. Preserve historical artifacts and mark findings with evidence.

## 1. Reconstruct the original system
- [ ] Build a source map: entry points, imports, modules, data stores, background tasks, and external services.
- [ ] Identify merge-conflict remnants, duplicate assets, dead paths, and contradictory architecture descriptions.
- [ ] Trace the original user-facing application from request to model to tool to response.
- [ ] Trace one smart-home event from sensor input through policy and action to observed outcome.
- [ ] Classify each subsystem: present in source, partially implemented, design-only, obsolete, or unverified.
- [ ] Record the commit and files supporting each conclusion.

## 2. Modernize model integrations
- [ ] Inventory all OpenAI and Gemini imports and call sites.
- [ ] Replace the deprecated `google-generativeai` integration with the maintained `google-genai` SDK after mapping behavior.
- [ ] Review the old OpenAI SDK pin and migrate deliberately to the current Responses API where appropriate.
- [ ] Define a provider-neutral interface for streaming, multimodal input, structured output, tool calls, cancellation, and usage metadata.
- [ ] Keep model names and provider-specific capabilities in configuration.
- [ ] Preserve a fallback strategy that does not assume two providers have identical capabilities.

## 3. Reconstruct agency and continuity
- [ ] Separate event ingestion, task planning, tool execution, memory updates, and user communication.
- [ ] Define durable task states, retries, timeouts, cancellation, and recovery.
- [ ] Separate episodic history, user-approved memory, working context, world state, and procedural knowledge.
- [ ] Record source, timestamp, confidence, and correction lineage for memory items.
- [ ] Define wake-up triggers and conditions under which Guardian should remain idle or ask the user.

## 4. Environment and simulation
- [ ] Compare Guardian's MQTT contract with SMARTHOUSE's current event and device models.
- [ ] Decide whether Home Assistant should be the primary device adapter or one of several.
- [ ] Treat MCP as an interoperability boundary, not as Guardian's internal architecture.
- [ ] Formalize desired, reported, inferred, and confirmed device state.
- [ ] Preserve the fixed-step deterministic simulation concept and define portable scenario fixtures.
- [ ] Add long-horizon scenarios for delayed events, missing sensors, conflicting observations, and recovery.

## 5. Evaluation questions
- [ ] Can Guardian resume a task after process restart?
- [ ] Can it explain why it woke and which evidence triggered it?
- [ ] Can it distinguish an issued command from a confirmed physical outcome?
- [ ] Does it know when its memory or world model may be stale?
- [ ] Can it abstain, ask, or escalate when confidence is insufficient?
- [ ] Can the same scenario be replayed deterministically?

## Preserved historical material
- [AGI_RESEARCH_NOTES.md](AGI_RESEARCH_NOTES.md) — historical significance and questions for future AI readers.
- [GUARDIAN_PUBLIC_ROADMAP.md](GUARDIAN_PUBLIC_ROADMAP.md) — updated 2026 research roadmap.
- [archive/GUARDIAN_PUBLIC_ROADMAP_2025.md](archive/GUARDIAN_PUBLIC_ROADMAP_2025.md) — original roadmap.
- [archive/TODO_2025.md](archive/TODO_2025.md) — original task list.

## Working rule

Do not rewrite the original project into a fashionable agent framework. First understand what was attempted and why. Modernize obsolete interfaces where there is a concrete benefit, but preserve the historical architecture as a source of research evidence.
