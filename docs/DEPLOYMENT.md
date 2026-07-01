# Deployment Runbook — Alibaba Cloud

End-to-end steps to take the Qwen Autopilot Agent from this repo to a live
backend on Alibaba Cloud, wired to GHAMAZON.

Prerequisites: an Alibaba Cloud account (with the hackathon cloud credits applied)
and the existing GHAMAZON Supabase project.

## Which deployment path?

Two options — both put the backend on Alibaba Cloud (the deployment proof):

- **A. VM — ECS or Simple Application Server (SWAS)** ← *recommended, simplest.*
  Just `git clone` + `uvicorn` on a small Ubuntu VM. No Docker, no registry.
  This is what the Alibaba team's session demoed. See **§5A**.
- **B. Function Compute (serverless container)** — build a Docker image, push to
  ACR, `s deploy`. More moving parts. See **§5B**.

> Note: the Alibaba team stated Qwen Cloud model usage is **mandatory** and
> Alibaba Cloud deployment is **strongly encouraged**. Do the VM deploy — it's
> cheap and quick — so the "proof of deployment" box is unambiguously ticked.

> Voucher tip: in the console billing settings, **disable the Free Tier/Quota
> toggle** so your hackathon voucher/credits are applied instead of free quota.
> You do **not** need the voucher to build, verify, or demo — the free 1M tokens
> on signup are plenty. Disable free quota only when you want the voucher/credits
> consumed. If the toggle is missing, email the organizers your **UID**.

---

## 1. Get a Qwen (DashScope) API key

1. Open **Model Studio** (Alibaba Cloud Console → Model Studio / Bailian).
2. Activate the service and **create an API key**.
3. Note your region. The OpenAI-compatible base URL is region-specific, e.g.
   Singapore: `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`.

Verify locally before anything else:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DASHSCOPE_API_KEY=sk-xxxx
python scripts/run_local.py samples/sample_manuscript.txt
```

You should see a drafted listing + quality flags. If this works, the Qwen
integration is good and the rest is plumbing.

## 2. Create an OSS bucket (manuscripts + covers)

1. Console → **Object Storage Service (OSS)** → create a bucket
   (e.g. `ghamazon-manuscripts`) in the **same region** as your function.
2. Create a **RAM user** with an AccessKey ID/Secret and grant it
   `AliyunOSSFullAccess` (or a bucket-scoped policy).
3. Record: `OSS_ACCESS_KEY_ID`, `OSS_ACCESS_KEY_SECRET`, `OSS_ENDPOINT`
   (e.g. `https://oss-ap-southeast-1.aliyuncs.com`), `OSS_BUCKET`.

## 3. Run the database migration

Apply `backend/migrations/001_agent_runs.sql` to the GHAMAZON Supabase project
(SQL editor or `supabase db push`). This creates the `agent_runs` table + the
admin-read RLS policy the dashboard uses.

## 5A. Deploy on a VM — ECS or Simple Application Server (recommended)

No Docker, no registry — just clone and run `uvicorn`. This is the fastest way
to get a public URL on Alibaba Cloud.

1. Create a **Simple Application Server** (or a small **ECS** instance), image
   **Ubuntu 22.04**, in your region (Singapore for the `-intl` endpoint).
2. In the instance's **firewall / security group**, open your app port (`8000`).
3. SSH in and set it up:
   ```bash
   sudo apt update && sudo apt install -y python3-pip git
   git clone https://github.com/kennethtutudonkor10-bit/qwen-autopilot-agent.git
   cd qwen-autopilot-agent/backend
   pip3 install -r requirements.txt
   cp .env.example .env && nano .env      # fill DASHSCOPE_API_KEY, OSS_*, SUPABASE_*
   python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000   # quick test
   ```
4. Visit `http://<server-ip>:8000/` — you should see the **Agent Console**;
   `http://<server-ip>:8000/healthz` returns `{"status":"ok"}`. **That URL is your
   proof of deployment** (screenshot it + the SWAS/ECS console).
5. Make it a durable service with systemd — `/etc/systemd/system/qwen-agent.service`:
   ```ini
   [Unit]
   Description=Qwen Autopilot Agent
   After=network.target
   [Service]
   WorkingDirectory=/root/qwen-autopilot-agent/backend
   EnvironmentFile=/root/qwen-autopilot-agent/backend/.env
   ExecStart=/usr/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   Restart=always
   [Install]
   WantedBy=multi-user.target
   ```
   ```bash
   sudo systemctl enable --now qwen-agent && sudo systemctl status qwen-agent
   ```

Then skip to **§6** to point GHAMAZON at `http://<server-ip>:8000`.

---

## 5B. Alternative: Function Compute (serverless container)

### Build & push the container image

Function Compute runs a custom container. Push to Alibaba Container Registry (ACR):

```bash
# from repo root
cd backend
docker build -t qwen-autopilot-agent .

# tag + push to your ACR namespace (create one in the ACR console first)
docker tag qwen-autopilot-agent \
  registry.ap-southeast-1.cr.aliyuncs.com/<your-namespace>/qwen-autopilot-agent:latest
docker login registry.ap-southeast-1.cr.aliyuncs.com
docker push \
  registry.ap-southeast-1.cr.aliyuncs.com/<your-namespace>/qwen-autopilot-agent:latest
```

Update the `image:` line in `deploy/s.yaml` to match this tag.

### Deploy to Function Compute

```bash
npm i -g @serverless-devs/s

# provide secrets via env (s.yaml reads ${env.*})
export DASHSCOPE_API_KEY=sk-xxxx
export OSS_ACCESS_KEY_ID=... OSS_ACCESS_KEY_SECRET=...
export SUPABASE_URL=https://<proj>.supabase.co
export SUPABASE_SERVICE_ROLE_KEY=...
export RESEND_API_KEY=...           # optional (email)

s deploy
```

`s deploy` prints the function's **HTTP trigger URL**. That is your agent API base.

Smoke test:

```bash
curl https://<function-url>/healthz          # -> {"status":"ok",...}
```

## 6. Point GHAMAZON at the agent

In the frontend environment (Cloudflare Pages project settings, or `.env`):

```
VITE_AGENT_URL=https://<function-url>
```

Redeploy the frontend. The admin **Autopilot** tab now talks to the live agent.

## 7. End-to-end check

1. Log into GHAMAZON as an **admin**.
2. Admin → **Autopilot** → *Run on a manuscript* → upload a PDF/txt.
3. Watch the run advance to **Needs review**; approve the listing.
4. Confirm a new `approved` book appears in the catalog and the author gets a
   notification.

---

## Environment variables reference

| Variable | Where | Purpose |
|---|---|---|
| `DASHSCOPE_API_KEY` | function | Qwen inference |
| `DASHSCOPE_BASE_URL` | function | region endpoint |
| `OSS_ACCESS_KEY_ID` / `_SECRET` | function | OSS auth |
| `OSS_ENDPOINT` / `OSS_BUCKET` | function | OSS target (use the `-internal` endpoint from FC for lower latency/cost) |
| `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` | function | books/users/notifications + run-state |
| `RESEND_API_KEY` / `RESEND_FROM` | function | author email (optional) |
| `APP_URL` | function | links in notifications |
| `VITE_AGENT_URL` | frontend | agent API base URL |

## Troubleshooting

- **`/healthz` ok but runs hang at `intake`** — check DashScope key/region and OSS creds in the function logs (`s logs` or FC console).
- **Dashboard shows no runs** — confirm the migration ran and you're logged in as `admin` (RLS gates SELECT).
- **VL path errors on scanned PDFs** — ensure `PyMuPDF` is in the image (it's in `requirements.txt`) and the model id in `config.py` is a VL model.
- **CORS errors in the browser** — add your Pages domain to `CORS_ORIGINS`.
