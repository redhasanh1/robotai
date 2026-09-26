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


def _lenient(kind, text, n=0):
    """Small models often answer in words instead of JSON (SmolVLM-500M: 'power: whole hand wraps the object').
    Try JSON first, then read the words - a robot should not freeze because of formatting."""
    try:
        return _json(text), True
    except (ValueError, json.JSONDecodeError):
        pass
    low = text.lower()
    if kind == "choose":
        hits = [(low.find(f), f) for f in primitives.FAMILIES if f in low]
        fam = min(hits)[1] if hits else "power"
        return {"family": fam, "why": text.strip()[:120]}, False
    if kind == "plan":
        return {"steps": [], "say": text.strip()[:160]}, False
    if kind == "program":
        return {"program": [], "say": text.strip()[:160]}, False
    if kind == "goal":
        return {"wrong": "", "goal": text.strip()[:200]}, False
    if kind == "rank":
        order = []
        for x in re.findall(r"\d+", text):
            if int(x) < n and int(x) not in order:
                order.append(int(x))
        return {"order": order, "why": text.strip()[:120]}, False
    held = (bool(re.search(r"\b(yes|held|holding|still in|true)\b", low))
            and not re.search(r"\b(no|not|dropped|fell|false)\b", low))
    return {"held": held, "cause": "" if held else text.strip()[:80]}, False


SKILLS = {"grasp": "close the hand on an object that is in the palm and hold it (works now)"}
FUTURE = {"reach": "move the arm to an object (needs the arm)", "place": "put a held object down (needs the arm)",
          "wipe": "rub a surface (needs the arm)", "navigate": "drive or walk somewhere (needs the base or legs)",
          "open": "open a door, drawer or tap (needs the arm)", "pour": "tip a held container (needs the arm)"}
OBJECT_WORDS = {"ball": "ball", "orange": "ball", "apple": "ball", "can": "can", "bottle": "can", "cup": "can",
                "block": "block", "cube": "block", "box": "block", "bar": "bar", "stick": "bar", "pen": "bar",
                "handle": "bar", "spoon": "bar", "fork": "bar"}


def find_object(text):
    """First known object word in a sentence -> sim object name, or None."""
    for w in re.findall(r"[a-z]+", text.lower()):
        if w in OBJECT_WORDS:
            return OBJECT_WORDS[w]
        if w.endswith("s") and w[:-1] in OBJECT_WORDS:
            return OBJECT_WORDS[w[:-1]]
    return None


class OpenAIBrain:
    def __init__(self, url=None, model=None, key=None, timeout=30):
        self.url = (url or os.environ.get("BRAIN_URL") or "https://api.cerebras.ai/v1").rstrip("/")
        self.model = model or os.environ.get("BRAIN_MODEL") or os.environ.get("CEREBRAS_MODEL") or "qwen-3.8-27b"
        self.key = key or os.environ.get("BRAIN_KEY") or os.environ.get("CEREBRAS_API_KEY") or ""
        self.timeout = timeout
        self.last_latency = 0.0
        self.calls = []
        self.json_ok = []          # per call: did the model follow the JSON format (reported by brain_live)

    def _ask(self, text, image=None, max_tokens=300, kind="", n=0):
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
        reply, ok = _lenient(kind, out["choices"][0]["message"]["content"], n)
        self.json_ok.append(ok)
        return reply

    def goal(self, command, world):
        """Scene-state step before planning: what is wrong now, and what should be true when the robot is done.
        Small models jump from words straight to actions ('spilled' -> tidy the remote); naming the end state first
        gives the planner something to aim at. Generic - no task-specific rules."""
        return self._ask(
            f'A person in this home says: "{command}"\n\n{world}\n\nDo not plan actions yet. Think about the situation: '
            'what is wrong or needed right now, and what should be true when you are finished? '
            'Reply with ONE JSON object: {"wrong": "<what is wrong now>", "goal": "<what should be true after>"}',
            None, 120, "goal")

    def choose_step(self, command, prog, k, error, options):
        """One-step repair: the failing step, the body's error, and replacements that already work -> an index."""
        steps = "\n".join(f"{i + 1}. {json.dumps(a)}" + ("   <- FAILED" if i == k else "") for i, a in enumerate(prog))
        opts = "\n".join(f"{i}: " + ("remove this step" if o["do"] == "remove" else json.dumps(o))
                         for i, o in enumerate(options))
        r = self._ask(
            f'Request: "{command}"\nThe robot\'s plan:\n{steps}\n\nStep {k + 1} failed on the body: {error}\n'
            f"Replacements for step {k + 1} (each one works on the body):\n{opts}\n\n"
            'Which one best does what the person asked? Reply with ONE JSON object: {"pick": <number>}',
            None, 20, "rank", len(options))
        if "pick" in r:
            try:
                return int(r["pick"])
            except (TypeError, ValueError):
                return 0
        return (r.get("order") or [0])[0]

    def program(self, command, world, actions_doc, problems=None, previous=None, goal=""):
        """Write (or repair) a motor program for the full robot: -> {"program": [...], "say": "..."}."""
        fix = ""
        if problems:
            fix = ("\nYour previous program was:\n" + json.dumps(previous) + "\nThe body simulator reported:\n- " +
                   "\n- ".join(problems) + "\nWrite a corrected program that avoids these problems.")
        return self._ask(
            "You control a humanoid robot's two arms in a simulator. Write a program for this request, thinking about "
            "how a person would do it with two hands and the objects on the table.\n"
            f'Request: "{command}"\n' + (f"The situation: {goal}\n" if goal else "") +
            f'\n{world}\n\nAvailable actions (JSON):\n{actions_doc}\n{fix}\n'
            'Reply with ONE JSON object: {"program": [ ...actions... ], "say": "<one short sentence to the person>"}',
            None, 700, "program")

    def plan(self, command, image=None):
        """Break a spoken command into skill steps. Honest about skills the robot doesn't have yet."""
        skills = "\n".join(f"- {k}: {v}" for k, v in {**SKILLS, **FUTURE}.items())
        r = self._ask(
            f'Command: "{command}"\nSkills:\n{skills}\nBreak the command into steps using only these skills. '
            'Reply {"steps": [{"skill": "<name>", "object": "<thing>"}], "say": "<one short sentence to the user>"}',
            image, 200, "plan")
        return _finish_plan(command, r)

    def choose(self, goal, image, memory_text, obj_hint=""):
        return self._ask(
            f"Task: {goal}\nObject: {obj_hint or 'see image'}\nGrasp families:\n{primitives.describe()}\n\n"
            f"{memory_text}\n\nPick the grasp family most likely to hold. "
            'Reply {"family": "<name>", "why": "<one short sentence>"}', image, 120, "choose")

    def rank(self, goal, image, cands, memory_text):
        rows = "\n".join(f"{i}: {c['family']} s={c['s']:.2f} t={c['t']:.2f} | physics predicts: "
                         f"{'holds' if c['pred']['held'] else 'drops'}, touching {','.join(c['pred']['touching']) or 'nothing'}, "
                         f"object {c['pred']['dist'] * 100:.1f} cm from palm" for i, c in enumerate(cands))
        return self._ask(
            f"Task: {goal}\nCandidate grasps, each already simulated:\n{rows}\n\n{memory_text}\n\n"
            "Rank ALL candidates best first, using the image, the physics predictions and past attempts. "
            'Reply {"order": [indices...], "why": "<one short sentence>"}', image, 60 + 8 * len(cands), "rank",
            len(cands))

    def verdict(self, goal, image):
        return self._ask(
            f"Task: {goal}\nThis image is right after the grasp, hand turned over. Is the object still in the hand? "
            'Reply {"held": true|false, "cause": "<if dropped, the likely reason in under 12 words>"}', image, 60,
            "verdict")


def _finish_plan(command, r):
    """Normalise a plan: map objects to the sim's names, split steps into can-do-now vs needs-hardware."""
    steps = [x for x in r.get("steps", []) if isinstance(x, dict)]
    if not steps and find_object(command):
        steps = [{"skill": "grasp", "object": find_object(command)}]
    for x in steps:
        x["sim_object"] = find_object(str(x.get("object", ""))) or find_object(command)
        x["ready"] = x.get("skill") in SKILLS and x["sim_object"] is not None
    return {"steps": steps, "say": r.get("say", ""),
            "missing": sorted({x.get("skill") for x in steps if x.get("skill") not in SKILLS})}


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

    def program(self, command, world, actions_doc, problems=None, previous=None, goal=""):
        """No model: translate what the keyword planner understands, plus a few built-in routines."""
        self._cost(120)
        low = command.lower()
        objs = [o for o in ("ball", "can", "block", "bar") if o in low] or \
               [find_object(command)] if find_object(command) else []
        o = objs[0] if objs else "ball"
        if re.search(r"\bjuggl", low):
            prog = [{"do": "pick", "obj": o}] + [{"do": "toss", "obj": o, "to": s, "height": 0.3}
                                                  for s in ("left", "right", "left", "right")]
            return {"program": prog, "say": f"juggling the {o} between my hands"}
        if re.search(r"\b(swap|switch) hands|other hand|pass\b", low):
            return {"program": [{"do": "pick", "obj": o}, {"do": "pass", "obj": o, "to": "left"},
                                {"do": "pass", "obj": o, "to": "right"}], "say": "passing it across"}
        if re.search(r"\b(throw|toss)\b", low):
            return {"program": [{"do": "pick", "obj": o}, {"do": "toss", "obj": o, "to": "right", "height": 0.3}],
                    "say": "up it goes"}
        return {"program": [], "say": ""}

    def plan(self, command, image=None):
        """Keyword planner: grasp known objects; name the missing skills for everything else."""
        self._cost(60)
        low = command.lower()
        obj = find_object(command)
        steps = []
        if any(w in low for w in ("dish", "wash", "clean", "wipe")):
            steps = [{"skill": "reach", "object": "plate"}, {"skill": "grasp", "object": "plate"},
                     {"skill": "navigate", "object": "sink"}, {"skill": "wipe", "object": "plate"},
                     {"skill": "place", "object": "rack"}]
        elif any(w in low for w in ("walk", "dog", "go to", "bring", "fetch")):
            steps = [{"skill": "navigate", "object": "leash"}, {"skill": "grasp", "object": obj or "leash"},
                     {"skill": "navigate", "object": "outside"}]
        elif obj:
            steps = [{"skill": "grasp", "object": obj}]
        r = _finish_plan(command, {"steps": steps})
        r["say"] = ("On it." if steps and not r["missing"] else
                    f"I can plan that, but I still need these skills: {', '.join(r['missing'])}." if steps else
                    "I don't know how to do that yet. Try: pick up the ball / can / block / bar.")
        return r

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
