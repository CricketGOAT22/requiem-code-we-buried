"""Real local-model demo on a reproducible two-commit repository.

Run: python3 -m scripts.demo_ai --model gemma3:4b
"""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from backend.afterlife import find_afterlives
from backend.narrator import NarrationError, narrate


def git(repo, *args):
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True, capture_output=True, text=True,
    )


def demo_records(repo):
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "REQUIEM Demo")
    git(repo, "config", "user.email", "demo@example.com")
    (repo / "legacy.py").write_text(
        "def check_age(age):\n    return age >= 18\n\n"
        "def forgotten():\n    return 'goodbye'\n",
        encoding="utf-8",
    )
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "Introduce two functions")
    (repo / "legacy.py").unlink()
    (repo / "modern.py").write_text(
        "def is_adult(value):\n    return value >= 18\n",
        encoding="utf-8",
    )
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "Retire legacy and introduce modern")
    return find_afterlives(repo)


def main():
    parser = argparse.ArgumentParser(description="REQUIEM local Gemma demo")
    parser.add_argument("--model", default="gemma3:4b", help="An already pulled local Ollama model")
    parser.add_argument("--output", type=Path, help="Optional JSON report location")
    args = parser.parse_args()

    print("\nREQUIEM — LOCAL GHOST STORIES, AUDITABLE FACTS")
    print("Synthetic fixture; model runs on 127.0.0.1; no cloud inference.\n")
    reports = []
    with tempfile.TemporaryDirectory(prefix="requiem-gemma-") as directory:
        for entry in demo_records(Path(directory)):
            print(f"🪦 {entry['path']}::{entry['function']}", flush=True)
            print("  Evidence: " + entry["old_commit"][:8] + " -> " + entry["new_commit"][:8])
            print("  Structural status: " + entry["status"], flush=True)
            try:
                report = narrate(entry, model=args.model)
            except NarrationError as exc:
                print(f"\nLocal AI error: {exc}", file=sys.stderr)
                return 1
            reports.append(report)
            print("  AI epitaph: " + report["ai_interpretation"]["epitaph"])
            print("  AI interpretation: " + report["ai_interpretation"]["explanation"])
            print("  Model-used evidence IDs: " + ", ".join(report["ai_interpretation"]["evidence_ids"]))
            for obs in report["observations"]:
                print(f"    [{obs['id']}] {obs['claim']}")
            print(f"  Model: {report['model']} | inference: {report['metrics']['total_seconds']}s")
            print("  NOTE: Model statements may still need human verification.\n")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(reports, indent=2, ensure_ascii=False), encoding="utf-8")
        print("Saved local demo report to:", args.output)
    print("Done. No claim of behavioral equivalence or proven code lineage.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
