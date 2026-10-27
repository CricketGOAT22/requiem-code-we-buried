"""Create a reproducible exhibit from a LOCAL Python Git checkout."""
import argparse
import json
import sys
from pathlib import Path

from backend.history import scan_history


def main():
    parser = argparse.ArgumentParser(
        description="Scan a bounded local Git history; no internet or model required"
    )
    parser.add_argument("--repo", required=True, help="Local root of a Git checkout")
    parser.add_argument("--revision", default="HEAD")
    parser.add_argument("--limit", type=int, default=120)
    parser.add_argument("--max-cases", type=int, default=8)
    parser.add_argument("--min-lines", type=int, default=2)
    parser.add_argument("--include-tests", action="store_true")
    parser.add_argument("--output", required=True, help="Path for JSON evidence report")
    args = parser.parse_args()
    def progress(index, total):
        print(f"Analyzing commit pair {index}/{total}...", file=sys.stderr, flush=True)

    report = scan_history(args.repo, revision=args.revision,
                          limit=args.limit, max_cases=args.max_cases,
                          min_lines=args.min_lines,
                          include_tests=args.include_tests, progress=progress)
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"REQUIEM REAL HISTORY — {report['repo_name']}")
    print(f"Visited {report['scan']['commits_visited']} first-parent commits")
    print(f"Observed {report['scan']['candidate_removals_found']} candidate removals")
    print(f"Selected {len(report['records'])} curated cases → {destination}")
    curation = report["scan"].get("curation", {})
    print(f"Grouped {curation.get('related_method_observations_grouped', 0)} additional method observations "
          f"across {curation.get('class_transition_groups', 0)} possible class transitions")
    for case in report["records"]:
        hits = case["possible_successors"]
        extra = (f" → POSSIBLE AFTERLIFE: {hits[0]['path']}::{hits[0]['function']}"
                 if hits else " → No matching new structure found")
        group = case.get("case_group", {})
        group_text = (f" [representing {group['related_removals']} methods]"
                      if group.get("related_removals", 1) > 1 else "")
        print(f"  {case['path']}::{case['function']} [{case['new_commit'][:8]}]{extra}{group_text}")
    if not report["records"]:
        print("No matching removals in this window. Try --limit 250 or --include-tests.")
    if report["scan"]["skipped_unparseable_pairs"]:
        print("CAUTION: Unparseable snapshots skipped; results are incomplete.")


if __name__ == "__main__":
    main()
