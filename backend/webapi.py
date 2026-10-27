"""Local-only API for the REQUIEM React exhibition; no third-party deps.

Serve from 127.0.0.1 only. Browser client uses the Vite /api proxy. All user
requests are limited to immutable indices in a synthetic Git fixture, so no
arbitrary file paths, Git commands, or remote repository fetches are accepted.
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading

from backend.exhibit import public_exhibit
from backend.narrator import NarrationError, narrate


class ExhibitionServer(ThreadingHTTPServer):
    allow_reuse_address = True

    def __init__(self, address, exhibit, *, narrator=narrate):
        super().__init__(address, ExhibitionHandler)
        self.exhibit = exhibit
        self.public = public_exhibit(exhibit)
        self.narrator = narrator
        self.ai_lock = threading.Lock()


class ExhibitionHandler(BaseHTTPRequestHandler):
    def _json(self, code, body):
        content = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        if self.path == "/api/health":
            self._json(200, {"ok": True, "mode": "local", "model": "gemma3:4b"})
        elif self.path == "/api/exhibit":
            self._json(200, self.server.public)
        else:
            self._json(404, {"error": "Unknown endpoint"})

    def do_POST(self):
        if self.path != "/api/narrate":
            self._json(404, {"error": "Unknown endpoint"})
            return
        if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
            self._json(415, {"error": "Expected application/json"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._json(400, {"error": "Invalid body length"})
            return
        if not 1 <= length <= 512:
            self._json(413, {"error": "Request body must be 1–512 bytes"})
            return
        try:
            payload = json.loads(self.rfile.read(length))
        except (UnicodeDecodeError, ValueError):
            self._json(400, {"error": "Invalid JSON"})
            return
        if not isinstance(payload, dict) or set(payload) != {"id"}:
            self._json(400, {"error": "Only a fixture record ID is supported"})
            return
        index = payload["id"]
        if type(index) is not int or not 0 <= index < len(self.server.exhibit["records"]):
            self._json(400, {"error": "Unknown fixture record ID"})
            return
        if not self.server.ai_lock.acquire(blocking=False):
            self._json(429, {"error": "Gemma is already narrating another function. Try again shortly."})
            return
        try:
            record = self.server.exhibit["records"][index]
            report = self.server.narrator(record, model="gemma3:4b", timeout=180)
            self._json(200, report)
        except NarrationError as exc:
            self._json(503, {"error": str(exc)})
        except Exception:  # Don't expose local paths or other internals to a browser
            self._json(500, {"error": "Unexpected local server error"})
        finally:
            self.server.ai_lock.release()

    def log_message(self, format, *args):
        return  # Keep terminal focused on user-facing startup information.
