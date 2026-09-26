"""Does the arm hit anything on the way? Replay a planned motion and let MuJoCo report robot-vs-house contacts.

The house sim is kinematic (poses are played back, nothing is pushed), so every geom has collisions off. For the
check they are switched on for robot-vs-house pairs only: robot links against counters, containers, the person, the
wall and objects. Not robot-vs-robot (neighbouring links of the InMoov mesh overlap by design) and not the floor.
Allowed: a hand touching the object its current step is about (grasping is contact).

    hits = collide.sweep(m, body)        # body = HomeBody after .run(program); -> [{"step", "t", "robot", "hit"}]
"""
import mujoco
import numpy as np

from . import motor

ROBOT, HOUSE = 2, 2            # contype/conaffinity bit used only during the check
HAND_WORDS = ("hand", "palm", "finger", "thumb", "index", "middle", "ring", "pinky", "wrist")


def _robot_bodies(m):
    root = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "base_node")
    out = set()
    for b in range(m.nbody):
        a = b
        while a > 0 and a != root:
            a = m.body_parentid[a]
        if a == root:
            out.add(b)
    return out


def _house_body(name):
    return name.startswith(("counter_", "cont_", "obj_")) or name == "person"


_FIELDS = ("geom_contype", "geom_conaffinity", "body_contype", "body_conaffinity")
_CACHE = {}


def _masks(m):
    """(robot bodies, the collision masks for robot-vs-house) - computed once per model."""
    if id(m) not in _CACHE:
        robot = _robot_bodies(m)
        gt, ga = np.zeros_like(m.geom_contype), np.zeros_like(m.geom_conaffinity)
        for g in range(m.ngeom):
            b = m.geom_bodyid[g]
            if b in robot:
                gt[g] = ROBOT
            elif _house_body(m.body(b).name) or (b == 0 and m.geom_size[g][2] > 0.1):   # world: the wall, not floor
                ga[g] = HOUSE
        bt, ba = np.zeros_like(m.body_contype), np.zeros_like(m.body_conaffinity)
        for g in range(m.ngeom):             # MuJoCo 3.x also filters by per-body masks, baked at compile time
            bt[m.geom_bodyid[g]] |= gt[g]
            ba[m.geom_bodyid[g]] |= ga[g]
        _CACHE[id(m)] = (robot, dict(zip(_FIELDS, (gt, ga, bt, ba))), mujoco.MjData(m))
    return _CACHE[id(m)]


class _Contacts:
    """with _Contacts(m): robot-vs-house contacts on; the model's own (all off) masks come back afterwards."""

    def __init__(self, m):
        self.m = m

    def __enter__(self):
        robot, masks, d = _masks(self.m)
        self.saved = {f: getattr(self.m, f).copy() for f in _FIELDS}
        for f, v in masks.items():
            getattr(self.m, f)[:] = v
        return robot, d

    def __exit__(self, *exc):
        for f in _FIELDS:
            getattr(self.m, f)[:] = self.saved[f]


def pose_hits(m, joints, obj_pos, ignore=(), tol=0.002):
    """One pose: {joint: value} + where the objects are ({name: xyz, or None if held/away}) ->
    [(robot body, house body, depth m)] for everything the robot is inside by more than tol."""
    with _Contacts(m) as (robot, d):
        for n, v in joints.items():
            j = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, n)
            if j >= 0:
                d.qpos[m.jnt_qposadr[j]] = v
        for o, p in obj_pos.items():
            b = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "obj_" + o.replace(" ", "_"))
            if b >= 0:
                d.mocap_pos[m.body_mocapid[b]] = p if p is not None else (0.0, 0.0, -5.0)
        mujoco.mj_forward(m, d)
        out = []
        for j in range(d.ncon):
            c = d.contact[j]
            b1, b2 = m.geom_bodyid[c.geom1], m.geom_bodyid[c.geom2]
            rb, hb = (b1, b2) if b1 in robot else (b2, b1)
            name = m.body(hb).name or "wall"
            if rb in robot and hb not in robot and -c.dist > tol and name not in ignore:
                out.append((m.body(rb).name, name, round(-c.dist, 3)))
        return out


def sweep(m, body, stride=2, tol=0.002):
    with _Contacts(m) as (robot, _):
        return _replay(m, body, robot, stride, tol)


def _replay(m, body, robot, stride, tol):
    d = mujoco.MjData(m)
    for o, p in getattr(body, "pos0", {}).items():             # start from where the objects really were
        bid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "obj_" + o.replace(" ", "_"))
        if bid >= 0:
            d.mocap_pos[m.body_mocapid[bid]] = p
    starts = getattr(body, "step_at", [])
    # which frame is playing on each on_frame call (motor.play: steps per frame + 1 settle call)
    frame_of = []
    for i, (sec, _, _) in enumerate(body.frames):
        frame_of += [i] * (max(1, int(sec / 0.02)) + 1)
    hits, seen, call = [], set(), [0]
    held_at = []                  # per frame: objects in a hand while that frame plays (from attach/detach events)
    held = set()
    for sec, _, ev in body.frames:
        held_at.append(set(held))
        if ev and ev[0] == "attach" and len(ev) > 2 and ev[2]:
            held.add("obj_" + str(ev[2]))
        elif ev and ev[0] in ("detach", "give", "fly"):
            held.discard("obj_" + str(ev[1]).replace(" ", "_"))

    def step_for(frame):
        cur = None
        for f0, k, a in starts:
            if f0 <= frame:
                cur = (k, a)
        return cur

    def check():
        c = call[0]
        call[0] += 1
        if c % stride or c >= len(frame_of):
            return
        frame = frame_of[c]
        st = step_for(frame)
        target = "obj_" + str(st[1].get("obj", "")).replace(" ", "_") if st else ""
        for j in range(d.ncon):
            g1, g2 = d.contact[j].geom1, d.contact[j].geom2
            b1, b2 = m.geom_bodyid[g1], m.geom_bodyid[g2]
            rb, hb = (b1, b2) if b1 in robot else (b2, b1)
            if rb not in robot or hb in robot or d.contact[j].dist > 0:
                continue
            rn, hn = m.body(rb).name, m.body(hb).name or "wall"
            if hn == target or hn in held_at[frame] or -d.contact[j].dist <= tol:
                continue                   # what this step handles, what is in a hand, and fingertips resting (<=tol)
            key = (st[0] if st else -1, rn, hn)
            if key not in seen:
                seen.add(key)
                hits.append({"step": (st[0] + 1) if st else 0, "do": st[1] if st else None,
                             "t": round(c * 0.02, 1), "robot": rn, "hit": hn, "depth": round(-d.contact[j].dist, 3)})

    motor.play(m, d, body.frames, check)
    return hits
