# ΔΣ Guardian — Research Roadmap (2026)

**Last reviewed:** 2026-11-25  
**Historical origin:** Guardian was developed as an always-available personal AI and smart-environment system before persistent AI agents became a mainstream product category. This roadmap updates the direction without rewriting that history.

## Purpose

Guardian is a personal, persistent AI system that can understand ongoing context, use tools, observe a digital and physical environment, carry out bounded tasks, and learn from outcomes. It is not merely a chatbot, a smart-home dashboard, or a wrapper around one model provider.

The original ambition remains relevant: a system that is present over time, remembers, notices, plans, coordinates subsystems, and can interact with the world. Modern models and agent platforms change what can be delegated to the model; they do not remove the need for a coherent runtime, durable state, explicit permissions, observability, and evaluation.

## What was already present in the early Guardian

The historical code and documents show several ideas that should remain visible:
- a persistent/background supervision concept;
- an autonomous core with trigger events and task concepts;
- a central integration hub connecting chat, analysis, and autonomous work;
- contextual and experience-oriented memory;
- a smart-home controller with sensor and actuator abstractions;
- an MQTT integration direction;
- a separate deterministic simulation specification;
- vision, file, system, memory, and home tools;
- a user-facing chat and dashboard.

These are architectural intentions and code artifacts, not proof that every subsystem was complete or reliably integrated. Preserve the original files and commit history as the evidence.

## Current architectural framing

Think of Guardian as a set of cooperating planes, not one giant agent loop.

### 1. Interaction plane
Conversation, voice, notifications, user preferences, task handoff, and visible explanations. The interface should support both immediate requests and long-running work.

### 2. Agent runtime
A durable task lifecycle: receive intent, clarify when necessary, plan, select tools, execute bounded steps, observe results, recover from failures, and report completion. The runtime—not the model prompt—owns retries, timeouts, cancellation, idempotency, and task state.

### 3. Context and memory plane
Separate episodic history, user-approved durable preferences, current working context, system state, and learned procedural knowledge. Store provenance, timestamps, confidence, retention policy, and correction history. Memory should be inspectable and revisable, not an opaque transcript dump.

### 4. Tool and integration plane
Expose capabilities through typed, discoverable interfaces. MCP is one useful interoperability protocol, not the entire architecture. Keep adapters for local tools, Home Assistant, MQTT, files, operating-system services, and external APIs replaceable.

### 5. Environment plane
Represent the home and digital environment as stateful systems: entities, devices, rooms, sensors, actuators, events, capabilities, and constraints. Distinguish reported state, inferred state, desired state, and confirmed outcomes.

### 6. Policy and authorization plane
The model may propose actions; a deterministic policy layer decides what is permitted. Risk, reversibility, scope, confidence, and user consent determine whether an action is automatic, confirmation-gated, or disallowed. Emergency behavior must be explicit and independently testable.

### 7. Simulation and evaluation plane
A reproducible virtual environment should allow agents to act, receive feedback, and be evaluated without touching a real home. Preserve deterministic scenarios and event traces. Evaluate task completion, recovery, calibration, latency, cost, unnecessary actions, and user correction—not just conversational quality.

## Modernization priorities

1. **Reconstruct before replacing.** Map the actual Guardian modules, imports, entry points, duplicated assets, and current behavior. The old tree contains unfinished and conflicting fragments; document them rather than silently assuming they work.
2. **Replace obsolete model integrations deliberately.** The project currently references the retired `google-generativeai` Python SDK and an old OpenAI SDK pin. Google recommends `google-genai`; OpenAI recommends the Responses API for new agentic integrations. Migrate behind provider adapters, preserving a stable internal interface and testing each adapter independently.
3. **Make the model layer provider-neutral.** Model identifiers, context limits, multimodal support, tool calling, structured output, streaming, and reasoning settings belong in provider configuration/capability metadata—not scattered through business logic.
4. **Separate model reasoning from execution.** Use an explicit task state machine and typed tool contracts. Persist each action request, authorization decision, result, and follow-up observation.
5. **Treat MCP as an adapter.** Current Home Assistant documentation supports MCP over Streamable HTTP and SSE, with OAuth for authenticated servers. Keep protocol-specific behavior outside Guardian's core domain model.
6. **Unify memory concepts before choosing infrastructure.** Define what is remembered, why, for how long, how it is corrected, and how it is retrieved. A vector database alone is not a memory architecture.
7. **Bring simulation forward.** The old fixed-step, seeded simulation idea is strategically important. Make the environment contract independent of any one simulator or home platform.
8. **Preserve the original design lineage.** Keep dated notes, original prompts, old roadmaps, and failed approaches. Mark modern reinterpretations as later analysis.

## Research questions

- What should wake Guardian: user intent, environmental event, scheduled task, prediction, or an agent's own uncertainty?
- How can persistent memory remain useful without turning stale assumptions into facts?
- How should several specialized agents share context without creating circular delegation or untraceable decisions?
- What should count as evidence that an action succeeded in the physical world?
- How can Guardian learn routines while distinguishing correlation, user preference, and accidental repetition?
- Which capabilities should remain local, and which justify external models or services?
- How can a personal agent remain useful across model-provider changes and API deprecations?
- What is the smallest simulation that can test long-horizon agency and recovery?

## Current status and honesty rule

This is a research roadmap, not a claim that Guardian currently implements the architecture above. The source tree must be inspected before assigning completion status. Mark each capability as **present in source**, **partially implemented**, **design-only**, **obsolete**, or **unverified**. Do not infer functionality from class names, comments, roadmap checkboxes, or aspirational prompts.

## References

- [OpenAI Responses API migration guide](https://developers.openai.com/api/docs/guides/migrate-to-responses)
- [OpenAI tool integration guide](https://developers.openai.com/api/docs/guides/tools)
- [Google Gen AI Python SDK](https://github.com/googleapis/python-genai)
- [Google Gemini SDK migration information](https://ai.google.dev/gemini-api/docs/migrate)
- [Home Assistant MCP integration](https://www.home-assistant.io/integrations/mcp)

## Historical record

The original 2025 roadmap is preserved at [archive/GUARDIAN_PUBLIC_ROADMAP_2025.md](archive/GUARDIAN_PUBLIC_ROADMAP_2025.md). Its language and ambitions belong to that period and should not be mistaken for the current technical plan.
