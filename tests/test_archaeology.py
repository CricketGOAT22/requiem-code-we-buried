import subprocess
import tempfile
import unittest
from pathlib import Path
from backend.archaeology import candidates


def command(path, *args):
    subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True)


class ArchaeologyTests(unittest.TestCase):
    def test_removed_function_has_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            command(repo, "init", "-q")
            command(repo, "config", "user.name", "Test")
            command(repo, "config", "user.email", "test@example.com")
            path = repo / "legacy.py"
            path.write_text("def forgotten():\n    return 42\n\ndef survivor():\n    return 7\n")
            command(repo, "add", ".")
            command(repo, "commit", "-qm", "Add functions")
            path.write_text("def survivor():\n    return 7\n")
            command(repo, "add", ".")
            command(repo, "commit", "-qm", "Remove forgotten")
            result = candidates(repo)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["function"], "forgotten")
            self.assertIn("return 42", result[0]["source"])


    def test_edit_without_removal_has_no_candidates(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            command(repo, "init", "-q")
            command(repo, "config", "user.name", "Test")
            command(repo, "config", "user.email", "test@example.com")
            path = repo / "main.py"
            path.write_text("def alive():\n    return 1\n")
            command(repo, "add", ".")
            command(repo, "commit", "-qm", "Start")
            path.write_text("def alive():\n    return 2\n")
            command(repo, "add", ".")
            command(repo, "commit", "-qm", "Edit")
            self.assertEqual(candidates(repo), [])

    def test_deleted_file_is_candidate(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            command(repo, "init", "-q")
            command(repo, "config", "user.name", "Test")
            command(repo, "config", "user.email", "test@example.com")
            path = repo / "obsolete.py"
            path.write_text("def relic():\n    return 'here'\n")
            command(repo, "add", ".")
            command(repo, "commit", "-qm", "Start")
            path.unlink()
            command(repo, "add", "-A")
            command(repo, "commit", "-qm", "Delete file")
            result = candidates(repo)
            self.assertEqual([item["function"] for item in result], ["relic"])

if __name__ == "__main__":
    unittest.main()
