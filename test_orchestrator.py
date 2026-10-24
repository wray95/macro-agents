import unittest
from orchestrator import deliberate, ROLES

class DeliberationTests(unittest.TestCase):
    def test_cross_references_and_synthesis(self):
        calls = []
        def fake(prompt, role, backend, model):
            calls.append((role, prompt))
            return "Final answer" if role == "Synthesizer" else f"{role} opinion"
        result = deliberate("What should we do?", rounds=1, caller=fake)
        self.assertEqual(result["answer"], "Final answer")
        self.assertEqual(len(calls), 11)
        self.assertEqual(len(result["history"]), 2)
        for role, prompt in calls[5:10]:
            self.assertIn("Other agents' views", prompt)
            self.assertNotIn(f"{role}:\n{role} opinion", prompt)
            for peer in ROLES:
                if peer != role:
                    self.assertIn(f"{peer}:\n{peer} opinion", prompt)

    def test_invalid_rounds(self):
        with self.assertRaises(ValueError):
            deliberate("question", rounds=4)

if __name__ == "__main__":
    unittest.main()

class MemoryTests(unittest.TestCase):
    def test_shared_memory_and_forget(self):
        import tempfile
        from pathlib import Path
        from memory import add, relevant, forget
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "memory.db"
            mid = add("Our onboarding flow should be accessible", path)
            self.assertIn("accessible", relevant("onboarding flow", path))
            calls = []
            def fake(prompt, role, backend, model):
                calls.append(prompt)
                return role
            deliberate("onboarding flow", rounds=1, caller=fake, memory=relevant("onboarding flow", path))
            self.assertEqual(len(calls), 11)
            self.assertTrue(all("accessible" in prompt for prompt in calls))
            self.assertTrue(forget(mid, path))
            self.assertEqual(relevant("onboarding flow", path), "")

class CompetitionTests(unittest.TestCase):
    def test_challenge_and_bounded_context(self):
        calls = []
        def fake(prompt, role, backend, model):
            calls.append((role, prompt))
            return "x" * 1200
        deliberate("design question", rounds=1, caller=fake, memory="context")
        for role, prompt in calls[5:10]:
            self.assertIn("Challenge the strongest rival", prompt)
            self.assertIn("context", prompt)
            self.assertNotIn("x" * 1200, prompt)
        self.assertIn("Judge the competing answers", calls[-1][1])

class APITests(unittest.TestCase):
    def test_api_backend_request(self):
        import json
        import os
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer
        from unittest.mock import patch
        from orchestrator import call_model
        seen = []
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                seen.append((self.path, data, self.headers["Authorization"]))
                body = json.dumps({"choices": [{"message": {"content": "OK"}}]}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            def log_message(self, *args):
                pass
        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with patch.dict(os.environ, {"AI_API_KEY": "test-key", "AI_BASE_URL": f"http://127.0.0.1:{server.server_port}/v1"}):
                self.assertEqual(call_model("question", "Architect", "api", "test-model"), "OK")
            self.assertEqual(seen[0][0], "/v1/chat/completions")
            self.assertEqual(seen[0][1]["model"], "test-model")
            self.assertEqual(seen[0][1]["max_tokens"], 350)
            self.assertEqual(seen[0][2], "Bearer test-key")
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

class FreebuffBridgeTests(unittest.TestCase):
    def test_prompt_has_five_roles_memory_and_question(self):
        from orchestrator import freebuff_prompt, ROLES
        prompt = freebuff_prompt("How do we launch?", "Launch offline first")
        for role in ROLES:
            self.assertIn(role, prompt)
        self.assertIn("Launch offline first", prompt)
        self.assertIn("How do we launch?", prompt)
        self.assertIn("Do not edit files", prompt)
