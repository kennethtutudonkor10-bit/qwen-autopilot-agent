# Qwen Autopilot Agent

> **Global AI Hackathon Series with Qwen Cloud — Track 4: Autopilot Agent**

An autopilot agent that runs a real marketplace's **manuscript-intake → publishing**
workflow end-to-end. An author uploads a manuscript; the agent ingests it, drafts
the entire store listing, runs quality and appropriateness checks, then **pauses
for a human to approve or edit** before anything is published or sent to the author.

It is the publishing brain behind [GHAMAZON](https://ghamazon.pages.dev), Ghana's
digital + print book marketplace.

## Why it fits Track 4

- **Ambiguous tasks** — raw manuscripts with no structured metadata.
- **External tool invocation** — Supabase, Alibaba Cloud OSS, email, notifications.
- **Human-in-the-loop** — admin approval before publish and before author email.

## Tech

- **Qwen-Agent** framework (Function Calling + MCP) — https://github.com/QwenLM/Qwen-Agent
- **Qwen models via DashScope** (Alibaba Cloud Model Studio): `qwen-plus`, `qwen3-coder-plus`, `qwen-vl-plus`
- **FastAPI** backend, deployed on **Alibaba Cloud Function Compute**
- **Alibaba Cloud OSS** for manuscript + cover files
- **Supabase** (Postgres) for book/user data and durable agent run-state
- **React + Tailwind** admin dashboard (lives in the GHAMAZON app)

## Repo layout

See [`PLAN.md`](PLAN.md) and [`docs/architecture.md`](docs/architecture.md).

```
backend/   FastAPI + Qwen-Agent orchestrator, skills, Alibaba Cloud integration
docs/      architecture + demo script
deploy/    Serverless Devs config for Function Compute
```

## Local development

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in DASHSCOPE_API_KEY, OSS_*, SUPABASE_*
uvicorn app.main:app --reload --port 8000
```

Then drive a run:

```bash
curl -X POST localhost:8000/runs \
  -F "file=@samples/manuscript.pdf" \
  -F "author_id=<uuid>"
```

## License

MIT — see [LICENSE](LICENSE).
