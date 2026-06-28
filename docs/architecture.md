# Architecture — Qwen Autopilot Agent

## System overview

```
┌──────────────────────────────────────────────────────────────────┐
│  Admin Dashboard (React + Tailwind, in GHAMAZON / Cloudflare Pages)│
│   • Agent run inbox        • Live agent trace (SSE)                │
│   • Approve / edit / reject checkpoint cards                       │
└───────────────────────────┬──────────────────────────────────────┘
                            │ REST + SSE
┌───────────────────────────▼──────────────────────────────────────┐
│  Agent API — FastAPI                                               │
│  Deployed on  ➜  ALIBABA CLOUD FUNCTION COMPUTE                    │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │ Orchestrator                                                   ││
│  │  Qwen-Agent `Assistant` running a ReAct loop                   ││
│  │  Models via DashScope (Alibaba Cloud Model Studio):            ││
│  │   • qwen-plus         — reasoning / planning                   ││
│  │   • qwen3-coder-plus  — structured listing JSON                ││
│  │   • qwen-vl-plus      — read manuscript pages / covers         ││
│  │                                                                ││
│  │  Pipeline state machine:                                       ││
│  │   INTAKE → DRAFT → QUALITY → [await HITL] → PUBLISH            ││
│  │           → [await HITL] → NOTIFY → DONE                       ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                    │
│  Custom skills (qwen_agent BaseTool)      MCP clients              │
│   • ingest_manuscript                     • email server          │
│   • draft_listing                         • github server (opt)   │
│   • run_quality_checks                                            │
│   • publish_book                                                  │
│   • request_human_approval ──┐                                    │
└──────────────────────────────┼────────────────────────────────────┘
                               │ persist run state, set status=awaiting_approval
        ┌──────────────────────▼─────────┐     ┌────────────────────────┐
        │ Supabase (Postgres)            │     │ Alibaba Cloud OSS       │
        │  • books, users (GHAMAZON)     │     │  • manuscript files     │
        │  • agent_runs (new)            │     │  • generated covers     │
        └────────────────────────────────┘     └────────────────────────┘
```

## Human-in-the-loop = resumable runs

The agent does not block a thread waiting for a human. When a skill needs
approval it calls `request_human_approval`, which:

1. Writes the proposed action (the draft listing, or the pending email) into
   `agent_runs.pending_action`.
2. Sets `agent_runs.status = 'awaiting_approval'` and the current pipeline step.
3. Returns control — the HTTP request completes.

The admin dashboard polls / subscribes to `awaiting_approval` runs and renders a
checkpoint card. When the admin approves or edits, the frontend calls
`POST /runs/{id}/resume` with the (possibly edited) payload, and the orchestrator
**rehydrates the run from `agent_runs` and continues** from the saved step.

This makes the workflow durable across restarts and the Function Compute
request lifecycle — a production-readiness point Track 4 rewards.

## Pipeline state machine

| State | Skill | Next |
|---|---|---|
| `intake` | `ingest_manuscript` | `draft` |
| `draft` | `draft_listing` | `quality` |
| `quality` | `run_quality_checks` | `awaiting_approval` (HITL #1) |
| `awaiting_approval` | — (human) | `publish` on approve / `rejected` on reject |
| `publish` | `publish_book` | `awaiting_approval` (HITL #2) |
| `awaiting_approval` | — (human) | `notify` |
| `notify` | email + notification MCP | `done` |

## Alibaba Cloud surface (deployment proof)

| Concern | Alibaba Cloud service | Code |
|---|---|---|
| Inference | Model Studio / DashScope (Qwen) | `orchestrator.py`, `config.py` |
| Compute | Function Compute (custom container) | `backend/Dockerfile`, `deploy/s.yaml` |
| File storage | Object Storage Service (OSS) | `backend/app/aliyun/oss.py` |

## Data: `agent_runs` table (new, in Supabase)

```sql
create table agent_runs (
  id              uuid primary key default gen_random_uuid(),
  book_id         uuid references books(id),
  status          text not null default 'intake',   -- pipeline state
  step            text not null default 'intake',
  manuscript_uri  text,                              -- OSS object key
  draft_listing   jsonb,                             -- agent's proposed listing
  quality_flags   jsonb,
  pending_action  jsonb,                             -- what HITL is approving
  trace           jsonb default '[]',                -- agent reasoning steps for the UI
  created_at      timestamptz default now(),
  updated_at      timestamptz default now()
);
```
