"""Independently recheck a saved case against immutable Git objects.

No Python source from the repository is executed. This verifies Git references,
function definitions and structural match metadata, NOT semantic equivalence.
"""

import re
from pathlib import Path

from backend.afterlife import classify_match
from backend.archaeology import functions, git, source_at

_SHA = re.compile(r"[0-9a-f]{40}\Z")


def audit_report(repo, report):
    """Return a plain JSON-compatible audit summary with per-case errors."""
    root = Path(repo).expanduser().resolve()
    if report.get("kind") != "real_git_history":
        raise ValueError("Audit requires a real Git history report")
    records = report.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("Report must contain selected cases")
    output = []
    for index, record in enumerate(records):
        errors = []
        before, after = record.get("old_commit"), record.get("new_commit")
        if (not isinstance(before, str) or not _SHA.fullmatch(before)
                or not isinstance(after, str) or not _SHA.fullmatch(after)):
            errors.append("Missing or invalid full commit SHA")
        else:
            for sha in (before, after):
                try:
                    if git(root, "cat-file", "-t", sha).strip() != "commit":
                        errors.append("Git reference is not a commit")
                except RuntimeError:
                    errors.append("Referenced Git commit is unavailable")
        if not errors:
            try:
                old_defs = functions(source_at(root, before, record["path"]))
                new_defs = functions(source_at(root, after, record["path"]))
                old_found = old_defs.get(record["function"])
                if old_found is None or old_found["source"] != record.get("source"):
                    errors.append("Original function/source not present in claimed old revision")
                if record["function"] in new_defs:
                    errors.append("Function still present in claimed new revision")
                for match in record.get("possible_successors", []):
                    new_match = functions(source_at(root, after, match["path"])).get(match["function"])
                    if not new_match or new_match["source"] != match.get("source"):
                        errors.append("Successor source not present at claimed revision")
                        continue
                    expected = classify_match(record["source"], match["source"])
                    if (not expected or expected["kind"] != match.get("kind")
                            or expected["similarity"] != match.get("similarity")):
                        errors.append("Structural similarity metadata not reproducible")
            except (SyntaxError, KeyError, TypeError, ValueError) as exc:
                errors.append(f"Could not parse recorded source: {type(exc).__name__}")
        output.append({
            "case": index + 1,
            "function": f"{record.get('path', '?')}::{record.get('function', '?')}",
            "verified": not errors,
            "errors": errors,
        })
    return {
        "repo_name": report.get("repo_name"),
        "selected_cases": len(output),
        "verified_cases": sum(r["verified"] for r in output),
        "candidate_removals_scanned": report.get("scan", {}).get("candidate_removals_found"),
        "grouping": report.get("scan", {}).get("curation", {}),
        "cases": output,
        "scope": "Code presence, absence, source text and structural metadata across recorded commit pairs only",
        "limitations": "Does not prove the cause of a deletion, class rename, ancestry, or equivalent runtime behavior",
    }
