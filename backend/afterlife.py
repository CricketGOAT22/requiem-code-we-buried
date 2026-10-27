"""Evidence-first search for possible successors to deleted Python functions.

Compares two Git revisions. We never execute code or contact a model/server.
Similar implementations are hypotheses, NOT proof of shared behavior or ancestry.
"""

import argparse
import ast
from difflib import SequenceMatcher
import json
from pathlib import Path
import textwrap

from backend.archaeology import candidates, changed_python_paths, functions, git, source_at


def shape_tokens(function_source):
    """Produce AST-based structural tokens with argument/local names normalized.

    This representation is intended for candidate discovery, not equivalence.
    Identifiers for external function calls and attribute names stay meaningful.
    """
    tree = ast.parse(textwrap.dedent(function_source))
    definition = next(
        (node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))),
        None,
    )
    if definition is None:
        return []

    arguments = definition.args
    bound = (arguments.posonlyargs + arguments.args + arguments.kwonlyargs)
    if arguments.vararg:
        bound.append(arguments.vararg)
    if arguments.kwarg:
        bound.append(arguments.kwarg)

    names = {arg.arg: f"argument_{index}" for index, arg in enumerate(bound)}
    # Normalize local variable spelling without changing the order of bindings.
    for statement in definition.body:
        for node in ast.walk(statement):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                if node.id not in names:
                    names[node.id] = f"local_{len(names)}"

    statements = definition.body
    if (statements and isinstance(statements[0], ast.Expr)
            and isinstance(statements[0].value, ast.Constant)
            and isinstance(statements[0].value.value, str)):
        statements = statements[1:]  # Ignore optional docstring in comparisons.

    tokens = []
    for statement in statements:
        for node in ast.walk(statement):
            if isinstance(node, (ast.Load, ast.Store, ast.Del)):
                continue
            if isinstance(node, ast.Name):
                tokens.append(f"Name:{names.get(node.id, node.id)}")
            elif isinstance(node, ast.Constant):
                tokens.append(f"Constant:{node.value!r}")
            elif isinstance(node, ast.Attribute):
                tokens.append(f"Attribute:{node.attr}")
            elif isinstance(node, ast.keyword):
                tokens.append(f"Keyword:{node.arg}")
            else:
                tokens.append(type(node).__name__)
    return tokens


def classify_match(old, new):
    """Return evidence score and level, or None if not a defensible match.

    Exact structure is always eligible (even for small functions). Near matches
    require >=25 AST tokens to avoid false positives on one-line functions.
    """
    before = shape_tokens(old)
    after = shape_tokens(new)
    if not before or not after:
        return None
    if before == after:
        return {"kind": "exact_normalized_structure", "similarity": 1.0}
    if min(len(before), len(after)) < 25:
        return None
    similarity = SequenceMatcher(None, before, after, autojunk=False).ratio()
    if similarity >= 0.93:
        return {"kind": "high_structural_similarity", "similarity": round(similarity, 3)}
    return None


def find_afterlives(repo, older="HEAD~1", newer="HEAD"):
    """Return evidence-backed removal records with possible successors.

    Restrict successor search to newly appearing qualified (path, function)
    definitions. This avoids treating long-existing duplicate code as evidence
    of a new move or rename during the selected revision interval.
    """
    repo = Path(repo).resolve()
    # A function cannot appear in an unchanged source file. Scanning the diff
    # reduces the work from O(all Python files x commit pairs) to O(changed files).
    # Renamed files appear as old-path deletion plus new-path introduction.
    changed_paths = sorted(changed_python_paths(repo, older, newer))
    arrivals = []
    for path in changed_paths:
        old_definitions = functions(source_at(repo, older, path))
        new_definitions = functions(source_at(repo, newer, path))
        for name, info in new_definitions.items():
            if name not in old_definitions:
                arrivals.append({
                    "path": path, "function": name,
                    "line": info["line"], "source": info["source"],
                })

    older_sha = git(repo, "rev-parse", older).strip()
    newer_sha = git(repo, "rev-parse", newer).strip()
    report = []
    for removed in candidates(repo, older, newer):
        matches = []
        for arrival in arrivals:
            evidence = classify_match(removed["source"], arrival["source"])
            if evidence is None:
                continue
            if removed["path"] == arrival["path"]:
                relationship = "possible_rename_or_replacement"
            elif removed["function"] == arrival["function"]:
                relationship = "possible_move"
            else:
                relationship = "possible_move_and_rename"
            matches.append({
                **arrival, **evidence, "relationship": relationship,
                "caveat": "Code similarity does not establish equal behavior or historical lineage.",
            })
        matches.sort(key=lambda item: (-item["similarity"], item["path"], item["function"]))
        report.append({
            **removed,
            "old_commit": older_sha, "new_commit": newer_sha,
            "status": "possible_survival" if matches else "no_successor_found",
            "possible_successors": matches[:5],
            "interpretation": (
                "Structural matches found; inspect linked source and Git diffs to verify."
                if matches else
                "No structural match found among newly appearing functions; this does not prove permanent deletion."
            ),
        })
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search for possible afterlives of removed Python functions")
    parser.add_argument("repo", help="Path to a local Git repository")
    parser.add_argument("--old", default="HEAD~1", help="Old Git revision")
    parser.add_argument("--new", default="HEAD", help="New Git revision")
    args = parser.parse_args()
    print(json.dumps(find_afterlives(args.repo, args.old, args.new), indent=2))
