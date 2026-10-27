"""Pure offline checks of human adjudication: labels are never inferred by an LLM."""
import copy
import unittest

from backend.benchmark import benchmark
from backend.review import (prepare_review, render_review_markdown,
                            set_review, summarize_review)
from tests.test_benchmark import record, response


def fixture():
    old = record()
    report = {
        "kind": "real_git_history", "repo_name": "sample/example",
        "scan": {"head": "b" * 40}, "records": [old],
    }
    lab = benchmark([old], ["gemma3:4b"],
                    transport=lambda payload: response())
    lab.update(repository="sample/example", scan_head="b" * 40,
               git_audit={"verified_cases": 1, "selected_cases": 1})
    return lab, report


class ReviewTests(unittest.TestCase):
    def test_creates_exactly_two_reviewer_items_from_paired_run(self):
        lab, report = fixture()
        book = prepare_review(lab, report)
        self.assertEqual(len(book["entries"]), 2)
        self.assertEqual({e["method"] for e in book["entries"]}, {"baseline", "guarded"})
        self.assertEqual({e["id"] for e in book["entries"]}, {"R001", "R002"})
        self.assertIsNone(book["entries"][0]["human_review"]["verdict"])

    def test_order_is_stable_for_given_seed(self):
        lab, report = fixture()
        a = prepare_review(lab, report, seed=14)
        b = prepare_review(lab, report, seed=14)
        self.assertEqual(a, b)
        self.assertEqual(len(a["input_sha256"]), 64)
        self.assertEqual(len(a["scan_sha256"]), 64)

    def test_rejects_repository_mismatch(self):
        lab, report = fixture()
        report["repo_name"] = "another/repository"
        with self.assertRaisesRegex(ValueError, "repositories differ"):
            prepare_review(lab, report)

    def test_refuses_unverified_git_history(self):
        lab, report = fixture()
        lab["git_audit"]["verified_cases"] = 0
        with self.assertRaisesRegex(ValueError, "complete Git audit"):
            prepare_review(lab, report)

    def test_rejects_unknown_subject_in_model_run(self):
        lab, report = fixture()
        lab["runs"][0]["subject"] = "fake.py::deleted"
        with self.assertRaisesRegex(ValueError, "unknown case"):
            prepare_review(lab, report)

    def test_invalid_structured_output_is_excluded_not_misgraded(self):
        lab, report = fixture()
        lab["runs"][0].update(valid=False, interpretation=None, error="invalid")
        book = prepare_review(lab, report)
        self.assertEqual(len(book["entries"]), 1)
        self.assertEqual(book["invalid_model_responses_excluded"], 1)

    def test_reason_required_for_unsupported_or_unclear(self):
        lab, report = fixture()
        book = prepare_review(lab, report)
        with self.assertRaisesRegex(ValueError, "explain"):
            set_review(book, "R001", "unsupported", "")
        with self.assertRaisesRegex(ValueError, "explain"):
            set_review(book, "R001", "unclear", "")
        with self.assertRaisesRegex(ValueError, "Unknown"):
            set_review(book, "R999", "supported", "")

    def test_pair_summary_distinguishes_human_evidence_labels(self):
        lab, report = fixture()
        book = prepare_review(lab, report)
        for entry in book["entries"]:
            if entry["method"] == "baseline":
                set_review(book, entry["id"], "unsupported", "False lineage claim")
            else:
                set_review(book, entry["id"], "supported", "Explanation appropriately cautious")
        summary = summarize_review(book)
        self.assertTrue(summary["reportable_as_complete"])
        self.assertEqual(summary["paired_outcomes"]["guarded_supported_baseline_unsupported"], 1)
        self.assertIn("False lineage claim", render_review_markdown(book))

    def test_pending_reviews_are_not_reportable_as_complete(self):
        lab, report = fixture()
        book = prepare_review(lab, report)
        set_review(book, "R001", "supported", "")
        summary = summarize_review(book)
        self.assertFalse(summary["reportable_as_complete"])
        self.assertEqual(summary["pending"], 1)
        self.assertIn("INCOMPLETE", render_review_markdown(book))

    def test_no_pretend_verdict_from_regex_review_flags(self):
        lab, report = fixture()
        lab["runs"][0]["review_flags"] = ["definite_lineage_language"]
        book = prepare_review(lab, report)
        flagged = next(e for e in book["entries"] if e["machine_flags"])
        self.assertIsNone(flagged["human_review"]["verdict"])

    def test_duplicate_model_method_repetition_rejected(self):
        lab, report = fixture()
        lab["runs"].append(copy.deepcopy(lab["runs"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate model runs"):
            prepare_review(lab, report)

    def test_does_not_count_unclear_pair_as_supported(self):
        lab, report = fixture()
        book = prepare_review(lab, report)
        for entry in book["entries"]:
            set_review(book, entry["id"],
                       "unclear" if entry["method"] == "baseline" else "supported",
                       "Need more evidence" if entry["method"] == "baseline" else "")
        self.assertEqual(summarize_review(book)["paired_outcomes"]["at_least_one_unclear"], 1)


if __name__ == "__main__":
    unittest.main()
