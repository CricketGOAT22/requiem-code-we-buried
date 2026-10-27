"""Verify each saved real-history case against local Git objects."""

import argparse
import json
from pathlib import Path

from backend.audit import audit_report


def main():
    parser = argparse.ArgumentParser(description="Audit REQUIEM evidence against Git objects")
    parser.add_argument("--repo", required=True, help="Original local Git checkout")
    parser.add_argument("--report", required=True, help="Saved JSON report from scan_history")
    parser.add_argument("--output", help="Optional output JSON audit path")
    args = parser.parse_args()
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    audit = audit_report(args.repo, report)
    print("REQUIEM — INDEPENDENT EVIDENCE AUDIT")
    print(f"Repository: {audit['repo_name']}")
    print(f"Verified selected cases: {audit['verified_cases']}/{audit['selected_cases']}")
    print(f"Observed candidate removals in window: {audit['candidate_removals_scanned']}")
    for case in audit["cases"]:
        symbol = "PASS" if case["verified"] else "FAIL"
        print(f"  [{symbol}] {case['function']}")
        for error in case["errors"]:
            print(f"      {error}")
    print(f"Scope: {audit['scope']}")
    print(f"Limit: {audit['limitations']}")
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
        print(f"Saved audit: {path}")
    if audit["verified_cases"] != audit["selected_cases"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
