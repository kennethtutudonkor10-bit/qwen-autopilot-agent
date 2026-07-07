# GHAMAZON Publishing Autopilot — Devpost Submission

**Tagline:** *An autopilot agent that turns a raw manuscript into a published, purchasable book — with an AI-generated cover — on a real marketplace, keeping a human in control of the decisions that matter.*

**Track:** Autopilot Agent (Track 4)

**Links:**
- Code repository: https://github.com/kennethtutudonkor10-bit/qwen-autopilot-agent
- Video demo: _[paste your public YouTube link]_

---

## Inspiration
GHAMAZON is a real Ghanaian digital + print book marketplace. Onboarding a new book is painfully manual: a human has to read the manuscript, write the store listing, price it, screen it for quality, design a cover, and notify the author. It's slow and it doesn't scale. We wanted an agent that automates the tedious 90% while keeping a human in charge of the 10% that actually matters — what gets published, and what gets sent to the author.

## What it does
The Publishing Autopilot takes a raw manuscript (PDF, text, or scanned image) with **no metadata** and drives it end-to-end:

1. **Ingest** — reads the manuscript and extracts title, genre, themes, and tone (Qwen 3.7 Max; Qwen vision for scanned PDFs).
2. **Draft listing** — writes a complete store listing: polished title, synopsis, back-cover copy, category, keywords, and a suggested price in cedis (Qwen 3.7 Plus).
3. **Quality screen** — runs an automated quality and appropriateness check, surfacing flags.
4. **Human checkpoint #1** — the agent **pauses**. The reviewer sees the AI-drafted listing and flags, **edits any field**, and approves.
5. **Publish** — writes a real, approved book into GHAMAZON's live database, and **generates original cover art** with Qwen's image model (`wan2.6-t2i`) — the book appears on the actual marketplace, purchasable, with a unique AI cover.
6. **Human checkpoint #2** — the agent drafts an author notification email; the human **edits and approves** it.
7. **Notify** — sends the author an in-app notification (and email), and the run completes.

The result: **raw manuscript → live, purchasable book with an AI cover**, with two human-approved (and human-editable) decision points.

## How we built it
- **Qwen Cloud (Alibaba Cloud Model Studio / DashScope)** via the OpenAI-compatible endpoint. **Four Qwen capabilities:** `qwen3.7-max` (reasoning), `qwen3.7-plus` (structured listing + vision on scanned manuscripts), and `wan2.6-t2i` (text-to-image cover art).
- **FastAPI** backend running a **durable, resumable state machine** — runs persist their state and full trace, so the human-in-the-loop checkpoints survive restarts, and the pipeline executes as a background task so the UI can animate each step in real time.
- **Custom function-calling skills** (Qwen-Agent framework) as the agentic surface; a deterministic orchestrator owns sequencing for production reliability. Clean layering: pure pipeline → IO steps → orchestrator → skills.
- **Real GHAMAZON integration** — publishes into the marketplace's Supabase (Postgres) `books` table, uploads generated covers to Supabase Storage, and writes author notifications; runs are visible in an **Autopilot** tab inside the GHAMAZON admin panel.
- **Alibaba Cloud OSS** for manuscript storage (with an in-process fallback for a zero-config demo).
- A **standalone, no-login Agent Console** with an **animated pipeline timeline** that lights up each stage as the agent works.
- **Open source (MIT).**

## Challenges we ran into
- A **resumable** human-in-the-loop loop so a run can pause for approval and continue later without losing state.
- Keeping the deterministic pipeline reliable while exposing an agentic, tool-calling surface — solved by strict layering so the production path stays lightweight.
- Wiring the agent into a **real** marketplace (database + storage) so a published book, and its AI cover, actually go live.

## Accomplishments we're proud of
- It's **not a toy** — the agent publishes real books, with AI-generated covers, into a real running marketplace.
- **Genuine, editable human-in-the-loop** at both critical decisions.
- The agent's reasoning is **visualized** step-by-step in an animated console.

## What we learned
Sophisticated use of Qwen's multi-model lineup — reasoning, structured output, vision, and image generation — through a single OpenAI-compatible interface, and how to design an autopilot that's autonomous where it's safe and human-gated where it counts.

## What's next
Batch manuscript intake, an ambiguity-handling step that asks clarifying questions, and an optional fully-autonomous mode for trusted authors.
