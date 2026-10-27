"""Create a temporary repository demonstrating a rename and genuine removal."""
from pathlib import Path
import subprocess
import tempfile

from backend.afterlife import find_afterlives


def run(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def main():
    with tempfile.TemporaryDirectory(prefix="requiem-evidence-") as directory:
        repo = Path(directory)
        run(repo, "init", "-q")
        run(repo, "config", "user.name", "REQUIEM Demo")
        run(repo, "config", "user.email", "demo@example.com")
        (repo / "old.py").write_text(
            "def check_age(age):\n    return age >= 18\n\n"
            "def forgotten():\n    return 'goodbye'\n", encoding="utf-8")
        run(repo, "add", "-A")
        run(repo, "commit", "-qm", "Introduce two historical functions")
        (repo / "old.py").unlink()
        (repo / "new.py").write_text(
            "def is_adult(value):\n    return value >= 18\n", encoding="utf-8")
        run(repo, "add", "-A")
        run(repo, "commit", "-qm", "Move and rename age check; retire forgotten")

        print("\nREQUIEM — THE AFTERLIFE DETECTOR")
        print("Reproducible fixture: two commits, no internet, no AI guessing.\n")
        results = find_afterlives(repo)
        for entry in results:
            print(f"  🪦  {entry['path']} :: {entry['function']}")
            print(f"      Removal evidence: {entry['old_commit'][:8]} → {entry['new_commit'][:8]}")
            if entry["possible_successors"]:
                match = entry["possible_successors"][0]
                print(f"      ✨ POSSIBLE AFTERLIFE: {match['path']} :: {match['function']}")
                print(f"      Evidence: {match['kind']} ({match['similarity']:.2f} structural similarity)")
            else:
                print("      🌑 No new structural successor found in this revision")
            print()
        print("Important: similarity is a lead for investigation, not proof of equivalent behavior.")


if __name__ == "__main__":
    main()
