"""The public site cannot ship unaudited case data or falsely claim live AI."""

from pathlib import Path
import hashlib
import json
import subprocess
import tempfile
import unittest

from backend.exhibit import make_exhibit
from backend.public_export import ExportError, make_public_snapshot
from backend.narrator import evidence_bundle
from backend.claim_gate import verified_view


class PublicExportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.report = make_exhibit(self.root)
        self.report.update({
            "kind": "real_git_history", "repo_name": "example/fixture",
            "repo_url": "https://github.com/example/fixture",
        })
        subprocess.run(["git", "-C", str(self.root), "remote", "add", "origin",
                        "https://github.com/example/fixture.git"], check=True)

    def tearDown(self):
        self.temporary.cleanup()

    def mock_narrator(self, record, **kwargs):
        facts = evidence_bundle(record)
        return {
            "subject": f"{record['path']}::{record['function']}",
            "factual_view": verified_view(facts),
            "ai_interpretation": {
                "epitaph": "A former shape. A surviving echo.",
                "explanation": "They were identical at runtime due to a security fix.",
                "evidence_ids": ["E1", "E2"],
            },
            "model": kwargs.get("model"), "metrics": {"total_seconds": 0},
        }

    def test_explicit_authorization_required(self):
        with self.assertRaisesRegex(ExportError, "authorization"):
            make_public_snapshot(self.root, self.report, with_ai=False)

    def test_origin_must_match(self):
        self.report["repo_url"] = "https://github.com/someone/private-repo"
        with self.assertRaisesRegex(ExportError, "match"):
            make_public_snapshot(self.root, self.report, with_ai=False, authorized=True)

    def test_tampering_fails_closed(self):
        self.report["records"][0]["source"] = "def fake():\n    return 1"
        with self.assertRaisesRegex(ExportError, "audit"):
            make_public_snapshot(self.root, self.report, with_ai=False, authorized=True)

    def test_precomputed_ai_is_never_a_factual_claim(self):
        output = make_public_snapshot(self.root, self.report, narrator=self.mock_narrator, authorized=True)
        self.assertTrue(output["publicMode"])
        self.assertEqual(output["audit"]["verified_cases"], 5)
        self.assertEqual(len(output["precomputedNarrations"]), 5)
        self.assertEqual(output["repoUrl"], "https://github.com/example/fixture")
        ai = output["precomputedNarrations"]["0"]
        self.assertIn("security fix", ai["ai_interpretation"]["explanation"])
        self.assertNotIn("security fix", str(ai["factual_view"]))
        self.assertNotIn("security fix", str(output["stones"]))

    def test_completed_human_review_can_be_published_but_not_rewritten(self):
        digest = hashlib.sha256(json.dumps(self.report, sort_keys=True,
            separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        record = self.report["records"][0]
        review_book = {
            "protocol": "requiem-human-adjudication-v1",
            "repository": "example/fixture", "scan_sha256": digest,
            "invalid_model_responses_excluded": 0,
            "entries": [{"id": "R001", "subject": record["function"],
                "before": record["old_commit"], "after": record["new_commit"],
                "model": "gemma3:4b", "method": "baseline", "repetition": 1,
                "human_review": {"verdict": "unsupported", "reason": "Claimed replacement."}}],
        }
        output = make_public_snapshot(self.root, self.report, authorized=True,
            with_ai=False, review_book=review_book)
        self.assertEqual(output["evaluation"]["completed"], 1)
        self.assertEqual(output["evaluation"]["groups"][0]["unsupported"], 1)
        review_book["scan_sha256"] = "00" * 32
        with self.assertRaisesRegex(ExportError, "exact Git report"):
            make_public_snapshot(self.root, self.report, authorized=True,
                with_ai=False, review_book=review_book)

    def test_preview_without_ai_is_marked_as_empty(self):
        output = make_public_snapshot(self.root, self.report, authorized=True, with_ai=False)
        self.assertEqual(output["precomputedNarrations"], {})
        self.assertEqual(output["audit"]["selected_cases"], 5)


if __name__ == "__main__":
    unittest.main()
