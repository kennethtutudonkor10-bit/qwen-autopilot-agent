"""Orchestrator: a Qwen-Agent Assistant driving the publishing pipeline.

The Assistant runs a ReAct loop over the registered skills using a Qwen model on
DashScope. The pipeline is a state machine (see docs/architecture.md): the agent
advances INTAKE -> DRAFT -> QUALITY, then hands off to a human checkpoint. On
resume it continues PUBLISH -> (human) -> NOTIFY -> DONE.
"""
from __future__ import annotations

from qwen_agent.agents import Assistant

from . import store
from .config import get_settings
from .skills import ALL_SKILLS  # noqa: F401 — importing registers the tools

SYSTEM = (
    "You are the GHAMAZON Publishing Autopilot. Given a manuscript run, ingest the "
    "file, draft a complete store listing, and run quality checks. Be precise and "
    "never fabricate book content. When the pipeline reaches a human checkpoint, "
    "stop and summarize what the human must approve. Resume only with approved data."
)


def _llm_cfg() -> dict:
    s = get_settings()
    return {
        "model": s.model_reason,
        "model_server": s.dashscope_base_url,
        "api_key": s.dashscope_api_key,
        "generate_cfg": {"temperature": 0.3},
    }


def build_agent() -> Assistant:
    function_list = [t.name for t in ALL_SKILLS]
    return Assistant(llm=_llm_cfg(), system_message=SYSTEM, function_list=function_list)


def run_until_checkpoint(run_id: str) -> dict:
    """Advance a run from its current step until it needs human approval or finishes.

    Returns the run row. When ``status == awaiting_approval`` the caller surfaces
    ``pending_action`` to the admin dashboard.
    """
    agent = build_agent()
    run = store.get_run(run_id)
    messages = [{
        "role": "user",
        "content": f"Process manuscript run {run_id} from step '{run['step']}'.",
    }]

    # qwen-agent streams responses; we take the final state.
    for _ in agent.run(messages=messages):
        pass

    # Skills update the run as they execute. After INTAKE->DRAFT->QUALITY the
    # pipeline pauses for review of the draft listing.
    run = store.get_run(run_id)
    if run["status"] == store.QUALITY:
        store.update_run(
            run_id,
            status=store.AWAITING_APPROVAL,
            pending_action={
                "checkpoint": "review_listing",
                "listing": run.get("draft_listing"),
                "flags": run.get("quality_flags"),
            },
        )
    return store.get_run(run_id)


def resume(run_id: str, approved_listing: dict | None, decision: str) -> dict:
    """Resume a run after a human checkpoint.

    decision: 'approve' | 'reject'. On approve we continue the pipeline; the
    second checkpoint (notify author) is handled the same way by the caller.
    """
    if decision == "reject":
        return store.update_run(run_id, status=store.REJECTED, pending_action=None)

    # TODO(day4-5): invoke publish_book with approved_listing, then pause again for
    # the author-notification checkpoint, then send email/notification on approve.
    store.update_run(run_id, pending_action=None)
    return run_until_checkpoint(run_id)
