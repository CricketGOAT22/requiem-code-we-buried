"""Export an audited Click repo for the read-only public REQUIEM exhibition."""

import argparse
import json
from pathlib import Path

from backend.public_export import ExportError, make_public_snapshot
from backend.narrator import NarrationError


def main():
    parser = argparse.ArgumentParser(description="Export a public, independently audited REQUIEM exhibit")
    parser.add_argument("--repo", required=True, help="Local checkout of the public GitHub project")
    parser.add_argument("--report", required=True, help="Git scan JSON to audit again")
    parser.add_argument("--output", default="frontend/public/exhibit.json")
    parser.add_argument("--model", default="gemma3:4b")
    parser.add_argument("--review", default="reports/gemma3-review.json", help="Completed human evidence-review workbook")
    parser.add_argument("--skip-ai", action="store_true", help="For local smoke tests only; public submissions should include generated epitaphs")
    parser.add_argument("--confirm-public-source", action="store_true", help="I confirm the source and source excerpts are appropriate to publish")
    args = parser.parse_args()
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    review = json.loads(Path(args.review).read_text(encoding="utf-8"))
    try:
        snapshot = make_public_snapshot(args.repo, report, model=args.model,
               with_ai=not args.skip_ai, authorized=args.confirm_public_source,
               review_book=review)
    except (ExportError, NarrationError) as exc:
        parser.error(str(exc))
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n"
    # On errors we never write a partial file, avoiding misleading data online.
    temp = destination.with_suffix(destination.suffix + ".tmp")
    temp.write_text(payload, encoding="utf-8")
    temp.replace(destination)
    print("REQUIEM PUBLIC EXPORT — AUDITED SNAPSHOT")
    print(f"Repository: {snapshot['repoName']}")
    print(f"Audited: {snapshot['audit']['verified_cases']}/{snapshot['audit']['selected_cases']}")
    print(f"Precomputed Gemma narrations: {len(snapshot['precomputedNarrations'])}")
    print(f"Human-reviewed explanations: {snapshot['evaluation']['completed']}")
    print(f"Source report SHA-256: {snapshot['reportDigest']}")
    print(f"Saved: {destination} ({len(payload.encode('utf-8'))} bytes)")
    if args.skip_ai:
        print("WARNING: This export contains no Gemma epitaphs; not the intended final public demo.")


if __name__ == "__main__":
    main()
