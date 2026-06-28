"""Pipeline skills, implemented as Qwen-Agent ``BaseTool`` subclasses.

These expose the pipeline as Qwen function-calling tools for the agentic/
interactive surface (the ``Assistant`` in orchestrator-agent mode). The actual
work lives in ``app.steps`` so it never drifts from the deterministic
orchestrator.
"""
from __future__ import annotations

import json

from qwen_agent.tools.base import BaseTool, register_tool

from .. import steps


@register_tool("ingest_manuscript")
class IngestManuscript(BaseTool):
    description = (
        "Read a manuscript file from OSS and extract raw structure: detected "
        "title, language, genre, themes, and a representative excerpt."
    )
    parameters = [{"name": "run_id", "type": "string", "required": True}]

    def call(self, params: str, **kwargs) -> str:
        args = json.loads(params)
        return json.dumps(steps.do_ingest(args["run_id"]))


@register_tool("draft_listing")
class DraftListing(BaseTool):
    description = (
        "Given extracted manuscript structure, produce a complete store listing: "
        "polished title, synopsis, back-cover copy, category, language, keywords, "
        "and a suggested price in GHS."
    )
    parameters = [
        {"name": "run_id", "type": "string", "required": True},
        {"name": "extracted", "type": "string", "required": True,
         "description": "JSON from ingest_manuscript"},
    ]

    def call(self, params: str, **kwargs) -> str:
        args = json.loads(params)
        return json.dumps(steps.do_draft(args["run_id"], json.loads(args["extracted"])))


@register_tool("run_quality_checks")
class RunQualityChecks(BaseTool):
    description = (
        "Screen a draft listing + manuscript excerpt for quality and "
        "appropriateness. Returns flags the human reviewer should see before "
        "approving."
    )
    parameters = [
        {"name": "run_id", "type": "string", "required": True},
        {"name": "extracted", "type": "string", "required": True,
         "description": "JSON from ingest_manuscript (provides the excerpt)"},
    ]

    def call(self, params: str, **kwargs) -> str:
        args = json.loads(params)
        flags = steps.do_quality(args["run_id"], json.loads(args["extracted"]))
        return json.dumps({"flags": flags})


@register_tool("publish_book")
class PublishBook(BaseTool):
    description = (
        "After human approval, write the approved listing into the GHAMAZON books "
        "table and move the manuscript to the public bucket. Returns the book id."
    )
    parameters = [
        {"name": "run_id", "type": "string", "required": True},
        {"name": "approved_listing", "type": "string", "required": True,
         "description": "JSON listing as approved/edited by the admin"},
    ]

    def call(self, params: str, **kwargs) -> str:
        args = json.loads(params)
        return json.dumps(steps.do_publish(args["run_id"], json.loads(args["approved_listing"])))
