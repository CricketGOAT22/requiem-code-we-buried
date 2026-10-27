"""Evidence/AI trust boundary for the REQUIEM exhibition.

This does NOT automatically fact-check a natural-language model response.
Instead, only deterministic Git observations may appear in the FACTUAL view.
The model's prose remains separately labeled UNVERIFIED creative content.
A digest detects changed report bytes, not whether the report matches Git.
"""

from hashlib import sha256
import json


def verified_view(observations):
    """Build factual-display content without consulting an AI response.

    Call only with observations built by the deterministic Git scanner.
    To make a strong authenticity claim, audit the saved scan against its
    Git objects with `scripts.audit_history` first.
    """
    if not isinstance(observations, list) or len(observations) < 2:
        raise ValueError("Expected at least the presence and absence observations")
    expected = [f"E{i}" for i in range(1, len(observations) + 1)]
    if [o.get("id") for o in observations if isinstance(o, dict)] != expected:
        raise ValueError("Evidence IDs must be ordered and consecutive")
    if not all(isinstance(o.get("claim"), str) and o["claim"].strip()
               for o in observations):
        raise ValueError("Empty or invalid observation")
    # Canonical digest of the reported evidence, *not* proof of Git authenticity.
    serialized = json.dumps(observations, sort_keys=True, ensure_ascii=False,
                            separators=(",", ":")).encode("utf-8")
    return {
        "mode": "bounded_git_observations",
        "claims": [{"id": o["id"], "text": o["claim"]} for o in observations],
        "sha256": sha256(serialized).hexdigest(),
        "caveat": (
            "These statements are constructed from the Git scan report, not "
            "written or validated by the language model. Verify a saved "
            "report against its original Git objects before claiming an "
            "independent audit. A structural match cannot prove lineage "
            "or runtime equivalence."
        ),
    }
