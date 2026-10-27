"""Human adjudication of REQUIEM narration against independently audited Git evidence.

Human labels are deliberately distinct from regular-expression review flags.
Nothing here asks an LLM to score another LLM. No network calls are made.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
import random

from backend.narrator import evidence_bundle

PROTOCOL = "requiem-human-adjudication-v1"
VERDICTS = ("supported", "unsupported", "unclear")


def _hash_json(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":")).encode("utf-8")).hexdigest()


def _key_from_record(record):
    return (f"{record['path']}::{record['function']}",
            record["old_commit"], record["new_commit"])


def _key_from_run(run):
    return (run["subject"], run["before"], run["after"])


def prepare_review(lab, report, *, seed=2026):
    """Build a reproducibly shuffled, reviewer-readable annotation workbook.

    Labels are hidden in the *CLI review screen*, not cryptographically blinded:
    this JSON workbook retains conditions for subsequent paired analysis.
    """
    if lab.get("protocol") != "requiem-evidence-lab-v1":
        raise ValueError("Expected a REQUIEM Evidence Lab v1 report")
    if report.get("kind") != "real_git_history":
        raise ValueError("Expected an authentic Git-history scan report")
    if lab.get("repository") != report.get("repo_name"):
        raise ValueError("Lab and Git report repositories differ")
    if lab.get("scan_head") != report.get("scan", {}).get("head"):
        raise ValueError("Lab and Git report scan heads differ")
    audit = lab.get("git_audit") or {}
    if (audit.get("verified_cases") != audit.get("selected_cases")
            or audit.get("verified_cases") != len(report.get("records", []))):
        raise ValueError("The Evidence Lab report does not show a complete Git audit")
    if not isinstance(seed, int):
        raise ValueError("Seed must be an integer")
    lookup = {_key_from_record(record): record for record in report["records"]}
    if len(lookup) != len(report["records"]):
        raise ValueError("Duplicate cases found in the Git report")
    entries = []
    invalid_count = 0
    for run in lab.get("runs", []):
        key = _key_from_run(run)
        if key not in lookup:
            raise ValueError(f"A model run references an unknown case: {key[0]}")
        if run.get("method") not in ("baseline", "guarded"):
            raise ValueError("Unrecognized prompt condition")
        if not isinstance(run.get("repetition"), int):
            raise ValueError("Missing repetition number")
        if not isinstance(run.get("model"), str) or not run["model"].strip():
            raise ValueError("Missing model name")
        if not run.get("valid"):
            invalid_count += 1
            continue  # Already counted separately as an invalid output.
        interpretation = run.get("interpretation")
        if not isinstance(interpretation, dict) or not all(
            isinstance(interpretation.get(field), str)
            for field in ("explanation", "epitaph")
        ):
            raise ValueError("Valid run is missing human-reviewable prose")
        record = lookup[key]
        allowed = {e["id"] for e in evidence_bundle(record)}
        cited = interpretation.get("evidence_ids")
        if not isinstance(cited, list) or not cited or any(
            not isinstance(i, str) or i not in allowed for i in cited
        ):
            raise ValueError("Run has nonexistent evidence identifiers")
        entries.append({
            "subject": run["subject"],
            "before": run["before"],
            "after": run["after"],
            "model": run["model"],
            "method": run["method"],
            "repetition": run["repetition"],
            "interpretation": interpretation,
            "evidence": evidence_bundle(record),
            "machine_flags": list(run.get("review_flags", [])),
            "human_review": {"verdict": None, "reason": ""},
        })
    if not entries:
        raise ValueError("No valid outputs to review")
    # Make duplicates impossible in the paired-comparison grouping.
    identifiers = [(e["subject"], e["before"], e["after"], e["model"],
                    e["method"], e["repetition"]) for e in entries]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Duplicate model runs in evidence-lab results")
    random.Random(seed).shuffle(entries)
    for i, entry in enumerate(entries, 1):
        entry["id"] = f"R{i:03d}"
    return {
        "protocol": PROTOCOL,
        "input_sha256": _hash_json(lab),
        "scan_sha256": _hash_json(report),
        "repository": lab["repository"],
        "review_policy": (
            "Assess the factual claims in EXPLANATION, not poetic merit. "
            "SUPPORTED: each factual assertion is directly evidenced, or uncertainty "
            "is clearly expressed. UNSUPPORTED: one or more categorical factual "
            "claims exceeds the cited Git evidence. UNCLEAR: cannot decide from "
            "the available excerpts; inspect commits and explain uncertainty. "
            "Evidence IDs alone do not prove a claim."
        ),
        "design_limitations": (
            "Conditions are masked in the terminal annotation view only, "
            "not cryptographically blinded; reviewer can recognize prompt style. "
            "Single-rater descriptive study, no validated factuality metric."
        ),
        "invalid_model_responses_excluded": invalid_count,
        "entries": entries,
    }


def set_review(book, entry_id, verdict, reason=""):
    if verdict not in VERDICTS:
        raise ValueError("Verdict must be supported, unsupported, or unclear")
    if not isinstance(reason, str):
        raise ValueError("Reason must be text")
    if verdict in ("unsupported", "unclear") and not reason.strip():
        raise ValueError("Please explain unsupported or unclear judgments")
    matches = [entry for entry in book["entries"] if entry["id"] == entry_id]
    if len(matches) != 1:
        raise ValueError("Unknown or duplicate review ID")
    matches[0]["human_review"] = {"verdict": verdict, "reason": reason.strip()}


def summarize_review(book):
    if book.get("protocol") != PROTOCOL:
        raise ValueError("Unknown review protocol")
    outcomes = defaultdict(lambda: {"reviewed": 0, "supported": 0,
                                     "unsupported": 0, "unclear": 0})
    by_pair = defaultdict(dict)
    pending = 0
    for entry in book["entries"]:
        verdict = entry["human_review"].get("verdict")
        if verdict is None:
            pending += 1
            continue
        if verdict not in VERDICTS:
            raise ValueError("Invalid recorded human verdict")
        totals = outcomes[(entry["model"], entry["method"])]
        totals["reviewed"] += 1
        totals[verdict] += 1
        key = (entry["subject"], entry["before"], entry["after"],
               entry["model"], entry["repetition"])
        if entry["method"] in by_pair[key]:
            raise ValueError("Duplicate review in a paired comparison")
        by_pair[key][entry["method"]] = verdict
    pairs = {"both_supported": 0, "both_unsupported": 0,
             "guarded_supported_baseline_unsupported": 0,
             "baseline_supported_guarded_unsupported": 0,
             "at_least_one_unclear": 0, "incomplete_pair": 0}
    for pair in by_pair.values():
        if not all(method in pair for method in ("baseline", "guarded")):
            pairs["incomplete_pair"] += 1
        elif "unclear" in pair.values():
            pairs["at_least_one_unclear"] += 1
        elif pair["baseline"] == pair["guarded"]:
            pairs["both_" + pair["baseline"]] += 1
        else:
            pairs[f"{ 'guarded' if pair['guarded'] == 'supported' else 'baseline'}_supported_"
                  f"{ 'baseline' if pair['baseline'] == 'unsupported' else 'guarded'}_unsupported"] += 1
    return {
        "protocol": PROTOCOL,
        "total_valid_outputs": len(book["entries"]),
        "invalid_outputs_excluded": book["invalid_model_responses_excluded"],
        "completed": len(book["entries"]) - pending,
        "pending": pending,
        "groups": [{"model": model, "method": method, **values}
                   for (model, method), values in sorted(outcomes.items())],
        "paired_outcomes": pairs,
        "reportable_as_complete": pending == 0,
    }


def render_review_markdown(book):
    result = summarize_review(book)
    lines = ["# REQUIEM — Human evidence adjudication", "",
             f"Repository: `{book['repository']}`", "",
             f"Completed reviews: **{result['completed']}/{result['total_valid_outputs']}**", "",
             "This is human annotation of model explanations against Git evidence, "
             "not an automated hallucination score.", "",
             "| Model | Condition | Reviewed | Supported | Unsupported | Unclear |",
             "|---|---|---:|---:|---:|---:|",]
    for group in result["groups"]:
        lines.append(f"| `{group['model']}` | {group['method']} | {group['reviewed']} | "
                     f"{group['supported']} | {group['unsupported']} | {group['unclear']} |")
    lines += ["", "## Paired outcomes", ""]
    for key, count in result["paired_outcomes"].items():
        lines.append(f"- {key.replace('_', ' ')}: **{count}**")
    lines += ["", "## Boundaries", "",
              "- `SUPPORTED` means an individual reviewer found no unsupported **explanatory** claim in the displayed Git observations; it is not a proof of correctness.",
              "- Samples were deliberately curated and the sample size may be small; do not generalize these results to all Git repositories.",
              "- Review interface masks model and condition labels but is not fully blind.",
              "- Any incomplete or unclear judgments remain visible instead of counting as model failures or successes.",
              "- Inference timing and automatic triage flags are distinct from these human judgments.", ""]
    if result["pending"]:
        lines.insert(5, "**INCOMPLETE — do not publish group proportions from this workbook.**")
    lines += ["## Human notes", ""]
    for item in book["entries"]:
        review = item["human_review"]
        if review["verdict"] is not None:
            lines += [f"- `{item['id']}` `{item['subject']}` "
                      f"[{item['model']}, {item['method']}]: "
                      f"**{review['verdict']}** — {review['reason'] or '(none)'}"]
    lines.append("")
    return "\n".join(lines)
