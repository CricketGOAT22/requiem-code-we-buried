"""Start the private local exhibit API: python3 -m scripts.serve"""

from pathlib import Path
import argparse
import json
import tempfile

from backend.exhibit import make_exhibit
from backend.webapi import ExhibitionServer


def main():
    parser = argparse.ArgumentParser(description="Serve synthetic or audited real Git exhibit")
    parser.add_argument("--report", help="Saved JSON from scripts.scan_history (local file)")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="requiem-exhibit-") as temp:
        if args.report:
            exhibit = json.loads(Path(args.report).read_text(encoding="utf-8"))
            if exhibit.get("kind") != "real_git_history" or not isinstance(exhibit.get("records"), list):
                parser.error("--report requires a real Git history report from scripts.scan_history")
            if not exhibit["records"]:
                parser.error("The report contains no cases. Scan more history first.")
        else:
            exhibit = make_exhibit(Path(temp))
        server = ExhibitionServer(("127.0.0.1", args.port), exhibit)
        print(f"\nREQUIEM local Git exhibit — 127.0.0.1:{args.port}", flush=True)
        print(f"Mode: {exhibit.get('kind', 'synthetic_git_fixture')} / {len(exhibit['records'])} cases.", flush=True)
        print("Frontend: run 'npm install' and 'npm run dev' inside frontend/", flush=True)
        print("Model: gemma3:4b, local Ollama at 127.0.0.1:11434", flush=True)
        print("Press Control+C to stop. No arbitrary repository reading or network fetches.\n", flush=True)
        try:
            server.serve_forever(poll_interval=0.25)
        except KeyboardInterrupt:
            print("\nStopping REQUIEM API.")
        finally:
            server.server_close()


if __name__ == "__main__":
    main()
