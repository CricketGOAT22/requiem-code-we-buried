"""Group related Git removal records without claiming causal ancestry.

A class rename may make many methods appear as separate removed functions.
Preserve the original counts but select diverse investigation examples.
This grouping is strictly heuristic: a structural match is NOT a proven rename.
"""


def _class_transition(record):
    matches = record.get("possible_successors", [])
    if not matches:
        return None
    first = matches[0]
    old_name = record["function"]
    new_name = first["function"]
    if "." not in old_name or "." not in new_name:
        return None
    old_parent, old_method = old_name.rsplit(".", 1)
    new_parent, new_method = new_name.rsplit(".", 1)
    if old_parent == new_parent or old_method != new_method:
        return None
    # Only group truly corresponding method names in changed class containers.
    return (record["new_commit"], record["path"], old_parent,
            first["path"], new_parent)


def curate(records, max_cases):
    """Return (selected, statistics) with each class transition shown once.

    The report's raw removal count stays unchanged. For a bounded exhibit,
    prefer representative possible successors and include an unmatched case
    when available to illustrate the limits of search.
    """
    groups = {}
    order = []
    for index, record in enumerate(records):
        transition = _class_transition(record)
        key = ("class_transition", *transition) if transition else ("single", index)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(record)

    representative = []
    for key in order:
        members = groups[key]
        item = dict(members[0])
        if key[0] == "class_transition":
            old_class = key[3]
            new_class = key[5]
            item["case_group"] = {
                "kind": "possible_class_transition",
                "label": f"Possible class change: {old_class} → {new_class}",
                "related_removals": len(members),
                "method_names": [m["function"].rsplit(".", 1)[-1] for m in members],
                "caveat": "Grouped by matching method names and structure; not proof of a class rename.",
            }
        else:
            item["case_group"] = {
                "kind": "individual_observation",
                "label": "Individual function observation",
                "related_removals": 1,
                "method_names": [],
                "caveat": "Presence or absence is verified only in the compared revisions.",
            }
        representative.append(item)

    with_match = [item for item in representative if item["possible_successors"]]
    without_match = [item for item in representative if not item["possible_successors"]]
    if max_cases > 1 and without_match and len(with_match) >= max_cases:
        selected = with_match[:max_cases - 1] + without_match[:1]
    else:
        selected = (with_match + without_match)[:max_cases]
    stats = {
        "distinct_observation_groups": len(groups),
        "related_method_observations_grouped": len(records) - len(groups),
        "class_transition_groups": sum(key[0] == "class_transition" for key in order),
        "selected_groups": len(selected),
    }
    return selected, stats
