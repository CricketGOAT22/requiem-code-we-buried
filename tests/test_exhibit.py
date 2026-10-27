"""End-to-end fixture and HTTP boundary tests, no model download required."""

import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from backend.exhibit import make_exhibit, public_exhibit
from backend.webapi import ExhibitionServer


class ExhibitTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.exhibit = make_exhibit(Path(self.temporary.name))

    def tearDown(self):
        self.temporary.cleanup()

    def test_five_deletions_and_context_difference(self):
        report = public_exhibit(self.exhibit)
        self.assertEqual(report["kind"], "synthetic_git_fixture")
        self.assertEqual(report["summary"]["removed"], 5)
        self.assertEqual(report["summary"]["possibleSurvivors"], 4)
        self.assertEqual(report["summary"]["unmatched"], 1)
        records = {stone["name"]: stone for stone in report["stones"]}
        self.assertEqual(records["check_age"]["possibleSuccessors"][0]["name"], "is_adult")
        self.assertEqual(records["count_echoes"]["possibleSuccessors"][0]["name"], "count_echoes")
        self.assertEqual(records["summon"]["possibleSuccessors"][0]["name"], "greet")
        self.assertFalse(records["forgotten"]["possibleSuccessors"])
        trap = records["can_enter"]
        self.assertEqual(trap["possibleSuccessors"][0]["similarity"], 1.0)
        self.assertEqual(trap["possibleSuccessors"][0]["name"], "can_enter_v2")
        self.assertEqual(trap["contextWarnings"][0]["before"], 18)
        self.assertEqual(trap["contextWarnings"][0]["after"], 21)
        self.assertTrue(any("MIN_AGE" in x["claim"] for x in trap["observations"]))
        # Fixture demonstrates non-equivalence of identical function ASTs:
        self.assertTrue(20 >= 18)
        self.assertFalse(20 >= 21)

    def test_evidence_is_separate_from_model_text(self):
        for stone in public_exhibit(self.exhibit)["stones"]:
            self.assertEqual(stone["observations"][0]["id"], "E1")
            self.assertEqual(stone["observations"][1]["id"], "E2")
            self.assertIn(stone["name"], stone["observations"][0]["claim"])
            self.assertNotIn("ai_interpretation", stone)

    def test_local_api_reads_and_mock_narration(self):
        def fake_narrator(record, **kwargs):
            return {"subject": record["function"], "ai_interpretation": {"epitaph": "A demo."}}

        server = ExhibitionServer(("127.0.0.1", 0), self.exhibit, narrator=fake_narrator)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            with urlopen(base + "/api/exhibit", timeout=5) as response:
                body = json.load(response)
            self.assertEqual(len(body["stones"]), 5)
            self.assertEqual(body["kind"], "synthetic_git_fixture")
            payload = json.dumps({"id": 0}).encode()
            request = Request(base + "/api/narrate", data=payload,
                              headers={"Content-Type": "application/json"})
            with urlopen(request, timeout=5) as response:
                result = json.load(response)
            self.assertEqual(result["subject"], self.exhibit["records"][0]["function"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_rejects_invalid_ids_and_content_type(self):
        server = ExhibitionServer(("127.0.0.1", 0), self.exhibit, narrator=lambda *args, **kwargs: None)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}/api/narrate"
        try:
            for value in (-1, 500, True, "0"):
                req = Request(base, data=json.dumps({"id": value}).encode(),
                              headers={"Content-Type": "application/json"})
                with self.assertRaises(HTTPError) as raised:
                    urlopen(req, timeout=5)
                self.assertEqual(raised.exception.code, 400)
            req = Request(base, data=b'{"id":0}', headers={"Content-Type": "text/plain"})
            with self.assertRaises(HTTPError) as raised:
                urlopen(req, timeout=5)
            self.assertEqual(raised.exception.code, 415)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
