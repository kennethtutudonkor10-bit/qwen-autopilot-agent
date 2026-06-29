# Judging Criteria → Where It's Met

A reviewer's map from the Track 4 rubric to concrete things in this repo.

## Technical Depth & Engineering (30%)
*"sophisticated use of QwenCloud APIs, custom skills, MCP integrations, algorithmic/engineering innovation"*

- **Multi-model Qwen usage** via Model Studio / DashScope (`backend/app/config.py`):
  `qwen-plus` (reasoning), `qwen3-coder-plus` (strict-JSON listings),
  `qwen-vl-plus` (scanned-manuscript vision).
- **Custom Qwen-Agent skills** as `BaseTool`s — `backend/app/skills/manuscript.py`.
- **MCP integration** config for the email tool — `backend/app/mcp_config.json`.
- **Strict-JSON + lenient-JSON parsing** and retries — `backend/app/qwen.py`.
- **Text/vision auto-routing** for scanned PDFs — `pipeline.ingest_auto`.

## Innovation & AI Creativity (30%)
*"architecture quality, modularity, scalability, error handling, non-trivial logic"*

- **Durable, resumable human-in-the-loop state machine** — `backend/app/orchestrator.py`
  (`docs/architecture.md`). Runs persist `pending_action` and resume after approval,
  surviving restarts / the Function Compute request lifecycle.
- **Clean layering**: `pipeline` (pure LLM logic) → `steps` (IO) → `orchestrator`
  (sequencing) → `skills` (agentic surface). The orchestrator imports no agent
  framework, so the production path stays lightweight.
- **Fail-soft notifications** — a delivery error can't crash a published run
  (`backend/app/notify.py`).

## Problem Value & Impact (25%)
*"real-world relevance, authentic business pain point, scalability, community adoption"*

- Automates the slowest part of running a real marketplace (GHAMAZON), with a
  visible operator console (the admin **Autopilot** tab).
- Reusable pattern for any intake → review → publish workflow.
- Open source (MIT).

## Presentation & Documentation (15%)
*"demo clarity, key logic visualized, clear docs, architecture docs"*

- **Agent trace is visualized** in the dashboard (each reasoning step), so judges
  see the logic, not just the output.
- `README.md`, `PLAN.md`, `docs/architecture.md`, `docs/DEPLOYMENT.md`,
  `docs/DEMO_SCRIPT.md`, and this file.

## Submission requirements

- [x] Public open-source repo + license (MIT)
- [ ] Proof of Alibaba Cloud deployment + code file using Alibaba Cloud APIs — `backend/app/aliyun/oss.py` (OSS) + DashScope in `orchestrator`/`qwen`; deploy via `docs/DEPLOYMENT.md`
- [x] Architecture diagram — `docs/architecture.md`
- [ ] ≤3-min public demo video — script in `docs/DEMO_SCRIPT.md`
- [ ] Text description — README + this map
- [x] Track identified — **Track 4: Autopilot Agent**
