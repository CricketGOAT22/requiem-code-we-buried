"""Prepare, annotate and summarize a human-reviewed Gemma benchmark offline.

Examples:
  python3 -m scripts.review_lab prepare --lab reports/gemma3-lab.json \\
      --repo external/click --report reports/click-history.json --review reports/gemma3-review.json
  python3 -m scripts.review_lab annotate --review reports/gemma3-review.json
  python3 -m scripts.review_lab summary --review reports/gemma3-review.json
"""

import argparse
import json
import os
from pathlib import Path
import tempfile

from backend.review import (prepare_review, render_review_markdown,
                            set_review, summarize_review)
from backend.audit import audit_report


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _save(path, data):
    """Write a durable review checkpoint without clobbering on interruption."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                         prefix=f".{path.name}.", suffix=".tmp",
                                         delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _display(item, *, show_source=False):
    print("\n" + "=" * 78)
    print(f"REVIEW {item['id']}  •  {item['subject']}")
    print(f"BEFORE {item['before'][:12]}  ->  AFTER {item['after'][:12]}")
    print("-" * 78)
    print("INDEPENDENT GIT OBSERVATIONS:")
    for evidence in item["evidence"]:
        print(f"  [{evidence['id']}] {evidence['claim']}")
        if show_source and evidence.get("source_excerpt"):
            print("    Code (UNTRUSTED DATA):")
            for line in evidence["source_excerpt"].splitlines()[:18]:
                print("      " + line[:120])
    prose = item["interpretation"]
    print("\nMODEL EXPLANATION (GRADE FACTUAL SUPPORT):")
    print("  " + prose["explanation"])
    print("\nCREATIVE EPITAPH (NOT SCORED FOR POETIC QUALITY):")
    print("  " + prose["epitaph"])
    print("\nCited evidence IDs: " + ", ".join(prose["evidence_ids"]))
    print("Model identity, prompt condition, and machine review flags are hidden here.")


def main():
    parser = argparse.ArgumentParser(description="Human review of real Git-history AI narration")
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare", help="Create a shuffled reviewer workbook")
    prepare.add_argument("--lab", required=True)
    prepare.add_argument("--repo", required=True, help="Real local Git checkout to verify again")
    prepare.add_argument("--report", required=True)
    prepare.add_argument("--review", required=True)
    prepare.add_argument("--seed", type=int, default=2026)
    annotate = sub.add_parser("annotate", help="Grade model prose interactively; autosaves")
    annotate.add_argument("--review", required=True)
    annotate.add_argument("--id", help="Revisit one reviewer item, e.g. R002")
    annotate.add_argument("--show-source", action="store_true")
    summary = sub.add_parser("summary", help="Export descriptive human-reviewed comparison")
    summary.add_argument("--review", required=True)
    args = parser.parse_args()

    try:
        if args.command == "prepare":
            if Path(args.review).exists():
                parser.error("Review file already exists; refusing to overwrite human labels")
            report = _read(args.report)
            audit = audit_report(args.repo, report)
            if audit["verified_cases"] != audit["selected_cases"]:
                parser.error("Live Git audit failed; cannot prepare reviewer workbook")
            print(f"Fresh Git audit passed: {audit['verified_cases']}/{audit['selected_cases']}")
            book = prepare_review(_read(args.lab), report, seed=args.seed)
            _save(args.review, book)
            print(f"Created {args.review}: {len(book['entries'])} valid responses to review")
            print(f"Invalid model outputs excluded: {book['invalid_model_responses_excluded']}")
            print(f"Next: python3 -m scripts.review_lab annotate --review {args.review}")
        elif args.command == "annotate":
            book = _read(args.review)
            entries = [e for e in book["entries"] if
                       (args.id == e["id"] if args.id else e["human_review"]["verdict"] is None)]
            if args.id and not entries:
                parser.error("No review item with that ID")
            if not entries:
                print("All available outputs have a human annotation. Run summary.")
                return 0
            print("Review claims against OBSERVATIONS (not just whether a citation ID exists).")
            print("  s = supported; u = unsupported; ? = unclear; k = skip; q = quit")
            print("  Explain any unsupported or unclear judgment. Your work autosaves.")
            for entry in entries:
                _display(entry, show_source=args.show_source)
                while True:
                    raw = input("Verdict [s/u/?/k/q]: ").strip().lower()
                    if raw in ("q", "quit"):
                        print("Stopped; completed reviews remain saved.")
                        return 0
                    if raw in ("k", "skip"):
                        break
                    verdict = {"s": "supported", "u": "unsupported", "?": "unclear"}.get(raw)
                    if not verdict:
                        print("Use s, u, ?, k or q.")
                        continue
                    reason = input("Why? (mandatory for u/?; optional for s): ").strip()
                    try:
                        set_review(book, entry["id"], verdict, reason)
                    except ValueError as exc:
                        print(exc)
                        continue
                    _save(args.review, book)
                    print(f"Saved {entry['id']} as {verdict}.")
                    break
            totals = summarize_review(book)
            print(f"Completed {totals['completed']}/{totals['total_valid_outputs']} reviews.")
        else:
            book = _read(args.review)
            result = summarize_review(book)
            out_path = Path(args.review).with_suffix(".md")
            out_path.write_text(render_review_markdown(book), encoding="utf-8")
            print(f"Human review: {result['completed']}/{result['total_valid_outputs']} completed; "
                  f"{result['pending']} pending; {result['invalid_outputs_excluded']} invalid model outputs excluded")
            for row in result["groups"]:
                print(f"{row['model']} {row['method']}: {row['supported']} supported, "
                      f"{row['unsupported']} unsupported, {row['unclear']} unclear "
                      f"({row['reviewed']} reviewed)")
            print(f"Paired descriptive outcomes: {result['paired_outcomes']}")
            print(f"Saved report: {out_path}")
            if not result["reportable_as_complete"]:
                print("INCOMPLETE: Do not publish proportions until all outputs have been reviewed.")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    except (EOFError, KeyboardInterrupt):
        print("\nInterrupted: previously entered reviews remain saved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
