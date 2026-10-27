"""Identify candidate function removals between Git revisions."""
import argparse
import ast
import json
import subprocess
from pathlib import Path


def git(repo, *args):
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Git command failed")
    return result.stdout


def python_files(repo, revision):
    return {
        path for path in git(repo, "ls-tree", "-r", "--name-only", revision).splitlines()
        if path.endswith(".py")
    }


def source_at(repo, revision, path):
    result = subprocess.run(
        ["git", "-C", str(repo), "show", f"{revision}:{path}"],
        capture_output=True, text=True, check=False,
    )
    return result.stdout if result.returncode == 0 else ""


def functions(source):
    """Return qualified function names mapped to source and line numbers."""
    tree = ast.parse(source)
    found = {}

    def visit(nodes, scope=""):
        for node in nodes:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                name = f"{scope}.{node.name}" if scope else node.name
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    found[name] = {
                        "line": node.lineno,
                        "source": ast.get_source_segment(source, node) or "",
                    }
                visit(node.body, name)
            elif isinstance(node, (ast.If, ast.Try, ast.With)):
                # Module-level conditional definitions are uncommon, but matter.
                visit(node.body, scope)
                visit(getattr(node, "orelse", []), scope)
                visit(getattr(node, "finalbody", []), scope)
    visit(tree.body)
    return found


def changed_python_paths(repo, older, newer):
    """List paths with changed Python content (including deleted and renamed files).

    We deliberately disable rename detection so both the source and destination
    of a file rename are scanned. Git's pathspec limits work to Python files.
    """
    paths = git(repo, "diff", "--no-renames", "--name-only", older, newer,
                "--", "*.py").splitlines()
    return set(paths)


def candidates(repo, older="HEAD~1", newer="HEAD"):
    """Read ONLY changed Python files instead of each file in both Git trees."""
    repo = Path(repo).resolve()
    removed = []
    for path in sorted(changed_python_paths(repo, older, newer)):
        before = functions(source_at(repo, older, path))
        after = functions(source_at(repo, newer, path))
        for name, info in before.items():
            if name not in after:
                removed.append({
                    "path": path, "function": name, "line": info["line"],
                    "source": info["source"], "last_seen": older,
                    "first_missing": newer, "status": "candidate_removal",
                })
    return removed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find functions missing between two Git revisions")
    parser.add_argument("repo", help="Local Git repository path")
    parser.add_argument("--old", default="HEAD~1")
    parser.add_argument("--new", default="HEAD")
    args = parser.parse_args()
    print(json.dumps(candidates(args.repo, args.old, args.new), indent=2))
