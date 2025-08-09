# ΔΣ Guardian — UI Revamp (from scratch)

Goal: replace legacy templates with a modern SPA tailored to our agent loop and SmartHouse control. Eliminate chat message duplication and stream mismatch; provide clean task/vision/audio/home panels; rebuild login.

Tech:
- Frontend: React + Vite + TypeScript + Tailwind (Zustand store)
- Transport: SSE stream v2 (stream_id, chunk, tool_result, message_complete, final_summary)
- Routing: /app (Chat), /tasks, /vision, /audio, /home, /settings, /login

Core UX:
- Single bubble per stream_id, live incremental chunks + tool results, final summary (no history re-echo)
- Tasks page: background jobs (start/stop/view)
- Vision/Audio controls + settings
- Home devices (safe templates)
- System status strip (model, quota, presence)

Backend adjustments (minimal):
- Add final_summary event in SSE; suppress history echo while stream_id active
- System tasks: list, details, cancel endpoints

Phases:
1) Protocol v2 + adapter in backend (no UI change)
2) Scaffold SPA, Chat page with live stream bubble
3) Tasks/Vision/Audio pages + settings
4) Home dashboard
5) Replace legacy /chat with SPA (/app) and retire old templates

Notes:
- Keep branch ui-revamp until parity, then switch default
- Stubs for future modules are allowed (buttons/flags visible but disabled)
