# REQUIEM — The Code We Buried

An evidence-first Git archaeology project for the Ghost in the Machine challenge.

## First milestone: verifiable candidate removals

The first engine finds Python functions that existed at one Git revision but are absent from the same file at another revision. These are **candidates**, not proof that functionality disappeared permanently. A later milestone will distinguish moves, renames and look-alike replacements.

Requires Python 3.10+ and Git. No package installation or external AI service is needed for this first milestone.

### Run tests

```bash
python3 -m unittest discover -s tests -v
```

### Analyze a local repository

```bash
python3 backend/archaeology.py /path/to/repo --old HEAD~1 --new HEAD
```

Output is JSON with path, function, source, line number and before/after revision labels. It processes local Git history and does not upload source code.

### Limitations (deliberately visible)

- Only Python source is analyzed in v0.1.
- Renamed or moved functions may be reported as candidate removals.
- No branch-wide or all-history scan yet; it compares two revisions.
- Historical files that cannot be parsed by the local Python interpreter are not supported yet.
- Do not expose arbitrary server-side repository paths to public users.

Next: commit-aware detection, possible survival matches, citations, Gemma-based constrained interpretations and a UI.
