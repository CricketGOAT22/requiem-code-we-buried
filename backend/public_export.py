"""Export an independently audited real-Git exhibit as a public static snapshot.

Only Git observations determine the factual view. Gemma is run locally at export
and saved as precomputed literary output. Static websites never call Ollama.
"""

import hashlib
import json
from pathlib import Path

from backend.audit import audit_report
from backend.exhibit import public_exhibit
from backend.history import github_origin
from backend.narrator import narrate
from backend.review import summarize_review


class ExportError(ValueError):
    pass


def make_public_snapshot(repo, report, *, model="gemma3:4b", with_ai=True,
                         narrator=narrate, authorized=False, review_book=None):
    """Produce a static exhibit only from explicitly approved public Git code."""
    if not authorized:
        raise ExportError("Explicit --confirm-public-source authorization is required")
    root = Path(repo).expanduser().resolve()
    origin = github_origin(root)
    if not origin or report.get("repo_url") != origin:
        raise ExportError("The report must match a recognized public GitHub origin")
    if report.get("kind") != "real_git_history":
        raise ExportError("Only real Git-history reports can be publicly exported")
    audit = audit_report(root, report)
    if audit["selected_cases"] < 1 or audit["verified_cases"] != audit["selected_cases"]:
        raise ExportError("Every selected case must pass a fresh Git-object audit")
    # The report is locally generated from the Git tree. This digest is an
    # integrity fingerprint of the export input, not a cryptographic signature.
    digest = hashlib.sha256(json.dumps(report, sort_keys=True,
                    separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    exhibit = public_exhibit(report)
    exhibit["publicMode"] = True
    exhibit["reportDigest"] = digest
    exhibit["audit"] = {
        "selected_cases": audit["selected_cases"],
        "verified_cases": audit["verified_cases"],
        "scope": audit["scope"],
        "limitations": audit["limitations"],
    }
    exhibit["precomputedNarrations"] = {}
    if review_book is not None:
        if (review_book.get("repository") != report.get("repo_name")
                or review_book.get("scan_sha256") != digest):
            raise ExportError("Human review does not match this exact Git report")
        summary = summarize_review(review_book)
        if not summary["reportable_as_complete"]:
            raise ExportError("Human-review workbook must be complete")
        exhibit["evaluation"] = summary
    if with_ai:
        if not model or not isinstance(model, str):
            raise ExportError("A local Ollama model must be provided")
        for item in exhibit["stones"]:
            record = report["records"][item["id"]]
            result = narrator(record, model=model)
            if (result.get("subject") != f"{record['path']}::{record['function']}"
                    or not isinstance(result.get("factual_view"), dict)
                    or not isinstance(result.get("ai_interpretation"), dict)):
                raise ExportError(f"Invalid model export for case {item['id']}")
            exhibit["precomputedNarrations"][str(item["id"])] = result
    return exhibit
