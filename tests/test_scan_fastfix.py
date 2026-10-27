"""Ensure the optimized scanner checks changed paths, including Git renames."""
import subprocess
import tempfile
from pathlib import Path
import unittest

from backend.archaeology import candidates, changed_python_paths
from backend.afterlife import find_afterlives
from backend.history import scan_history


def run_git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True,
                   capture_output=True, text=True)


class FastScanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        run_git(self.root, "init", "-q")
        run_git(self.root, "config", "user.name", "Unit Test")
        run_git(self.root, "config", "user.email", "test@example.invalid")
        # An unchanged invalid Python file must not break analysis of a changed file.
        (self.root / "broken.py").write_text("def unparseable(:", encoding="utf-8")
        (self.root / "old.py").write_text(
            "def gone(value):\n    return value + 10\n", encoding="utf-8")
        run_git(self.root, "add", "-A")
        run_git(self.root, "commit", "-qm", "first")

    def test_only_changed_file_is_inspected(self):
        (self.root / "old.py").unlink()
        (self.root / "new.py").write_text(
            "def returned(number):\n    return number + 10\n", encoding="utf-8")
        run_git(self.root, "add", "-A")
        run_git(self.root, "commit", "-qm", "second")
        self.assertEqual(changed_python_paths(self.root, "HEAD~1", "HEAD"),
                         {"old.py", "new.py"})
        records = find_afterlives(self.root)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["possible_successors"][0]["function"], "returned")
        reports = scan_history(self.root, limit=2)
        self.assertEqual(len(reports["records"]), 1)

    def test_git_rename_path_is_not_hidden(self):
        (self.root / "old.py").rename(self.root / "new.py")
        run_git(self.root, "add", "-A")
        run_git(self.root, "commit", "-qm", "rename file")
        changed = changed_python_paths(self.root, "HEAD~1", "HEAD")
        self.assertEqual(changed, {"old.py", "new.py"})
        self.assertEqual(candidates(self.root)[0]["function"], "gone")
        self.assertEqual(find_afterlives(self.root)[0]["possible_successors"][0]["function"], "gone")


if __name__ == "__main__":
    unittest.main()
