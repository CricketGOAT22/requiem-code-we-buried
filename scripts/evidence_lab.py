"""Compare guarded and basic open-weight narration on freshly audited real Git history.

Run from project root; reads only a local Git checkout. The Ollama client
only calls loopback. This script never posts reports to a remote server.
"""

import argparse
import json
from pathlib import Path
import sys

from backend.audit import audit_report
from backend.benchmark import benchmark, local_model_digests, markdown_report


def main():
    p = argparse.ArgumentParser(description="REQUIEM local model evidence benchmark")
    p.add_argument("--repo", required=True, help="Local Git checkout to audit")
    p.add_argument("--report", required=True, help="Local scan_history JSON")
    p.add_argument("--models", nargs="+", default=["gemma3:4b"], help="Locally pulled Ollama models")
    p.add_argument("--max-cases", type=int, default=4)
    p.add_argument("--repetitions", type=int, default=1)
    p.add_argument("--output", default="reports/evidence-lab.json")
    p.add_argument("--check-only", action="store_true", help="Audit without any model calls")
    args = p.parse_args()

    if not 1 <= args.max_cases <= 30:
        p.error("--max-cases must be between 1 and 30")
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    audit = audit_report(args.repo, report)
    if audit["verified_cases"] != audit["selected_cases"]:
        print("STOP: Git evidence audit failed. No AI comparison performed.", file=sys.stderr)
        for case in audit["cases"]:
            if not case["verified"]:
                print(f"  {case['function']}: {case['errors']}", file=sys.stderr)
        return 1
    print(f"Independent Git audit: {audit['verified_cases']}/{audit['selected_cases']} cases verified", flush=True)
    selected = report["records"][:args.max_cases]
    print(f"Selected {len(selected)} cases from {report['repo_name']}.", flush=True)
    if args.check_only:
        print("Preflight successful: no Ollama request made.")
        return 0

    def progress(item):
        status = "VALID" if item["valid"] else "REJECTED"
        print(f"[{status}] {item['model']} | {item['method']} | "
              f"{item['subject']} | {item['metrics'].get('seconds', 0)} s | "
              f"flags: {len(item['review_flags'])}", flush=True)

    result = benchmark(selected, args.models, repetitions=args.repetitions,
                       model_digests=local_model_digests(), on_result=progress)
    result["repository"] = report["repo_name"]
    result["scan_head"] = report["scan"]["head"]
    result["git_audit"] = audit
    json_path = Path(args.output)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path = json_path.with_suffix(".md")
    md_path.write_text(markdown_report(result), encoding="utf-8")
    print(f"Saved raw results: {json_path}")
    print(f"Saved comparison table: {md_path}")
    print("WARNING: Automated review flags are NOT factuality scores. Manually inspect every explanation.")
    return 0 if all(run["valid"] for run in result["runs"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
