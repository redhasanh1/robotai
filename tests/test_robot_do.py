"""Full-body tasks: phrasings -> programs, AI programs checked + repaired on the body, both arms, toss/catch."""
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import robot_do as R  # noqa: E402
from hand import brain, motor  # noqa: E402
from hand.inmoov_sim import build_model  # noqa: E402

M = build_model(meshes=False, extra=motor.scene_xml())


def test_known_phrasings_become_programs_that_run_clean():
    for c in R.TASKS:
        prog, unknown = R.plan(c)
        if unknown:
            prog += brain.StubBrain().program(", ".join(unknown), "", "")["program"]
        assert prog, c
        b = motor.Body(M).run(prog)
        assert not b.problems, (c, b.problems)
        assert b.held == {"right": None, "left": None}


def test_pronoun_and_both_arms():
    assert R.plan("grab the orange and put it on the right")[0] == [{"do": "pick", "obj": "ball"},
                                                                   {"do": "place", "obj": "ball", "at": "right"}]
    b = motor.Body(M).run([{"do": "place", "obj": "can", "at": "far left"}], finish=False)
    assert not b.problems and b.pos["can"][0] > 0.2            # crossed to the left arm's side


def test_toss_is_caught_only_if_the_hand_gets_there_in_time():
    ok = motor.Body(M).run([{"do": "pick", "obj": "ball"}, {"do": "toss", "obj": "ball", "to": "left", "height": 0.3}],
                           finish=False)
    assert not ok.problems and ok.held["left"] == "ball"
    b = motor.Body(M)
    b.ARM_SPEED = None
    motor.ARM_SPEED, saved = 0.5, motor.ARM_SPEED                # a very slow arm cannot make the catch
    try:
        slow = motor.Body(M).run([{"do": "pick", "obj": "ball"}, {"do": "toss", "obj": "ball", "to": "left",
                                                                   "height": 0.1}], finish=False)
    finally:
        motor.ARM_SPEED = saved
    assert any("throw higher" in p for p in slow.problems) and slow.held["left"] is None


def test_checker_reports_what_is_wrong():
    b = motor.Body(M).run([{"do": "fly"}, {"do": "joints", "set": {"right_elbow_x": 9}},
                           {"do": "pick", "obj": "dog"}, {"do": "move_hand", "hand": "left", "to": [0.9, 0, 1]},
                           {"do": "grip", "hand": "right", "amount": 1}])
    text = " ".join(b.problems)
    for bit in ("unknown action", "outside its limits", "no dog", "cannot reach", "nothing within reach"):
        assert bit in text


class _AI(BaseHTTPRequestHandler):
    calls = []

    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        text = body["messages"][1]["content"][0]["text"]
        _AI.calls.append(text)
        if "simulator reported" in text:                         # second call: the repair
            prog = [{"do": "pick", "obj": "ball"}, {"do": "toss", "obj": "ball", "to": "left", "height": 0.3}]
        else:                                                      # first call: a mistake the body must catch
            prog = [{"do": "pick", "obj": "ball"}, {"do": "move_hand", "hand": "left", "to": [0.9, -0.3, 1.0]}]
        out = json.dumps({"choices": [{"message": {"content": json.dumps({"program": prog, "say": "ok"})}}]})
        self.send_response(200)
        self.end_headers()
        self.wfile.write(out.encode())


def test_ai_program_is_checked_on_the_body_and_repaired():
    srv = HTTPServer(("127.0.0.1", 0), _AI)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        b = brain.OpenAIBrain(url=f"http://127.0.0.1:{srv.server_port}/v1", model="t", key="")
        lines = []
        prog, problems, _ = R.think("juggle the ball", M, b, lines.append)
    finally:
        srv.shutdown()
    assert len(_AI.calls) == 2 and "cannot reach" in _AI.calls[1]
    assert not problems and prog[-1]["do"] == "toss"


def test_end_markers_and_wait_are_not_problems():
    b = motor.Body(M).run([{"do": "wave"}, {"do": "wait", "seconds": 1}, {"do": "terminate"}, {"do": "done"}])
    assert not b.problems
