# Qwen Autopilot Agent — Build Plan

**Hackathon:** Global AI Hackathon Series with Qwen Cloud
**Track:** 4 — Autopilot Agent
**Deadline:** 2026-07-09 21:00 GMT
**Repo:** `qwen-autopilot-agent` (this repo) — the agent / hackathon submission
**Application surface:** `GHAMAZON` — Ghana's digital + print book marketplace (existing app the agent plugs into)

---

## 1. What we are building

An **autopilot agent that runs GHAMAZON's manuscript-intake-to-publishing workflow end-to-end**.

An author uploads a manuscript; the agent ingests it, drafts the entire store
listing, runs quality and appropriateness checks, then **pauses for a human
(admin) to approve or edit** before anything is published or sent to the author.

This is a real, open-ended business workflow — not a chatbot. It demonstrates the
three behaviours Track 4 asks for:

- **Ambiguous tasks** — raw manuscripts with no structured metadata.
- **External tool invocation** — Supabase (DB), Alibaba Cloud OSS (files), email, notifications.
- **Human-in-the-loop at critical decision points** — admin approval before publish + before author email.

### The pipeline

```
Author uploads manuscript (PDF/EPUB)
  1. INTAKE        agent ingests file (Qwen long-context / Qwen-VL reads it)
  2. DRAFT LISTING title polish, synopsis, back-cover copy, category, language,
                   keywords, suggested price
  3. QUALITY CHECK appropriateness + quality + duplicate flags
  ── HITL #1 ──    admin reviews auto-listing + flags → approve / edit / reject
  4. PUBLISH       write approved book row, move file to public bucket
  ── HITL #2 ──    admin approves the author notification before it goes out
  5. NOTIFY        email + in-app notification to author; run logged
```

Steps 1–4 reuse GHAMAZON infrastructure that already exists: the books table,
upload flow, **admin approval queue** (the HITL UI), `NotificationBell`, and the
email worker. The agent *feeds* those rather than rebuilding them.

---

## 2. Why this scores on the rubric

| Criterion (weight) | How we hit it |
|---|---|
| **Technical Depth & Engineering (30%)** | Built on **Qwen-Agent** with custom `BaseTool` skills + **MCP** servers. Multi-model routing: `qwen3.7-max` reasoning, `qwen3.7-plus` structured output + vision for scanned manuscripts. DashScope (Alibaba Cloud) API throughout. |
| **Innovation & AI Creativity (30%)** | Typed pipeline state machine, ReAct planning loop, **resumable human-in-the-loop** (agent persists state and resumes on approval), retries + guardrails, modular skill registry. |
| **Problem Value & Impact (25%)** | Automates the slowest part of running a real marketplace; reusable for any intake→review→publish workflow. Live product, not a toy. |
| **Presentation & Documentation (15%)** | Admin dashboard *visualizes the agent's reasoning and each checkpoint* (judges want "key logic visualized") + architecture diagram + this plan. |

---

## 3. Decisions (locked, override anytime)

- **Backend language:** Python + Qwen-Agent (native MCP / skills / function-calling).
- **State store:** reuse GHAMAZON **Supabase** for book/user data and agent run-state — fastest path in 11 days.
- **Alibaba Cloud proof:** agent backend deployed on **Function Compute**, inference via **DashScope (Qwen)**, manuscript files on **OSS**. (`backend/app/aliyun/` is the code file that demonstrates Alibaba Cloud APIs.)
- **AI provider:** **Qwen only** inside the agent path. (GHAMAZON's existing Gemini copilot is out of scope for the submission; migrate or leave it as a separate site feature.)

---

## 4. Architecture

See [`docs/architecture.md`](docs/architecture.md).

```
React admin dashboard (GHAMAZON, Cloudflare Pages)
        │  REST / SSE  (live agent trace + approve/edit checkpoints)
        ▼
FastAPI Agent API  ── deployed on Alibaba Cloud Function Compute ──
        │
   Qwen-Agent Assistant (ReAct loop)  ── DashScope: qwen3.7-max / qwen3.7-plus (vision)
        │
   Custom skills (BaseTool)            MCP clients
   • ingest_manuscript (Qwen-VL)       • github (optional)
   • draft_listing                     • email
   • run_quality_checks
   • publish_book
   • request_human_approval ─► persists run, resumes on approval
        │
   Supabase (books, users, agent_runs)      Alibaba Cloud OSS (manuscripts, covers)
```

---

## 5. Repo structure

```
qwen-autopilot-agent/
├── PLAN.md                      ← this file
├── README.md
├── LICENSE                      ← MIT (open-source requirement)
├── docs/
│   ├── architecture.md
│   └── DEMO_SCRIPT.md           (added day 9)
├── backend/
│   ├── app/
│   │   ├── main.py              FastAPI + SSE endpoints
│   │   ├── config.py            settings / env
│   │   ├── orchestrator.py      Qwen-Agent Assistant + pipeline state machine
│   │   ├── store.py             Supabase run/state persistence
│   │   ├── skills/              custom BaseTool skills
│   │   ├── aliyun/              Alibaba Cloud APIs (OSS) — deployment proof
│   │   └── mcp_config.json      MCP servers (email, github)
│   ├── requirements.txt
│   ├── Dockerfile               Function Compute custom-container image
│   └── .env.example
└── deploy/
    └── s.yaml                   Serverless Devs config for Function Compute
```

---

## 6. Timeline (today 2026-06-28 → 2026-07-09 21:00 GMT)

| Day | Date | Milestone |
|---|---|---|
| 1 | Jun 28–29 | Alibaba Cloud + Model Studio account, hackathon credits via coupon, DashScope key, "hello Qwen" call. **Scaffold committed (this step).** |
| 2 | Jun 30 | Qwen-Agent orchestrator + skill stubs runnable; ReAct loop produces a draft listing from a sample manuscript (CLI). |
| 3 | Jul 1 | `ingest_manuscript` (Qwen-VL on a PDF) + `draft_listing` + `run_quality_checks` end-to-end. |
| 4 | Jul 2 | HITL engine: pause / persist / resume on approval. `agent_runs` table + Supabase wiring. |
| 5 | Jul 3 | `publish_book` + email/notification MCP; OSS upload of manuscript + cover. |
| 6 | Jul 4 | GHAMAZON admin dashboard: agent run inbox + live trace + approve/edit checkpoint UI. |
| 7 | Jul 5 | Deploy backend to Function Compute; full run on cloud against staging Supabase. |
| 8 | Jul 6 | Hardening: retries, guardrails, error handling; one polished end-to-end demo scenario. |
| 9 | Jul 7 | Architecture diagram + README + DEMO_SCRIPT.md. Full dry run. |
| 10 | Jul 8 | Record + edit ≤3-min demo video, upload public (YouTube). Optional blog post. |
| 11 | Jul 9 | Buffer + **submit on Devpost before 21:00 GMT.** |

---

## 7. Submission checklist

- [ ] Public, open-source repo + license visible at top of repo page *(LICENSE present)*
- [ ] Proof of Alibaba Cloud deployment + code file using Alibaba Cloud APIs (`backend/app/aliyun/`)
- [ ] Architecture diagram in repo
- [ ] ≤3-min demo video, public (YouTube/Vimeo/FB)
- [ ] Text description of features/functionality
- [ ] Track identified: **Track 4 — Autopilot Agent**
- [ ] *(Optional)* blog post for the Blog Post Award

---

## 8. References

- DashScope OpenAI-compatible API — https://www.alibabacloud.com/help/en/model-studio/compatibility-of-openai-with-dashscope
- Model Studio supported models — https://www.alibabacloud.com/help/en/model-studio/models
- Qwen-Agent framework — https://github.com/QwenLM/Qwen-Agent
