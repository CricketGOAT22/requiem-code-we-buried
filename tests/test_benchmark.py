"""Offline tests for the actual benchmarking protocol; no Ollama needed."""

import copy
import json
import unittest

from backend.benchmark import (
    METHODS, baseline_prompt, benchmark, make_payload, markdown_report,
    run_one, summarize, triage,
)


def record():
    return {
        "path": "legacy.py", "function": "check_age", "line": 3,
        "source": "def check_age(age):\n    return age >= MIN_AGE\n",
        "old_commit": "a" * 40, "new_commit": "b" * 40,
        "status": "possible_survival",
        "possible_successors": [{
            "path": "modern.py", "function": "is_adult", "line": 3,
            "source": "def is_adult(age):\n    return age >= MIN_AGE\n",
            "kind": "exact_normalized_structure", "similarity": 1.0,
        }],
        "context_warnings": [{"message": "MIN_AGE changed from 18 to 21."}],
    }


def response(explanation="A possible match appeared, but equivalence cannot be established.", ids=None):
    return {
        "model": "gemma3:4b",
        "response": json.dumps({
            "epitaph": "Its lines have vanished. Its story remains in Git.",
            "explanation": explanation,
            "evidence_ids": ids if ids is not None else ["E1", "E3", "E4"],
        }),
        "total_duration": 2_000_000_000,
        "prompt_eval_count": 130, "eval_count": 40,
    }


class BenchmarkTests(unittest.TestCase):
    def test_treatments_have_same_schema_evidence_and_options(self):
        a = make_payload(record(), model="gemma3:4b", method="baseline")
        b = make_payload(record(), model="gemma3:4b", method="guarded")
        self.assertEqual(a["format"], b["format"])
        self.assertEqual(a["options"], b["options"])
        self.assertNotEqual(a["prompt"], b["prompt"])
        for evidence_id in ("E1", "E2", "E3", "E4"):
            self.assertIn(evidence_id, a["prompt"])
            self.assertIn(evidence_id, b["prompt"])

    def test_valid_result_records_model_metrics_without_claiming_accuracy(self):
        result = run_one(record(), model="gemma3:4b", method="guarded",
                         transport=lambda payload: response())
        self.assertTrue(result["valid"])
        self.assertEqual(result["metrics"]["seconds"], 2.0)
        self.assertEqual(result["review_flags"], [])

    def test_rejects_fabricated_citation_id(self):
        result = run_one(record(), model="gemma3:4b", method="baseline",
                         transport=lambda payload: response(ids=["E999"]))
        self.assertFalse(result["valid"])
        self.assertIn("unsupported evidence", result["error"])

    def test_detects_definite_unsupported_equivalence_as_manual_review_flag(self):
        parsed = {"explanation": "The old function was renamed and preserves the same behavior."}
        self.assertIn("definite_lineage_language", triage(parsed, record()))
        self.assertIn("unproven_equivalence_language", triage(parsed, record()))
        self.assertIn("possible_successor_without_uncertainty_word", triage(parsed, record()))

    def test_cautious_language_is_not_flagged_as_definitive(self):
        explanation = {"explanation": "A possible structural successor was found; constant MIN_AGE changed so behavior may differ."}
        self.assertEqual(triage(explanation, record()), [])

    def test_summary_distinguishes_format_failures_from_review_flags(self):
        calls = []
        def transport(payload):
            calls.append(payload)
            if len(calls) == 1:
                return response(ids=["E999"])
            return response("It was renamed and is functionally identical.")
        results = benchmark([record()], ["gemma3:4b"], transport=transport)
        self.assertEqual(len(results["runs"]), 2)
        self.assertEqual(results["summary"][0]["valid_structured_outputs"], 0)
        self.assertEqual(results["summary"][1]["valid_structured_outputs"], 1)
        self.assertEqual(results["summary"][1]["responses_flagged_for_review"], 1)
        self.assertIn("not hallucination or accuracy rates", markdown_report(results))

    def test_repeated_treatments_reverse_order(self):
        methods_seen = []
        def transport(payload):
            methods_seen.append("guarded" if "do not invent" in payload["prompt"] else "baseline")
            return response()
        output = benchmark([record()], ["gemma3:4b"], repetitions=2, transport=transport)
        self.assertEqual(methods_seen, ["baseline", "guarded", "guarded", "baseline"])
        self.assertEqual(len(output["runs"]), 4)

    def test_unknown_treatment_rejected(self):
        with self.assertRaises(ValueError):
            make_payload(record(), model="gemma3:4b", method="cheat")


if __name__ == "__main__":
    unittest.main()
