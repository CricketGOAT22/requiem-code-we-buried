"""Demonstrate the trust boundary without downloading/running a model.

The transport deliberately returns an unsupported model explanation. The
bounded factual view comes exclusively from the deterministic Git observations.
"""
import json
import tempfile
from pathlib import Path

from backend.exhibit import make_exhibit
from backend.narrator import narrate


def main():
    with tempfile.TemporaryDirectory(prefix="requiem-firewall-") as folder:
        cases = make_exhibit(Path(folder))["records"]
        case = next(c for c in cases if c["possible_successors"])
        def malicious(_payload):
            return {"model": "injected-demo-transport", "response": json.dumps({
                "epitaph": "An echo remains. It lingers in history.",
                "explanation": "The replacement was ordered because of a security bug. Runtime behavior is identical.",
                "evidence_ids": ["E1", "E2", "E3"],
            })}
        result = narrate(case, transport=malicious)
        factual = result["factual_view"]
        print("REQUIEM — THE CITATION TRAP / EVIDENCE FIREWALL")
        print("Source: controlled synthetic Git history. Model output: deliberately injected test response.")
        print("\nUNVERIFIED model explanation (not displayed as fact):")
        print("  " + result["ai_interpretation"]["explanation"])
        print("\nBOUNDED Git-derived factual view:")
        for item in factual["claims"]:
            print(f"  {item['id']}: {item['text']}")
        print("\nGit-report fingerprint (not a proof of authenticity): " + factual["sha256"][:16])
        print("PASS: Unsupported model prose was not promoted to the factual record.")


if __name__ == "__main__":
    main()
