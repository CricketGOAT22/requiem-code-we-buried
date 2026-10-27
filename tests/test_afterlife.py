"""Reproducible Git-history fixtures for possible successor detection."""
import subprocess
import tempfile
import unittest
from pathlib import Path

from backend.afterlife import classify_match, find_afterlives


def git(folder, *args):
    subprocess.run(["git", "-C", str(folder), *args], check=True, capture_output=True)


class AfterlifeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.name", "Test")
        git(self.repo, "config", "user.email", "test@example.com")

    def write(self, filename, content):
        path = self.repo / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def commit(self, message):
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", message)

    def test_rename_and_argument_change_detected(self):
        self.write("age.py", "def check_age(age):\n    return age >= 18\n")
        self.commit("Add check")
        self.write("age.py", "def is_adult(value):\n    return value >= 18\n")
        self.commit("Rename check")
        record = find_afterlives(self.repo)[0]
        self.assertEqual(record["status"], "possible_survival")
        self.assertEqual(record["possible_successors"][0]["function"], "is_adult")
        self.assertEqual(record["possible_successors"][0]["kind"], "exact_normalized_structure")
        self.assertEqual(len(record["new_commit"]), 40)

    def test_function_moved_to_another_file(self):
        self.write("legacy.py", "def calculate(x):\n    return x * 12\n")
        self.commit("Add")
        (self.repo / "legacy.py").unlink()
        self.write("new/home.py", "def calculate(value):\n    return value * 12\n")
        self.commit("Move")
        record = find_afterlives(self.repo)[0]
        self.assertEqual(record["possible_successors"][0]["relationship"], "possible_move")

    def test_true_removal_is_unmatched(self):
        self.write("old.py", "def farewell():\n    return 'nothing remains'\n")
        self.commit("Add")
        (self.repo / "old.py").unlink()
        self.commit("Delete")
        self.assertEqual(find_afterlives(self.repo)[0]["status"], "no_successor_found")

    def test_changed_comparison_is_not_exact_match(self):
        self.assertIsNone(classify_match(
            "def old(x):\n    return x >= 18\n",
            "def new(y):\n    return y < 18\n",
        ))

    def test_unmodified_existing_duplicate_is_not_new_successor(self):
        self.write("old.py", "def vanished(x):\n    return x * 2\n")
        self.write("other.py", "def existing(x):\n    return x * 2\n")
        self.commit("Add duplicate")
        (self.repo / "old.py").unlink()
        self.commit("Remove only one")
        self.assertEqual(find_afterlives(self.repo)[0]["status"], "no_successor_found")

    def test_no_removed_functions_returns_empty_list(self):
        self.write("main.py", "def alive():\n    return 1\n")
        self.commit("Add")
        self.write("main.py", "def alive():\n    return 2\n")
        self.commit("Edit")
        self.assertEqual(find_afterlives(self.repo), [])


if __name__ == "__main__":
    unittest.main()
