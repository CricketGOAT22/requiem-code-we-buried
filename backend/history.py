"""Scan a bounded window of a local Git repository for real function removals.

No repository code is executed. No cloning or network access occurs in this
module. All conclusions concern pairs of observed revisions, not provenance or
runtime equivalence across the full lifetime of a repository.
"""

from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit

from backend.afterlife import find_afterlives
from backend.curation import curate
from backend.archaeology import git
from backend.context import changed_literal_context
from backend.narrator import evidence_bundle


_GITHUB_PATH = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def github_origin(repo):
    """Give an audited https://github.com/owner/project URL, never credentials."""
    result = subprocess.run(
        ["git", "-C", str(repo), "config", "--get", "remote.origin.url"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode:
        return None
    raw = result.stdout.strip()
    if raw.startswith("git@github.com:"):
        project = raw[len("git@github.com:"):]
    else:
        parts = urlsplit(raw)
        if parts.scheme != "https" or parts.hostname != "github.com":
            return None
        # Reject remote credentials, ports, and ambiguous URL structure.
        if parts.username or parts.password or parts.port or parts.query or parts.fragment:
            return None
        project = parts.path.lstrip("/")
    project = project.removesuffix(".git").strip("/")
    if not _GITHUB_PATH.fullmatch(project):
        return None
    return "https://github.com/" + project


def _is_test_path(path):
    segments = path.split("/")
    return ("tests" in segments or "test" in segments
            or path.rsplit("/", 1)[-1].startswith("test_")
            or path.rsplit("/", 1)[-1] == "conftest.py")


def scan_history(repo, *, revision="HEAD", limit=120, max_cases=8,
                 min_lines=2, include_tests=False, progress=None):
    """Return a JSON-safe exhibit from nearby first-parent Git commit pairs.

    Stops at a fixed number of commits to prevent accidental full-history scans.
    Records are explicitly a selection, never all removals in the repository.
    """
    if not 2 <= limit <= 500:
        raise ValueError("limit must be between 2 and 500 commits")
    if not 1 <= max_cases <= 30:
        raise ValueError("max_cases must be between 1 and 30")
    if not 1 <= min_lines <= 50:
        raise ValueError("min_lines must be between 1 and 50")
    root = Path(repo).expanduser().resolve()
    if not (root / ".git").exists():
        raise ValueError("Select the root of a local Git checkout (with a .git directory)")

    shas = git(root, "rev-list", "--first-parent", f"--max-count={limit}", revision).splitlines()
    if len(shas) < 2:
        raise ValueError("At least two commits are required")

    assessed = []
    pairs_with_py_changes = 0
    invalid_pairs = []
    for index, (newer, older) in enumerate(zip(shas[:-1], shas[1:]), 1):
        if progress and (index == 1 or index % 10 == 0 or index == len(shas) - 1):
            progress(index, len(shas) - 1)
        changes = git(root, "diff", "--name-only", older, newer, "--", "*.py").splitlines()
        if not changes or (not include_tests and all(_is_test_path(p) for p in changes)):
            continue
        pairs_with_py_changes += 1
        try:
            found = find_afterlives(root, older, newer)
        except (SyntaxError, UnicodeError) as exc:
            # A Python source snapshot could not be parsed. Never label it
            # a removal based on missing/invalid AST data.
            invalid_pairs.append({"commit": newer, "reason": type(exc).__name__})
            continue
        for record in found:
            if not include_tests and _is_test_path(record["path"]):
                continue
            if len(record["source"].strip().splitlines()) < min_lines:
                continue
            record["context_warnings"] = (
                changed_literal_context(root, record, record["possible_successors"][0])
                if record["possible_successors"] else []
            )
            record["observations"] = evidence_bundle(record)
            assessed.append(record)

    # Prefer examples showing a plausible successor; retain unmatched cases.
    # Stable within each group: first-parent order, newest commit first.
    assessed.sort(key=lambda r: 0 if r["possible_successors"] else 1)
    selected, curation_stats = curate(assessed, max_cases)
    web_url = github_origin(root)
    return {
        "kind": "real_git_history",
        "repo_name": web_url.split("github.com/", 1)[-1] if web_url else root.name,
        "repo_url": web_url,
        "older": selected[0]["old_commit"] if selected else shas[-1],
        "newer": selected[0]["new_commit"] if selected else shas[0],
        "records": selected,
        "scan": {
            "head": shas[0], "commits_visited": len(shas),
            "pairs_examined": len(shas) - 1,
            "pairs_with_python_changes": pairs_with_py_changes,
            "candidate_removals_found": len(assessed),
            "displayed_cases": len(selected),
            "curation": curation_stats,
            "skipped_unparseable_pairs": invalid_pairs,
            "first_parent_only": True,
            "include_tests": include_tests,
        },
        "disclaimer": (
            "Real local Git history. Each case compares a pair of first-parent "
            "revisions. These selected cases are not a complete history. "
            "Related method removals from possible class transitions are grouped "
            "to avoid repeating one change as many stories. Structural similarity "
            "never proves code ancestry or equivalent behavior. Repository code was not executed."
        ),
    }
