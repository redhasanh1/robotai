"""The brain: one interface, any OpenAI-compatible endpoint. Local model, rented GPU (vLLM) or Cerebras is just
a different BRAIN_URL - nothing else in the stack changes. That swap is the capstone experiment.

Three questions, each ONE call no matter how many candidates (the model sees all N at once):
    choose(goal, image, memory)            -> {"family", "why"}            which kind of grasp
    rank(goal, image, candidates, memory)  -> {"order": [i...], "why"}     best of N, given physics predictions
    verdict(goal, image)                   -> {"held": bool, "cause"}      did it actually work (self-check)

Env: BRAIN_URL (default Cerebras), BRAIN_MODEL, BRAIN_KEY (falls back to CEREBRAS_API_KEY). Keys never logged.

StubBrain answers the same questions with fixed rules and a latency model, so the loop, tests and benchmark run
with no network. Its latency profiles are ASSUMPTIONS until tools/cerebras_latency.py measures the real ones.
"""
import base64
import json
import os
import re
import time
import urllib.request

import numpy as np

from . import primitives

SYSTEM = ("You control a 5-finger robot hand (thumb, index, middle, ring, pinky; one tendon servo per finger, "
          "flexion 0=open 1=closed) that picks things up and must keep holding them when the hand turns over. "
          "Answer with ONE JSON object and nothing else.")


def _jpeg_b64(img):
    import cv2
    ok, buf = cv2.imencode(".jpg", img[:, :, ::-1] if img.ndim == 3 else img, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return base64.b64encode(buf.tobytes()).decode()


def _json(text):
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError(f"no JSON in reply: {text[:200]!r}")
    return json.loads(m.group(0))


class OpenAIBrain:
    def __init__(self, url=None, model=None, key=None, timeout=30):
        self.url = (url or os.environ.get("BRAIN_URL") or "https://api.cerebras.ai/v1").rstrip("/")
        self.model = model or os.environ.get("BRAIN_MODEL") or os.environ.get("CEREBRAS_MODEL") or "qwen-3.8-27b"
        self.key = key or os.environ.get("BRAIN_KEY") or os.environ.get("CEREBRAS_API_KEY") or ""
        self.timeout = timeout
        self.last_latency = 0.0
        self.calls = []

    def _ask(self, text, image=None, max_tokens=300):
        content = [{"type": "text", "text": text}]
        if image is not None:
            content.append({"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + _jpeg_b64(image)}})
        body = json.dumps({"model": self.model, "max_tokens": max_tokens, "temperature": 0.2,
                           "messages": [{"role": "system", "content": SYSTEM},
                                        {"role": "user", "content": content}]}).encode()
        headers = {"Content-Type": "application/json"}
        if self.key:
            headers["Authorization"] = "Bearer " + self.key
        req = urllib.request.Request(self.url + "/chat/completions", data=body, headers=headers)
        t0 = time.perf_counter()
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            out = json.loads(r.read())
        self.last_latency = time.perf_counter() - t0
        self.calls.append(self.last_latency)
        return _json(out["choices"][0]["message"]["content"])

    def choose(self, goal, image, memory_text, obj_hint=""):
        return self._ask(
            f"Task: {goal}\nObject: {obj_hint or 'see image'}\nGrasp families:\n{primitives.describe()}\n\n"
            f"{memory_text}\n\nPick the grasp family most likely to hold. "
            'Reply {"family": "<name>", "why": "<one short sentence>"}', image, 120)

    def rank(self, goal, image, cands, memory_text):
        rows = "\n".join(f"{i}: {c['family']} s={c['s']:.2f} t={c['t']:.2f} | physics predicts: "
                         f"{'holds' if c['pred']['held'] else 'drops'}, touching {','.join(c['pred']['touching']) or 'nothing'}, "
                         f"object {c['pred']['dist'] * 100:.1f} cm from palm" for i, c in enumerate(cands))
        return self._ask(
            f"Task: {goal}\nCandidate grasps, each already simulated:\n{rows}\n\n{memory_text}\n\n"
            "Rank ALL candidates best first, using the image, the physics predictions and past attempts. "
            'Reply {"order": [indices...], "why": "<one short sentence>"}', image, 60 + 8 * len(cands))

    def verdict(self, goal, image):
        return self._ask(
            f"Task: {goal}\nThis image is right after the grasp, hand turned over. Is the object still in the hand? "
            'Reply {"held": true|false, "cause": "<if dropped, the likely reason in under 12 words>"}', image, 60)


# ---------------------------------------------------------------- no-network stand-in
PROFILES = {
    # name: (seconds to first token, output tokens per second). ASSUMED numbers, replace with measurements.
    "local_1660ti": (1.8, 25.0),     # small VLM on the laptop GPU
    "rented_gpu":   (0.6, 90.0),     # 30B-class VLM on a rented L4/A10 with vLLM
    "cerebras":     (0.25, 1500.0),  # Cerebras inference API
    "instant":      (0.0, 1e9),
}
PRIOR = {"ball": "power", "can": "power", "bottle": "power", "cup": "power", "block": "tripod", "cube": "tripod",
         "cap": "tripod", "bar": "hook", "handle": "hook", "pen": "pinch", "card": "lateral"}


class StubBrain:
    """Same interface as OpenAIBrain. Rules instead of a model; latency simulated from a profile."""

    def __init__(self, profile="instant", verdict_error=0.0, seed=0):
        self.ttft, self.tps = PROFILES[profile]
        self.profile = profile
        self.verdict_error = verdict_error
        self.rng = np.random.default_rng(seed)
        self.last_latency = 0.0
        self.calls = []

    def _cost(self, out_tokens):
        self.last_latency = self.ttft + out_tokens / self.tps
        self.calls.append(self.last_latency)

    def choose(self, goal, image, memory_text, obj_hint=""):
        """What a sensible model does with the prompt: reuse what held on this object, avoid what only dropped."""
        self._cost(40)
        held, dropped = {}, set()
        for fam, ok in re.findall(r"- " + re.escape(obj_hint) + r": (\w+) .*?-> (HELD|DROPPED)", memory_text):
            if ok == "HELD":
                held[fam] = held.get(fam, 0) + 1
            else:
                dropped.add(fam)
        m = re.search(r"do not repeat: (.*)", memory_text)
        avoid = set(m.group(1).split(", ")) if m else set()
        if held:
            fam = max(held, key=held.get)
            if fam not in avoid:
                return {"family": fam, "why": "held this object before"}
        order = [PRIOR.get(obj_hint, "power")] + list(primitives.FAMILIES)
        fam = next((f for f in order if f not in avoid and f not in dropped), order[0])
        return {"family": fam, "why": "prior for this object" if fam == order[0] else "prior failed, trying another"}

    def rank(self, goal, image, cands, memory_text):
        self._cost(20 + 8 * len(cands))
        score = [(c["pred"]["held"], len(c["pred"]["touching"]), -c["pred"]["dist"]) for c in cands]
        return {"order": sorted(range(len(cands)), key=lambda i: score[i], reverse=True), "why": "physics score"}

    def verdict(self, goal, image, truth=None):
        self._cost(20)
        held = bool(truth) if self.rng.random() >= self.verdict_error else not truth
        return {"held": held, "cause": "" if held else "fingers did not close around it"}


def make(kind=None):
    """BRAIN=stub:<profile> for offline runs, anything else -> OpenAI-compatible endpoint."""
    kind = kind or os.environ.get("BRAIN", "stub:instant")
    if kind.startswith("stub"):
        return StubBrain(kind.split(":", 1)[1] if ":" in kind else "instant")
    return OpenAIBrain()
