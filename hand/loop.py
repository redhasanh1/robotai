"""The brain loop, end to end in simulation:

    look -> brain CHOOSES a grasp family (memory in the prompt)
         -> sample N variants locally
         -> physics PREDICTS each one (nominal sim = the robot's imagination)
         -> brain RANKS all N in one call
         -> hand EXECUTES the best one in the world
         -> brain VERIFIES from the camera; on failure the cause goes to memory and the next-ranked grasp is tried

The "world" is a second sim with randomised object mass/friction/placement and servo speed, so the imagination is
never exactly right - the same gap the real hand will have. Time is virtual: brain latency comes from the brain
(measured for real endpoints, profiled for StubBrain) plus measured physics compute, so a whole benchmark runs in
minutes without waiting for real seconds.
"""
import os
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field

import numpy as np

from . import primitives, sim
from .brain import StubBrain
from .config import HandConfig


_POOL = None


_GPU = {}


def predict_all(qs, obj):
    """Physics prediction for every candidate.
    - n >= 64 and a CUDA GPU: NVIDIA MuJoCo Warp, all candidates as parallel worlds (1024 in 1.9 s on a 1660 Ti)
    - otherwise parallel across CPU cores: 16 candidates 1.03 s serial -> 0.18 s on 8 workers
    HAND_WORKERS=0 forces serial CPU, HAND_GPU=0 disables the GPU path."""
    global _POOL
    if len(qs) >= 64 and os.environ.get("HAND_GPU", "1") != "0":
        try:
            from .gpu_sim import BatchGrasp
            key = (obj, len(qs))
            if key not in _GPU:
                _GPU[key] = BatchGrasp(obj, len(qs))
            return [dict(r, touching=[], slip_t=None) for r in _GPU[key].evaluate(qs)]
        except Exception:                     # no CUDA / no mujoco_warp: fall back to CPU
            pass
    workers = int(os.environ.get("HAND_WORKERS", min(8, (os.cpu_count() or 2) - 1)))
    if workers <= 1 or len(qs) < 4:
        return [sim.evaluate(q, obj) for q in qs]
    if _POOL is None:
        _POOL = ProcessPoolExecutor(workers)
    return list(_POOL.map(sim.evaluate, qs, [obj] * len(qs)))


def randomized_world(obj, seed, holdout=False):
    """A sim that disagrees with the nominal model the way reality will.
    holdout=True also swaps the CONTACT MODEL (softer contacts, pyramidal friction cone, no torsional friction,
    lower impedance ratio) - physics the imagination does not share and that nothing was tuned on."""
    rng = np.random.default_rng(seed)
    servos = HandConfig().servos
    for s in servos:
        s.v_max *= rng.uniform(0.75, 1.15)
        s.tau *= rng.uniform(0.8, 1.5)
        s.backlash = rng.uniform(0.01, 0.06)
    w = sim.SimHand(obj, servos=servos)
    m = w.model
    bid = m.body("object").id
    gid = [g for g in range(m.ngeom) if m.geom_bodyid[g] == bid]
    m.body_mass[bid] *= rng.uniform(0.6, 1.6)
    for g in gid:
        m.geom_friction[g, 0] *= rng.uniform(0.7, 1.2)
    if holdout:
        import mujoco
        m.opt.cone = mujoco.mjtCone.mjCONE_PYRAMIDAL
        m.opt.impratio = 1.0
        m.geom_solref[:] = (0.02, 1.0)
        m.geom_condim[:] = 3
    adr = m.jnt_qposadr[m.body_jntadr[bid]]
    w.data.qpos[adr:adr + 2] += rng.uniform(-0.006, 0.006, 2)   # object not exactly where it was last time
    w._settle_object()
    return w


@dataclass
class Result:
    success: bool
    tries: int
    seconds: float                      # virtual wall-clock: brain latency + physics compute
    brain_s: float
    physics_s: float
    family: str
    chosen: dict = field(default_factory=dict)
    log: list = field(default_factory=list)


def _plan(goal, obj, brain, memory, n, rng, use_memory, image, avoid=()):
    """choose -> sample -> predict -> rank. Returns (family, ranked candidates, brain_s, physics_s, log)."""
    brain_s = physics_s = 0.0
    log = []
    mem_text = memory.as_prompt(goal, obj) if (memory is not None and use_memory) else "No past attempts yet."
    if avoid:
        mem_text += "\nAlready failed just now, do not repeat: " + ", ".join(sorted(avoid))
    c = brain.choose(goal, image, mem_text, obj_hint=obj)
    brain_s += brain.last_latency
    fam = c.get("family") if c.get("family") in primitives.FAMILIES else "power"
    if fam in avoid:                                    # model ignored the hint: take the next untried family
        fam = next((f for f in primitives.FAMILIES if f not in avoid), fam)
    best = memory.best(obj) if (memory is not None and use_memory) else None
    center = (best["s"], best["t"]) if best and best["family"] == fam else None
    cands = primitives.sample(fam, n, rng, center=center)
    log.append({"step": "choose", "family": fam, "why": c.get("why", ""), "latency": brain.last_latency})

    t0 = time.perf_counter()
    for cand, pred in zip(cands, predict_all([c["q"] for c in cands], obj)):
        cand["pred"] = pred
    physics_s += time.perf_counter() - t0

    order = [0]
    if n > 1:
        r = brain.rank(goal, image, cands, mem_text)
        brain_s += brain.last_latency
        order = [i for i in r.get("order", []) if isinstance(i, int) and 0 <= i < n]
        order += [i for i in range(n) if i not in order]
        log.append({"step": "rank", "order": order[:5], "why": r.get("why", ""), "latency": brain.last_latency})
    return fam, [cands[i] for i in order], brain_s, physics_s, log


def attempt(goal, obj, brain, memory=None, n=8, seed=0, max_tries=3, verify=True, use_memory=True,
            render=False, rng=None, veto=None, max_replans=2, holdout=False, world=None):
    """One task. With verify=True the robot checks itself after every try and replans on failure
    (new family if the physics had no better idea); with verify=False it assumes success, like most robots.
    veto (default: on when n > 1): if physics predicts that even the best-ranked grasp drops, replan with another
    family BEFORE touching anything - thinking is cheap, a dropped object is not."""
    rng = rng or np.random.default_rng(seed)
    veto = n > 1 if veto is None else veto
    make_world = (lambda: world) if world is not None else (lambda: randomized_world(obj, seed, holdout))
    world = make_world()                     # sim by default; hand.hardware.HardwareWorld for the real hand
    image = world.render() if render else None
    fam, ranked, brain_s, physics_s, log = _plan(goal, obj, brain, memory, n, rng, use_memory, image)
    failed_fams, k = set(), 0
    for _ in range(max_replans if veto else 0):
        if any(c["pred"]["held"] for c in ranked):
            break
        failed_fams.add(fam)
        log.append({"step": "veto", "family": fam, "why": "physics predicts every variant drops"})
        fam, ranked, b, p, lg = _plan(goal, obj, brain, memory, n, rng, use_memory, image, failed_fams)
        brain_s, physics_s = brain_s + b, physics_s + p
        log += lg
    ranked.sort(key=lambda c: not c["pred"]["held"])      # stable: keeps the brain's order among believed holds
    success, tries, chosen = False, 0, ranked[0]
    while tries < max_tries:
        tries += 1
        if k >= len(ranked) or (tries > 1 and not ranked[k]["pred"]["held"]):
            # nothing left that physics believes in: replan with a different family
            failed_fams.add(fam)
            fam, ranked, b, p, lg = _plan(goal, obj, brain, memory, n, rng, use_memory, image, failed_fams)
            brain_s, physics_s, k = brain_s + b, physics_s + p, 0
            log += lg
        chosen = ranked[k]
        k += 1
        if tries > 1:
            world = make_world()                           # object put back, same world
        out = world.grasp_test(chosen["q"])
        truth = out["held"]
        if verify and out["slip_t"] is not None:
            # fast path: the local 50 Hz slip check saw the object move off the palm - no model call needed
            believed, cause = False, f"slipped {out['slip_t']:.2f} s after turning over (local slip check)"
        elif verify:
            # slow path: nothing slipped locally, ask the model to confirm from the camera
            img = world.render() if render else None
            v = brain.verdict(goal, img, truth) if isinstance(brain, StubBrain) else brain.verdict(goal, img)
            brain_s += brain.last_latency
            believed, cause = bool(v.get("held")), v.get("cause", "")
        else:
            believed, cause = True, ""
        log.append({"step": "execute", "try": tries, "cand": {x: chosen[x] for x in ("family", "s", "t")},
                    "pred": chosen["pred"]["held"], "truth": truth, "believed": believed})
        if memory is not None:
            # memory holds what the robot BELIEVES happened - it never sees the ground truth
            memory.add(goal, obj, chosen, believed, "" if believed else (cause or "dropped"))
        success = truth
        if believed or not verify:
            break
    return Result(success, tries, brain_s + physics_s, brain_s, physics_s, chosen["family"],
                  {x: chosen[x] for x in ("family", "s", "t")}, log)
