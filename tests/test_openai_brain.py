"""The real-model code path, tested against a local fake OpenAI-compatible server (no key, no network)."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import numpy as np
import pytest

from hand import brain, loop, memory

SEEN = []


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        SEEN.append({"auth": self.headers.get("Authorization"), "body": body})
        text = body["messages"][1]["content"][0]["text"]
        if "Pick the grasp family" in text:
            reply = 'Sure! {"family": "power", "why": "round object"}'           # chatter around the JSON
        elif "Rank ALL" in text:
            n = text.count("physics predicts")
            reply = json.dumps({"order": list(range(n))[::-1], "why": "reversed"})
        else:
            reply = '{"held": true, "cause": ""}'
        out = json.dumps({"choices": [{"message": {"content": reply}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(out)


@pytest.fixture(scope="module")
def server():
    srv = HTTPServer(("127.0.0.1", 0), Fake)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}/v1"
    srv.shutdown()


def test_openai_brain_calls_and_parses(server):
    b = brain.OpenAIBrain(url=server, model="test-model", key="k")
    img = np.zeros((24, 32, 3), np.uint8)
    assert b.choose("pick up the ball", img, "", "ball")["family"] == "power"
    last = SEEN[-1]
    assert last["auth"] == "Bearer k" and last["body"]["model"] == "test-model"
    assert last["body"]["messages"][1]["content"][1]["image_url"]["url"].startswith("data:image/jpeg;base64,")
    assert b.last_latency > 0


def test_real_brain_through_the_loop(server):
    b = brain.OpenAIBrain(url=server, model="m", key="")
    r = loop.attempt("pick up the can", "can", b, memory.Memory(), n=4, seed=0)
    assert r.tries >= 1 and r.brain_s > 0
    assert SEEN[-1]["auth"] is None                   # no key -> no Authorization header (local servers)


def test_bad_reply_raises():
    with pytest.raises(ValueError):
        brain._json("I cannot help with that")
