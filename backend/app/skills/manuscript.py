"""Pipeline skills, implemented as Qwen-Agent ``BaseTool`` subclasses.

Each skill is registered with the orchestrator's ``Assistant`` and invoked by the
model through function calling. Skills are thin wrappers: they do IO (OSS, the run
store) and delegate the language work to ``app.pipeline``.
"""
from __future__ import annotations

import json

from qwen_agent.tools.base import BaseTool, register_tool

from .. import pipeline, store
from ..aliyun import oss


@register_tool("ingest_manuscript")
class IngestManuscript(BaseTool):
    description = (
        "Read a manuscript file from OSS and extract raw structure: detected "
        "title, language, genre, themes, and a representative excerpt."
    )
    parameters = [
        {"name": "run_id", "type": "string", "required": True},
    ]

    def call(self, params: str, **kwargs) -> str:
        args = json.loads(params)
        run = store.get_run(args["run_id"])
        data = oss.get_bytes(run["manuscript_uri"])
        text = pipeline.extract_text(data, run["manuscript_uri"])
        extracted = pipeline.ingest(text)
        store.update_run(args["run_id"], status=store.DRAFT, step=store.DRAFT)
        store.append_trace(args["run_id"], store.INTAKE, extracted)
        return json.dumps(extracted)


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
        listing = pipeline.draft_listing(json.loads(args["extracted"]))
        store.update_run(args["run_id"], status=store.DRAFT, step=store.DRAFT,
                         draft_listing=listing)
        store.append_trace(args["run_id"], store.DRAFT, listing)
        return json.dumps(listing)


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
        run = store.get_run(args["run_id"])
        excerpt = json.loads(args["extracted"]).get("excerpt", "")
        flags = pipeline.quality_checks(run.get("draft_listing") or {}, excerpt)
        store.update_run(args["run_id"], status=store.QUALITY, step=store.QUALITY,
                         quality_flags=flags)
        store.append_trace(args["run_id"], store.QUALITY, flags)
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
        listing = json.loads(args["approved_listing"])
        # TODO(day5): insert into Supabase `books` (status='approved') + publish file.
        book_id = ""  # set from the insert
        store.update_run(args["run_id"], status=store.PUBLISH, step=store.PUBLISH,
                         book_id=book_id)
        store.append_trace(args["run_id"], store.PUBLISH, {"book_id": book_id})
        return json.dumps({"book_id": book_id, "listing": listing})
