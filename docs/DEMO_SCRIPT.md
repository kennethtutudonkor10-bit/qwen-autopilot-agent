# Demo Video Script (≤ 3:00)

Target: the hackathon's required ≤3-min public demo. Goal — show a real,
end-to-end **autopilot** with human-in-the-loop, not a chatbot. Lead with the
workflow and the checkpoints; keep the marketplace as the backdrop.

Record at 1440×900, admin already logged in, one sample manuscript ready.

---

### 0:00–0:20 — Hook + problem
> "This is GHAMAZON, a Ghanaian book marketplace. Every new book means an author
> uploads a manuscript and a human has to read it, write the listing, price it,
> and check it's appropriate — slow, and it doesn't scale."

**Screen:** GHAMAZON homepage, then Admin → Autopilot tab.

### 0:20–0:40 — What the agent is
> "We built an autopilot agent on Qwen Cloud that does the whole intake-to-publish
> workflow, and stops for a human at the decisions that matter."

**Screen:** the Autopilot dashboard (empty inbox + the architecture diagram as an overlay for 3–4s).

### 0:40–1:15 — Kick off a run (ambiguous input + tool use)
> "I upload a raw manuscript — no metadata. The agent reads it with Qwen, drafts
> a complete listing, and screens it for quality. For scanned PDFs it switches to
> Qwen-VL automatically."

**Screen:** click *Run on a manuscript* → upload → watch status badges advance
Ingesting → Drafting → Quality. Expand the **agent trace** to show the steps.

### 1:15–2:00 — Human checkpoint #1 (the core of Track 4)
> "Now the autopilot pauses. Here's the AI-drafted title, synopsis, category and
> price, plus its quality flags. I can edit anything — say, bump the price — then
> approve."

**Screen:** the *Review listing* checkpoint card. Edit the price field. Click
**Approve & publish**. Cut to the catalog showing the new book live.

### 2:00–2:30 — Human checkpoint #2 + completion
> "It publishes the book, then pauses again with a drafted author email. I approve,
> and the author is notified by email and in-app. Run complete."

**Screen:** the *Approve notification* card → **Send & finish** → run shows
**Published**; show the author's notification bell / email.

### 2:30–2:55 — Production-readiness + tech
> "The whole thing runs on Alibaba Cloud Function Compute, uses Qwen-plus,
> qwen3-coder and Qwen-VL via Model Studio, custom Qwen-Agent skills and MCP, with
> durable resumable runs so checkpoints survive restarts. It's open source."

**Screen:** architecture diagram; quick flash of the repo + the live `/healthz`.

### 2:55–3:00 — Close
> "An autopilot that handles ambiguous work, calls real tools, and keeps a human
> in control. Thanks for watching."

---

## Shot checklist
- [ ] Homepage + Autopilot tab
- [ ] Upload → live status + trace
- [ ] Checkpoint #1: edit + approve
- [ ] New book live in catalog
- [ ] Checkpoint #2: approve email
- [ ] Run = Published, author notified
- [ ] Architecture diagram + `/healthz`
- [ ] Repo URL on screen

## Recording tips
- Pre-seed 1–2 completed runs so the inbox isn't empty.
- If a Qwen call is slow on camera, cut between upload and the checkpoint.
- Upload the final cut to YouTube/Vimeo as **public** and put the link in the Devpost submission + README.
