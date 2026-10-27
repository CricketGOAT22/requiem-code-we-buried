"""Real Git commit-window tests; only repositories created by this test run."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from backend.history import github_origin, scan_history
from backend.exhibit import public_exhibit


def git(path, *args):
    result = subprocess.run(["git", "-C", str(path), *args],
                            capture_output=True, text=True, check=True)
    return result.stdout.strip()


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.repo = Path(self.folder.name)
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.name", "History Test")
        git(self.repo, "config", "user.email", "fixture@example.invalid")
        git(self.repo, "remote", "add", "origin", "https://github.com/pallets/click.git")
        (self.repo / "sample.py").write_text(
            "def original(value):\n    return value * 2\n\n"
            "def truly_gone(value):\n    return value + 5\n", encoding="utf-8"
        )
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "create historical functions")
        self.first = git(self.repo, "rev-parse", "HEAD")
        (self.repo / "sample.py").write_text("# Gone from original module\n", encoding="utf-8")
        (self.repo / "new.py").write_text(
            "def reincarnated(number):\n    return number * 2\n", encoding="utf-8"
        )
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "replace an implementation")
        self.second = git(self.repo, "rev-parse", "HEAD")
        (self.repo / "README.md").write_text("Documentation only\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "document")

    def tearDown(self):
        self.folder.cleanup()

    def test_real_scanner_finds_original_git_evidence(self):
        result = scan_history(self.repo, limit=3)
        self.assertEqual(result["kind"], "real_git_history")
        self.assertEqual(result["scan"]["commits_visited"], 3)
        self.assertEqual(result["scan"]["candidate_removals_found"], 2)
        cases = {item["function"]: item for item in result["records"]}
        self.assertEqual(cases["original"]["new_commit"], self.second)
        self.assertEqual(cases["original"]["old_commit"], self.first)
        self.assertEqual(cases["original"]["possible_successors"][0]["function"], "reincarnated")
        self.assertEqual(cases["truly_gone"]["possible_successors"], [])
        self.assertEqual(cases["original"]["observations"][0]["id"], "E1")

    def test_public_exhibit_preserves_commit_urls(self):
        result = public_exhibit(scan_history(self.repo, limit=3))
        self.assertEqual(result["repoName"], "pallets/click")
        self.assertEqual(result["summary"]["removed"], 2)
        self.assertEqual(result["summary"]["possibleSurvivors"], 1)
        example = result["stones"][0]
        self.assertEqual(example["newCommitUrl"], f"https://github.com/pallets/click/commit/{self.second}")
        self.assertIn("Real local Git history", result["disclaimer"])

    def test_origin_rejects_credentials(self):
        git(self.repo, "remote", "set-url", "origin", "https://secret@github.com/pallets/click.git")
        self.assertIsNone(github_origin(self.repo))

    def test_origin_accepts_ssh(self):
        git(self.repo, "remote", "set-url", "origin", "git@github.com:pallets/click.git")
        self.assertEqual(github_origin(self.repo), "https://github.com/pallets/click")

    def test_limit_validation(self):
        with self.assertRaises(ValueError):
            scan_history(self.repo, limit=501)
        with self.assertRaises(ValueError):
            scan_history(self.repo, limit=1)


if __name__ == "__main__":
    unittest.main()
