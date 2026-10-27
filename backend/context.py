"""Detect a narrow but important source of structural false positives.

An exact function AST can mask changed module constants. This uses literal
module-level bindings only, never executing untrusted repository content.
"""

import ast

from backend.archaeology import source_at


def literal_bindings(module_source):
    try:
        tree = ast.parse(module_source)
    except SyntaxError:
        return {}
    output = {}
    for statement in tree.body:
        if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name):
            node = statement.targets[0]
            if isinstance(statement.value, ast.Constant) and type(statement.value.value) in (str, int, float, bool):
                output[node.id] = statement.value.value
        elif isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name) and isinstance(statement.value, ast.Constant):
            if type(statement.value.value) in (str, int, float, bool):
                output[statement.target.id] = statement.value.value
    return output


def referenced_names(function_source):
    try:
        tree = ast.parse(function_source)
    except SyntaxError:
        return set()
    return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)}


def changed_literal_context(repo, record, match):
    old_source = source_at(repo, record["old_commit"], record["path"])
    new_source = source_at(repo, record["new_commit"], match["path"])
    old_bindings = literal_bindings(old_source)
    new_bindings = literal_bindings(new_source)
    referenced = referenced_names(record["source"]) & referenced_names(match["source"])
    warnings = []
    for name in sorted(referenced & old_bindings.keys() & new_bindings.keys()):
        if old_bindings[name] != new_bindings[name]:
            warnings.append({
                "variable": name,
                "before": old_bindings[name],
                "after": new_bindings[name],
                "kind": "changed_module_level_literal",
                "message": (
                    f"Module-level literal {name} changed from {old_bindings[name]!r} "
                    f"to {new_bindings[name]!r}. Identical function structure can "
                    "still depend on different context; behavior was not proven equivalent."
                ),
            })
    return warnings
