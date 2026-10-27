"""Step 8: duplicate suppression and tamper-detecting Git audits."""

import subprocess
import tempfile
import unittest
from pathlib import Path

from backend.audit import audit_report
from backend.curation import curate
from backend.history import scan_history


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True, check=True).stdout.strip()


class CurationAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.name", "Audit Fixture")
        git(self.repo, "config", "user.email", "fixture@example.invalid")
        (self.repo / "before.py").write_text(
            "class Old:\n"
            "    def a(self, x):\n        return x + 10\n"
            "    def b(self, x):\n        return x * 13\n"
            "    def c(self, x):\n        return x / 17\n"
            "def dead(x):\n    return x ** 3\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "add old class and standalone function")
        (self.repo / "before.py").unlink()
        (self.repo / "after.py").write_text(
            "class New:\n"
            "    def a(self, x):\n        return x + 10\n"
            "    def b(self, x):\n        return x * 13\n"
            "    def c(self, x):\n        return x / 17\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "rename class and delete one function")

    def test_groups_methods_but_preserves_original_removal_count(self):
        report = scan_history(self.repo, limit=2, max_cases=8)
        self.assertEqual(report["scan"]["candidate_removals_found"], 4)
        self.assertEqual(len(report["records"]), 2)
        self.assertEqual(report["scan"]["curation"]["related_method_observations_grouped"], 2)
        class_group = next(r for r in report["records"] if r["possible_successors"])
        self.assertEqual(class_group["case_group"]["related_removals"], 3)
        self.assertEqual(class_group["case_group"]["kind"], "possible_class_transition")
        self.assertEqual(set(class_group["case_group"]["method_names"]), {"a", "b", "c"})

    def test_audit_confirms_actual_sources_and_commits(self):
        report = scan_history(self.repo, limit=2)
        audit = audit_report(self.repo, report)
        self.assertEqual(audit["verified_cases"], 2)
        self.assertTrue(all(c["verified"] for c in audit["cases"]))

    def test_audit_fails_if_source_is_modified(self):
        report = scan_history(self.repo, limit=2)
        report["records"][0]["source"] = "def fake():\n    return 999"
        audit = audit_report(self.repo, report)
        self.assertLess(audit["verified_cases"], audit["selected_cases"])

    def test_does_not_merge_unrelated_rename_events(self):
        examples = [{
            "function": "A.f", "path": "file.py", "new_commit": "a" * 40,
            "possible_successors": [{"function": "B.f", "path": "file.py"}],
        }, {
            "function": "X.g", "path": "file.py", "new_commit": "a" * 40,
            "possible_successors": [{"function": "Y.g", "path": "file.py"}],
        }]
        chosen, stats = curate(examples, 8)
        self.assertEqual(len(chosen), 2)
        self.assertEqual(stats["related_method_observations_grouped"], 0)


if __name__ == "__main__":
    unittest.main()
