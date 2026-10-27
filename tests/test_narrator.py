"""Offline unit tests: no model download or Ollama process necessary."""

import json
import unittest

from backend.narrator import (
    NarrationError, build_prompt, evidence_bundle, narrate, output_schema,
    validate_narrative,
)


def fixture(with_successor=True):
    matches = ([{
        "path": "modern.py", "function": "is_adult", "source":
        "def is_adult(value):\n    return value >= 18\n",
        "similarity": 1.0, "kind": "exact_normalized_structure",
    }] if with_successor else [])
    return {
        "path": "legacy.py", "function": "check_age", "line": 1,
        "source": "def check_age(age):\n    return age >= 18\n",
        "old_commit": "a" * 40, "new_commit": "b" * 40,
        "status": "possible_survival" if with_successor else "no_successor_found",
        "possible_successors": matches,
    }


class NarratorTests(unittest.TestCase):
    def test_observations_are_deterministic_and_conservative(self):
        observations = evidence_bundle(fixture())
        self.assertEqual([x["id"] for x in observations], ["E1", "E2", "E3"])
        self.assertIn("not proof", observations[2]["claim"])
        self.assertIn("is no longer defined at path", observations[1]["claim"])

    def test_no_successor_yields_only_two_observations(self):
        self.assertEqual(len(evidence_bundle(fixture(False))), 2)

    def test_prompt_has_no_claim_of_definite_rename(self):
        entry = fixture()
        prompt = build_prompt(entry, evidence_bundle(entry))
        self.assertIn("never proof", prompt)
        self.assertIn("do not invent", prompt)

    def test_schema_restricts_citation_ids(self):
        schema = output_schema(["E1", "E2"])
        self.assertEqual(schema["properties"]["evidence_ids"]["items"]["enum"], ["E1", "E2"])

    def test_mocked_successful_request_parses_and_records_metrics(self):
        sent = []

        def mocked(payload):
            sent.append(payload)
            return {
                "model": "gemma3:4b", "response": json.dumps({
                    "epitaph": "Lines linger in memory. The past remains legible.",
                    "explanation": "A structurally similar new function appeared; lineage is unproven.",
                    "evidence_ids": ["E1", "E3", "E1"],
                }),
                "total_duration": 2_000_000_000, "prompt_eval_count": 100,
                "eval_count": 30,
            }
        result = narrate(fixture(), transport=mocked)
        self.assertEqual(result["ai_interpretation"]["evidence_ids"], ["E1", "E3"])
        self.assertEqual(result["metrics"]["total_seconds"], 2.0)
        self.assertEqual(sent[0]["model"], "gemma3:4b")
        self.assertFalse(sent[0]["stream"])
        self.assertIsInstance(sent[0]["format"], dict)

    def test_rejects_model_citation_to_nonexistent_commit_evidence(self):
        bad = json.dumps({
            "epitaph": "A lost line. An echo.",
            "explanation": "A replacement existed.",
            "evidence_ids": ["E999"],
        })
        with self.assertRaisesRegex(NarrationError, "unsupported evidence"):
            validate_narrative(bad, ["E1", "E2"])

    def test_rejects_invalid_json(self):
        with self.assertRaisesRegex(NarrationError, "invalid JSON"):
            validate_narrative("Here are three options!", ["E1"])

    def test_rejects_missing_fields(self):
        with self.assertRaisesRegex(NarrationError, "required three fields"):
            validate_narrative('{"epitaph":"Hello"}', ["E1"])

    def test_no_ai_request_fabricated_on_model_failure(self):
        with self.assertRaisesRegex(NarrationError, "no response"):
            narrate(fixture(), transport=lambda _: {"wrong": "payload"})


if __name__ == "__main__":
    unittest.main()
