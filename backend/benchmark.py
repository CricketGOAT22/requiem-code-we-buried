"""Reproducible local narration evaluation for verified Git observations.

This is an exploratory comparison, NOT an automatic semantic truth grader.
The only network endpoint is the local Ollama loopback service.
"""

from collections import defaultdict
from datetime import datetime, timezone
import json
import re
from statistics import median
from urllib.error import URLError
from urllib.request import urlopen

from backend.narrator import (
    NarrationError, _call_ollama, build_prompt, evidence_bundle,
    output_schema, validate_narrative,
)


# Every treatment gets identical evidence, generation settings and JSON schema.
# The baseline is a simple evidence-supplied writing prompt; the guarded
# treatment additionally instructs the model how to handle uncertainty.
METHODS = ("baseline", "guarded")
OPTIONS = {"temperature": 0.2, "seed": 26, "num_predict": 260}


def baseline_prompt(record, evidence):
    context = {
        "deceased_function": f"{record['path']}::{record['function']}",
        "observations": evidence,
        "task": "Describe this change and write a short two-sentence epitaph.",
    }
    return (
        "You are an assistant writing a brief Git-history museum exhibit. "
        "Using the observations below, respond with ONE JSON object with "
        "three keys: epitaph, explanation, evidence_ids. "
        "The explanation should summarize the change, and evidence_ids should "
        "list the IDs you used. Do not add other fields.\n\n"
        + json.dumps(context, ensure_ascii=False, indent=2)
    )


def make_payload(record, *, model, method):
    if method not in METHODS:
        raise ValueError(f"Unknown experimental method: {method}")
    evidence = evidence_bundle(record)
    prompt = (build_prompt(record, evidence) if method == "guarded"
              else baseline_prompt(record, evidence))
    return {
        "model": model,
        "prompt": prompt,
        "format": output_schema([e["id"] for e in evidence]),
        "stream": False,
        "options": dict(OPTIONS),
    }


# Flags are triage heuristics; none are a claim of actual hallucination.
_PATTERNS = {
    "definite_lineage_language": re.compile(
        r"\b(was renamed|was moved|was replaced|is the replacement|"
        r"definitively replaced|was refactored into|became the new)\b", re.I
    ),
    "unproven_equivalence_language": re.compile(
        r"\b(behav(?:es|ed|ior) identically|equivalent behavior|"
        r"no change in logic|does not indicate a change in logic|"
        r"functionally identical|same behavior)\b", re.I
    ),
    "claimed_motive_language": re.compile(
        r"\b(was removed because|was deleted because|developers decided to|"
        r"removed to fix|removed due to)\b", re.I
    ),
}
_UNCERTAINTY = re.compile(
    r"\b(may|might|possible|possibly|potential|could|suggests?|"
    r"cannot|can't|unknown|unproven|not prove|no proof|not establish|"
    r"doesn't establish|uncertain)\b", re.I
)


def triage(prose, record):
    """Identify sentences needing human review. Not a truth classifier."""
    explanation = prose["explanation"]
    flags = []
    for label, pattern in _PATTERNS.items():
        if pattern.search(explanation):
            flags.append(label)
    if record.get("possible_successors") and not _UNCERTAINTY.search(explanation):
        flags.append("possible_successor_without_uncertainty_word")
    if record.get("context_warnings") and not re.search(
        r"\b(context|constant|literal|behavior|logic|different|change|"
        r"equivalen|threshold|limit)\w*", explanation, re.I
    ):
        flags.append("context_warning_not_discussed")
    return flags


def local_model_digests(*, opener=urlopen):
    """Record the exact local model digests when Ollama exposes them."""
    try:
        with opener("http://127.0.0.1:11434/api/tags", timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
        return {m["name"]: m["digest"] for m in data.get("models", [])
                if isinstance(m, dict) and "name" in m and "digest" in m}
    except (OSError, URLError, ValueError, TypeError, KeyError):
        return {}


def run_one(record, *, model, method, transport=None, timeout=180):
    """Perform one real or injected local-model call and retain invalid outputs."""
    payload = make_payload(record, model=model, method=method)
    evidence_ids = [x["id"] for x in evidence_bundle(record)]
    result = {
        "subject": f"{record['path']}::{record['function']}",
        "before": record["old_commit"],
        "after": record["new_commit"],
        "model": model,
        "method": method,
        "record_status": record["status"],
        "context_warning_count": len(record.get("context_warnings", [])),
        "valid": False, "interpretation": None, "review_flags": [],
        "error": None, "metrics": {},
    }
    try:
        response = (transport(payload) if transport is not None
                    else _call_ollama(payload, timeout=timeout))
        if not isinstance(response, dict):
            raise NarrationError("Ollama returned a non-object response")
        result["metrics"] = {
            "seconds": round((response.get("total_duration") or 0) / 1e9, 3),
            "prompt_tokens": response.get("prompt_eval_count"),
            "output_tokens": response.get("eval_count"),
        }
        interpretation = validate_narrative(response.get("response"), evidence_ids)
        result["interpretation"] = interpretation
        result["valid"] = True
        result["review_flags"] = triage(interpretation, record)
    except (NarrationError, ValueError, TypeError) as exc:
        result["error"] = str(exc)
    return result


def summarize(runs):
    """Report descriptive metrics, never an unsupported factuality score."""
    groups = defaultdict(list)
    for run in runs:
        groups[(run["model"], run["method"])].append(run)
    summary = []
    for (model, method), entries in sorted(groups.items()):
        valid = [e for e in entries if e["valid"]]
        speeds = [e["metrics"]["seconds"] for e in entries
                  if e["metrics"].get("seconds", 0) > 0]
        summary.append({
            "model": model, "method": method,
            "attempts": len(entries), "valid_structured_outputs": len(valid),
            "responses_flagged_for_review": sum(bool(e["review_flags"]) for e in valid),
            "median_reported_inference_seconds": (round(median(speeds), 3)
                                                  if speeds else None),
            "prompt_tokens_total": sum(e["metrics"].get("prompt_tokens") or 0
                                       for e in entries),
            "output_tokens_total": sum(e["metrics"].get("output_tokens") or 0
                                       for e in entries),
        })
    return summary


def benchmark(records, models, *, repetitions=1, transport=None,
              methods=METHODS, model_digests=None, on_result=None):
    if not records:
        raise ValueError("At least one audited case is required")
    if not 1 <= repetitions <= 5:
        raise ValueError("Repetitions must be between 1 and 5")
    if not models or any(not isinstance(m, str) or not m.strip() for m in models):
        raise ValueError("At least one local model tag is required")
    runs = []
    # Alternating treatment within each case reduces ordering bias somewhat;
    # a single machine is still not a rigorous latency benchmark.
    for record in records:
        for model in models:
            for repeat in range(repetitions):
                ordered = (methods if repeat % 2 == 0 else tuple(reversed(methods)))
                for method in ordered:
                    result = run_one(record, model=model, method=method,
                                     transport=transport)
                    result["repetition"] = repeat + 1
                    runs.append(result)
                    if on_result:
                        on_result(result)
    return {
        "protocol": "requiem-evidence-lab-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "note": "Automated checks establish structure/citation-ID validity only. "
                "Review flags are heuristics; judge model claims against Git manually.",
        "policy": "Both treatments receive identical Git evidence and JSON schema. "
                  "Only the wording of the prompt differs.",
        "models": list(models),
        "model_digests": model_digests or {},
        "repetitions": repetitions,
        "case_count": len(records),
        "runs": runs,
        "summary": summarize(runs),
    }


def markdown_report(result):
    lines = [
        "# REQUIEM — Evidence Lab (measured local run)", "",
        f"Protocol: `{result['protocol']}`. Cases: {result['case_count']}. "
        f"Repetitions: {result['repetitions']}.", "",
        "The same verified Git observations and JSON schema were given to a "
        "basic writing prompt and an evidence-cautious prompt. "
        "These are descriptive measurements, **not hallucination or accuracy rates**.", "",
        "| Model | Prompt | Attempts | Valid JSON/schema/citations | "
        "Flagged for human review | Median model time |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for entry in result["summary"]:
        seconds = entry["median_reported_inference_seconds"]
        lines.append(
            f"| `{entry['model']}` | {entry['method']} | {entry['attempts']} | "
            f"{entry['valid_structured_outputs']} | "
            f"{entry['responses_flagged_for_review']} | "
            f"{f'{seconds:.3f}s' if seconds is not None else 'n/a'} |"
        )
    lines += ["", "## Limitations", "",
              "- The validator checks citation **identifiers**, not whether the surrounding prose follows logically from them.",
              "- Review flags are regex triage signals; zero flags does **not** mean zero hallucinations.",
              "- These results concern selected cases from a bounded Git-history scan, not all changes in the repository.",
              "- Timing includes model scheduling/caching effects and is not a controlled hardware comparison.",
              "- The exact Git commits, prompts, model tags/digests, and raw outputs are retained in the JSON artifact.", ""]
    return "\n".join(lines)
