"""Deterministic, fully synthetic Git exhibition for the REQUIEM local website.

No history is represented as a real-world repository. Every item comes from
actual Git commits made inside a disposable local demo repository.
"""

from pathlib import Path
import subprocess

from backend.afterlife import find_afterlives
from backend.narrator import evidence_bundle
from backend.context import changed_literal_context


def _git(path, *args):
    result = subprocess.run(
        ["git", "-C", str(path), *args], capture_output=True,
        text=True, check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "demo Git command failed")
    return result.stdout.strip()


def make_exhibit(directory):
    """Populate directory with two commits and return their verified removal records."""
    repo = Path(directory)
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "REQUIEM Fixture")
    _git(repo, "config", "user.email", "fixture@example.invalid")
    (repo / "legacy.py").write_text(
        "MIN_AGE = 18\n\n"
        "def can_enter(age):\n"
        "    return age >= MIN_AGE\n\n"
        "def check_age(age):\n"
        "    return age >= 18\n\n"
        "def forgotten():\n"
        "    return 'goodbye'\n\n"
        "def summon(name):\n"
        "    return f'Hello, {name}'\n",
        encoding="utf-8",
    )
    (repo / "archives").mkdir()
    (repo / "archives" / "ledgers.py").write_text(
        "def count_echoes(values):\n"
        "    total = 0\n"
        "    for value in values:\n"
        "        if value > 0:\n"
        "            total += value\n"
        "    return total\n",
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "Introduce forgotten functions")
    older = _git(repo, "rev-parse", "HEAD")

    (repo / "legacy.py").unlink()
    (repo / "archives" / "ledgers.py").unlink()
    (repo / "modern.py").write_text(
        "MIN_AGE = 21\n\n"
        "def can_enter_v2(age):\n"
        "    return age >= MIN_AGE\n\n"
        "def is_adult(value):\n"
        "    return value >= 18\n\n"
        "def greet(name):\n"
        "    return f'Hello, {name}'\n",
        encoding="utf-8",
    )
    (repo / "archives" / "restored.py").write_text(
        "def count_echoes(values):\n"
        "    total = 0\n"
        "    for value in values:\n"
        "        if value > 0:\n"
        "            total += value\n"
        "    return total\n",
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "Move and rename useful implementations")
    newer = _git(repo, "rev-parse", "HEAD")

    records = find_afterlives(repo, older, newer)
    for record in records:
        record["context_warnings"] = (
            changed_literal_context(repo, record, record["possible_successors"][0])
            if record["possible_successors"] else []
        )
        record["observations"] = evidence_bundle(record)
    records.sort(key=lambda r: (r["status"] != "possible_survival", r["path"], r["function"]))
    return {"older": older, "newer": newer, "records": records}


def public_exhibit(exhibit):
    """Transform deterministic data into a client-facing, auditable exhibit."""
    stones = []
    for index, record in enumerate(exhibit["records"]):
        stones.append({
            "id": index,
            "name": record["function"],
            "path": record["path"],
            "line": record["line"],
            "source": record["source"],
            "status": record["status"],
            "oldCommit": record["old_commit"],
            "newCommit": record["new_commit"],
            "possibleSuccessors": [{
                "name": match["function"],
                "path": match["path"],
                "line": match["line"],
                "source": match["source"],
                "similarity": match["similarity"],
                "kind": match["kind"],
                "relationship": match["relationship"],
                "caveat": match["caveat"],
            } for match in record["possible_successors"]],
            "interpretation": record["interpretation"],
            "contextWarnings": record.get("context_warnings", []),
            "observations": record["observations"],
            "caseGroup": record.get("case_group"),
            "oldCommitUrl": (
                f"{exhibit['repo_url']}/commit/{record['old_commit']}"
                if exhibit.get("repo_url") else None
            ),
            "newCommitUrl": (
                f"{exhibit['repo_url']}/commit/{record['new_commit']}"
                if exhibit.get("repo_url") else None
            ),
        })
    return {
        "kind": exhibit.get("kind", "synthetic_git_fixture"),
        "repoName": exhibit.get("repo_name", "REQUIEM FIXTURE"),
        "repoUrl": exhibit.get("repo_url"),
        "scan": exhibit.get("scan"),
        "disclaimer": exhibit.get(
            "disclaimer",
            "Synthetic, reproducible Git history. All commit evidence is real within the fixture; none of these are claims about a public repository.",
        ),
        "older": exhibit["older"],
        "newer": exhibit["newer"],
        "stones": stones,
        "summary": {
            "removed": len(stones),
            "possibleSurvivors": sum(bool(s["possibleSuccessors"]) for s in stones),
            "unmatched": sum(not s["possibleSuccessors"] for s in stones),
        },
    }
