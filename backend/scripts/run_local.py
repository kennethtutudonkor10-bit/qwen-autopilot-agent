"""Local dry-run of the publishing pipeline — needs only DASHSCOPE_API_KEY.

Runs ingest -> draft_listing -> quality_checks against a local manuscript file,
with no OSS or Supabase. Verifies the Qwen integration end-to-end.

    cd backend
    export DASHSCOPE_API_KEY=sk-...        # or put it in backend/.env
    python scripts/run_local.py samples/sample_manuscript.txt
"""
from __future__ import annotations

import json
import os
import sys

# allow `python scripts/run_local.py` from the backend/ dir
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import pipeline  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python scripts/run_local.py <manuscript.txt|.pdf>")
        return 2
    path = sys.argv[1]
    with open(path, "rb") as f:
        data = f.read()

    print(f"\n=== Ingesting {path} ===")
    extracted = pipeline.ingest_auto(data, path)  # text, or Qwen-VL for scanned PDFs
    print(f"(source: {extracted.get('source')})")
    print(json.dumps(extracted, indent=2, ensure_ascii=False))

    print("\n=== Draft listing ===")
    listing = pipeline.draft_listing(extracted)
    print(json.dumps(listing, indent=2, ensure_ascii=False))

    print("\n=== Quality checks ===")
    flags = pipeline.quality_checks(listing, extracted.get("excerpt", ""))
    print(json.dumps(flags, indent=2, ensure_ascii=False))

    print(f"\nDone. {len(flags)} flag(s). "
          f"{'CLEAN — ready for human review.' if not flags else 'Review required.'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
