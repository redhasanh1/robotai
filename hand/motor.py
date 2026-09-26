"""The full robot's motor programs: a small action language the AI writes, and a checker/executor that plays it on
the InMoov sim with both arms.

A program is a JSON list of actions. The robot's AI writes it for whatever it is asked ("juggle the ball"), the
executor checks every step against the body (IK reach, joint limits, is that hand holding it, can the catching
hand get there in time), and returns frames to play plus a list of problems. Problems go back to the AI, which
repairs its own program - thinking at inference time, no training.

Actions ("hand" is "right", "left" or "auto" = nearest):
  {"do": "pick", "obj": "ball", "hand": "auto"}
  {"do": "place", "obj": "ball", "at": "left|middle|right|front"}     or  "on": "can"
  {"do": "give", "obj": "ball"}                                       hand it to the person
  {"do": "pass", "obj": "ball", "to": "left"}                         hand-to-hand in the middle
  {"do": "toss", "obj": "ball", "to": "left", "height": 0.25}        throw up, the other (or same) hand catches
  {"do": "move_hand", "hand": "right", "to": [x, y, z], "seconds": 1}  or "to": "above can" / "middle" / "rest"
  {"do": "grip", "hand": "right", "amount": 0.8}                      closing within 6 cm of an object picks it up
  {"do": "joints", "set": {"right_elbow_x": 1.2}, "seconds": 1}
  {"do": "point", "obj": "can"} {"do": "push", "obj": "ball", "dir": "left|right|away|toward"}
  {"do": "look", "obj": "ball"} {"do": "gesture", "name": "wave|box|clap|nod|shake"} {"do": "say", "text": "..."}
Coordinates are metres: +x = robot's left, -y = away from the robot (in front), z up; table top z = 0.88.
"""
import numpy as np

from . import reach

TABLE_Z = 0.88
SPOTS = {"right": (-0.40, -0.30), "middle": (-0.25, -0.30), "left": (-0.10, -0.30), "front": (-0.25, -0.24),
         "far left": (0.25, -0.30), "far right": (-0.40, -0.30)}
START = {"ball": (-0.36, -0.35), "can": (-0.26, -0.35), "block": (-0.16, -0.35), "bar": (-0.08, -0.27)}
OBJ = {"ball": ("sphere", "0.03", "0.85 0.3 0.25 1", 0.03),
       "can": ("cylinder", "0.028 0.045", "0.3 0.55 0.9 1", 0.045),
       "block": ("box", "0.028 0.028 0.028", "0.95 0.8 0.2 1", 0.028),
       "bar": ("capsule", "0.013 0.06", "0.4 0.8 0.4 1", 0.013)}
FINGERS = ("index", "majeure", "ringFinger", "ringfinger", "pinky", "thumb")
HANDOVER = (-0.25, -0.52, 1.20)
MIDDLE = (0.0, -0.36, 1.10)          # where the two hands meet
NECK, TURN = "head_neck_001", "head_rothead"
G = 9.81
ARM_SPEED = 5.0                       # rad/s: InMoov shoulder/elbow servos, no faster
GESTURES = ("wave", "box", "clap", "nod", "shake")


def scene_xml():
    x0, y0 = SPOTS["middle"]
    body = (f'<body name="table" pos="{x0 + 0.12} {y0 - 0.03} {TABLE_Z / 2}"><geom type="box" '
            f'size="0.42 0.14 {TABLE_Z / 2}" rgba="0.45 0.35 0.28 1"/></body>')
    for name, (typ, size, rgba, h) in OBJ.items():
        x, y = START[name]
        euler = ' euler="0 90 0"' if name == "bar" else ""
        body += (f'<body name="obj_{name}" mocap="true" pos="{x} {y} {TABLE_Z + h}">'
                 f'<geom type="{typ}" size="{size}" rgba="{rgba}"{euler}/></body>')
    return body


def describe_world(pos, held):
    lines = [f"- {o}: at ({p[0]:.2f}, {p[1]:.2f}, {p[2]:.2f})" + (f", held in the {h} hand" if h else "")
             for o, p in pos.items() for h in [next((s for s, v in held.items() if v == o), None)]]
    return ("Objects:\n" + "\n".join(lines) + "\nRight hand reaches x -0.45..0.05, left hand x -0.05..0.45, "
            "y -0.24..-0.42 near the table, z 0.95..1.35. Hands meet at the middle (0, -0.36, 1.1).")


class Body:
    """Executes a program on the body model, collecting frames (seconds, {joint: angle}, event) and problems."""

    def __init__(self, m):
        self.m = m
        self.pos = {k: np.array([*START[k], TABLE_Z + OBJ[k][3]], float) for k in OBJ}
        self.held = {"right": None, "left": None}
        self.frames, self.problems, self.said = [], [], []
        self.arm_q = {"right": {n: 0.0 for n in reach.arm("right")}, "left": {n: 0.0 for n in reach.arm("left")}}
        self.grip = {"right": 0.0, "left": 0.0}

    # ---- helpers
    def _fingers(self, side, amount):
        out = {}
        for i in range(self.m.nu):
            n = self.m.actuator(i).name
            if n.startswith(f"{side}Hand_") and any(f in n for f in FINGERS):
                out[n] = float(self.m.actuator_ctrlrange[i, 1]) * amount
        return out

    def _pose(self):
        out = {}
        for s in ("right", "left"):
            out.update(self.arm_q[s])
            out.update(self._fingers(s, self.grip[s]))
        return out

    def _side_for(self, xyz, hand="auto"):
        if hand in ("right", "left"):
            return hand
        return "left" if xyz[0] > -0.02 else "right"

    def _hand_xyz(self, side):
        import mujoco
        d = mujoco.MjData(self.m)
        for n, v in self.arm_q[side].items():
            d.qpos[self.m.jnt_qposadr[self.m.joint(n).id]] = v
        mujoco.mj_forward(self.m, d)
        return d.xpos[self.m.body(reach.palm(side)).id].copy()

    def move(self, side, xyz, seconds=None, event=None, why=""):
        q, err = reach.solve(self.m, xyz, side=side)
        if q is None:
            self.problems.append(f"{why or 'move_hand'}: {side} hand cannot reach ({xyz[0]:.2f}, {xyz[1]:.2f}, "
                                 f"{xyz[2]:.2f}) - {err * 100:.0f} cm short")
            return False
        need = max(abs(q[n] - self.arm_q[side][n]) for n in q) / ARM_SPEED
        self.arm_q[side] = q
        self.frames.append((max(seconds or 0.0, need, 0.3), self._pose(), event))
        return True

    def set_grip(self, side, amount, event=None, seconds=0.5):
        self.grip[side] = float(np.clip(amount, 0, 1))
        self.frames.append((seconds, self._pose(), event))

    # ---- skills
    def pick(self, o, hand="auto"):
        if o not in self.pos:
            return self.problems.append(f"pick: there is no {o}")
        if o in self.held.values():
            return
        side = self._side_for(self.pos[o], hand)
        if self.held[side]:
            self.place(self.held[side], "front")
        p, h = self.pos[o], OBJ[o][3]
        top = p[2] + h
        if not self.move(side, (p[0], p[1], top + 0.12), why=f"pick {o}"):
            return
        self.move(side, (p[0], p[1], top + 0.04), 0.6)
        self.held[side] = o
        self.set_grip(side, 0.8, ("attach", side, o))
        self.move(side, (p[0], p[1], top + 0.14), 0.6)

    def place(self, o, at=None, on=None):
        side = next((s for s, v in self.held.items() if v == o), None)
        if side is None:
            self.pick(o)
            side = next((s for s, v in self.held.items() if v == o), None)
            if side is None:
                return
        if on:
            if on not in self.pos or on == o:
                return self.problems.append(f"place: can't put the {o} on '{on}'")
            x, y = self.pos[on][:2]
            z = self.pos[on][2] + OBJ[on][3] + OBJ[o][3]
        else:
            if at not in SPOTS:
                return self.problems.append(f"place: unknown spot '{at}' (use {', '.join(SPOTS)})")
            x, y = SPOTS[at]
            for k in OBJ:
                if k != o and np.linalg.norm(self.pos[k][:2] - (x, y)) < 0.06:
                    x += 0.07 if x < -0.2 else -0.07
            z = TABLE_Z + OBJ[o][3]
        side2 = self._side_for((x, y, z))
        if side2 != side:                             # other side of the table: hand it across first
            self.pass_to(o, side2)
            side = side2
        if not self.move(side, (x, y, z + OBJ[o][3] + 0.14), why=f"place {o}"):
            return
        self.move(side, (x, y, z + OBJ[o][3] + 0.04), 0.6)
        self.pos[o] = np.array([x, y, z])
        self.held[side] = None
        self.set_grip(side, 0.0, ("detach", o, (x, y, z)))
        self.move(side, (x, y, z + OBJ[o][3] + 0.16), 0.5)

    def give(self, o):
        side = next((s for s, v in self.held.items() if v == o), None)
        if side is None:
            self.pick(o)
            side = next((s for s, v in self.held.items() if v == o), None)
            if side is None:
                return
        target = HANDOVER if side == "right" else (-HANDOVER[0], HANDOVER[1], HANDOVER[2])
        if self.move(side, target, 1.2, why="give"):
            self.held[side] = None
            self.pos[o] = np.array([target[0], target[1] - 0.12, TABLE_Z + 0.35])
            self.set_grip(side, 0.0, ("give", o, tuple(self.pos[o])))
            self.said.append(f"here's the {o}")

    def pass_to(self, o, to):
        frm = next((s for s, v in self.held.items() if v == o), None)
        if frm is None:
            self.pick(o)
            frm = next((s for s, v in self.held.items() if v == o), None)
        if frm is None or frm == to:
            return
        a = (MIDDLE[0] - 0.03 if frm == "right" else MIDDLE[0] + 0.03, MIDDLE[1], MIDDLE[2])
        b = (MIDDLE[0] + 0.05 if to == "left" else MIDDLE[0] - 0.05, MIDDLE[1], MIDDLE[2] + 0.02)
        if self.move(frm, a, 1.0, why="pass") and self.move(to, b, 1.0, why="pass"):
            self.held[to], self.held[frm] = o, None
            self.set_grip(to, 0.8, ("attach", to, o), 0.4)
            self.set_grip(frm, 0.0, None, 0.4)

    def toss(self, o, to=None, height=0.25):
        frm = next((s for s, v in self.held.items() if v == o), None)
        if frm is None:
            self.pick(o)
            frm = next((s for s, v in self.held.items() if v == o), None)
            if frm is None:
                return
        to = to if to in ("right", "left") else frm
        height = float(np.clip(height, 0.05, 0.5))
        release = np.array((-0.12 if frm == "right" else 0.12, -0.36, 1.05))
        catch = np.array((-0.12 if to == "right" else 0.12, -0.36, 1.05))
        if to == frm:
            catch = release.copy()
        if not self.move(frm, release, 0.8, why="toss (wind up)"):
            return
        vz = np.sqrt(2 * G * height)
        t_flight = 2 * vz / G
        v = np.array([(catch[0] - release[0]) / t_flight, (catch[1] - release[1]) / t_flight, vz])
        # thrower lets go, catcher must be under the landing point before it arrives
        self.held[frm] = None
        self.grip[frm] = 0.0
        q_catch, err = reach.solve(self.m, catch - [0, 0, 0.02], side=to)
        if q_catch is None:
            self.problems.append(f"toss: the {to} hand can't reach the landing point - the {o} falls")
            self.frames.append((t_flight, self._pose(), ("fly", o, tuple(release), tuple(v), t_flight, None)))
            self.pos[o] = np.array([catch[0], catch[1], TABLE_Z + OBJ[o][3]])
            return
        need = max(abs(q_catch[n] - self.arm_q[to][n]) for n in q_catch) / ARM_SPEED
        caught = need <= t_flight or to == frm
        self.arm_q[to] = q_catch
        self.grip[to] = 0.0
        self.frames.append((t_flight, self._pose(), ("fly", o, tuple(release), tuple(v), t_flight,
                                                      to if caught else None)))
        if caught:
            self.held[to] = o
            self.set_grip(to, 0.8, ("attach", to, o), 0.15)
        else:
            self.problems.append(f"toss: the {to} hand needs {need:.2f} s to get there but the {o} lands in "
                                 f"{t_flight:.2f} s - throw higher")
            self.pos[o] = np.array([catch[0], catch[1], TABLE_Z + OBJ[o][3]])

    def move_hand(self, hand, to, seconds=1.0):
        side = hand if hand in ("right", "left") else "right"
        if isinstance(to, str):
            t = to.lower()
            if t == "rest":
                self.arm_q[side] = {n: 0.0 for n in self.arm_q[side]}
                self.frames.append((max(seconds, 0.6), self._pose(), None))
                return
            if t == "middle":
                to = MIDDLE
            elif t.startswith("above "):
                o = t.split()[-1]
                if o not in self.pos:
                    return self.problems.append(f"move_hand: no {o}")
                to = self.pos[o] + [0, 0, OBJ[o][3] + 0.12]
            else:
                return self.problems.append(f"move_hand: don't know where '{to}' is")
        try:
            xyz = [float(v) for v in to][:3]
        except (TypeError, ValueError):
            return self.problems.append(f"move_hand: bad target {to!r}")
        self.move(side, xyz, seconds)

    def grip_cmd(self, hand, amount):
        side = hand if hand in ("right", "left") else "right"
        near = None
        if amount > 0.5 and self.held[side] is None:
            p = self._hand_xyz(side)
            near = min(self.pos, key=lambda o: np.linalg.norm(self.pos[o] - p))
            gap = np.linalg.norm(self.pos[near] - p)
            if gap > 0.06 + OBJ[near][3] or near in self.held.values():
                self.problems.append(f"grip: nothing within reach of the {side} hand (closest: {near}, "
                                     f"{gap * 100:.0f} cm away - move_hand closer first, e.g. to the object's "
                                     f"height + 4 cm)")
                near = None
            if near:
                self.held[side] = near
        if amount <= 0.5 and self.held[side]:
            o = self.held[side]
            p = self._hand_xyz(side)
            self.held[side] = None
            self.pos[o] = np.array([p[0], p[1], max(TABLE_Z + OBJ[o][3], p[2] - 0.05)])
            return self.set_grip(side, amount, ("detach", o, tuple(self.pos[o])))
        self.set_grip(side, amount, ("attach", side, near) if near else None)

    def joints(self, values, seconds=1.0):
        pose = {}
        for n, v in (values or {}).items():
            try:
                jid = self.m.joint(n).id
            except KeyError:
                self.problems.append(f"joints: no joint called {n}")
                continue
            lo, hi = self.m.jnt_range[jid]
            v2 = float(np.clip(v, lo, hi))
            if abs(v2 - float(v)) > 1e-6:
                self.problems.append(f"joints: {n}={v} is outside its limits [{lo:.2f}, {hi:.2f}], clamped")
            pose[n] = v2
            for s in ("right", "left"):
                if n in self.arm_q[s]:
                    self.arm_q[s][n] = v2
        self.frames.append((max(seconds, 0.3), {**self._pose(), **pose}, None))

    def point(self, o):
        if o not in self.pos:
            return self.problems.append(f"point: no {o}")
        p = self.pos[o]
        side = self._side_for(p)
        self.grip[side] = 0.9
        if self.move(side, (p[0], p[1] + 0.05, 1.12), 1.0, why="point"):
            f = self._fingers(side, 0.9)
            f.update({n: 0.0 for n in f if "index" in n})
            self.frames.append((0.8, {**self._pose(), **f}, None))
        self.grip[side] = 0.0

    def push(self, o, d):
        if o not in self.pos:
            return self.problems.append(f"push: no {o}")
        step = np.array({"left": (0.12, 0, 0), "right": (-0.12, 0, 0), "away": (0, -0.04, 0),
                         "toward": (0, 0.07, 0)}.get(d, (0, 0.07, 0)))
        p = self.pos[o]
        side = self._side_for(p)
        back = p - step * np.array([0.5, 0.8, 0])
        z = TABLE_Z + 0.09
        if not self.move(side, back + [0, 0, 0.12], 1.0, why="push"):
            return
        self.move(side, (back[0], back[1], z), 0.6)
        new = p + step
        self.move(side, (new[0] - step[0] * 0.5, new[1] - step[1] * 0.8, z), 1.0, ("slide", o, tuple(new)))
        self.pos[o] = new
        self.move(side, (new[0], new[1], z + 0.1), 0.6)

    def gesture(self, g):
        base = self._pose()
        if g == "wave":
            up = {"right_shoulder_x": 2.1, "right_elbow_x": 0.9, "right_shoulder_z": 0.2}
            self.frames.append((1.0, {**base, **up}, None))
            for k in range(4):
                self.frames.append((0.35, {**base, **up, "right_shoulder_z": 0.8 if k % 2 == 0 else -0.35}, None))
        elif g == "box":
            guard = {"right_shoulder_x": 0.25, "right_elbow_x": 1.5, "left_shoulder_x": 0.25, "left_elbow_x": 1.5}
            self.frames.append((0.7, {**base, **guard}, None))
            for k in range(4):
                s = "right" if k % 2 == 0 else "left"
                self.frames.append((0.25, {**base, **guard, f"{s}_shoulder_x": 1.1, f"{s}_elbow_x": 0.1}, None))
                self.frames.append((0.3, {**base, **guard}, None))
        elif g == "clap":
            apart = {"right_shoulder_x": 1.2, "left_shoulder_x": 1.2, "right_elbow_x": 0.6, "left_elbow_x": 0.6,
                     "right_shoulder_z": 0.6, "left_shoulder_z": 0.6}
            for _ in range(3):
                self.frames.append((0.35, {**base, **apart}, None))
                self.frames.append((0.2, {**base, **apart, "right_shoulder_z": -0.3, "left_shoulder_z": -0.3}, None))
        elif g in ("nod", "shake"):
            j = NECK if g == "nod" else TURN
            for k in range(4):
                self.frames.append((0.3, {**base, j: 0.3 if k % 2 == 0 else -0.3}, None))
            self.frames.append((0.3, {**base, j: 0.0}, None))
        else:
            self.problems.append(f"gesture: unknown '{g}' (use {', '.join(GESTURES)})")
        # arms return to where they were
        self.frames.append((0.6, self._pose(), None))

    def look(self, o):
        if o in self.pos:
            turn = float(np.clip(-np.arctan2(self.pos[o][0], 0.5), -0.34, 0.34))
            self.frames.append((1.0, {**self._pose(), TURN: turn}, None))

    # ---- program
    def run(self, program, finish=True):
        for i, a in enumerate(program if isinstance(program, list) else []):
            if not isinstance(a, dict) or "do" not in a:
                self.problems.append(f"step {i + 1}: not an action: {a!r}")
                continue
            do = str(a["do"]).lower()
            n0 = len(self.problems)
            try:
                if do == "pick":
                    self.pick(a.get("obj"), a.get("hand", "auto"))
                elif do == "place":
                    self.place(a.get("obj"), a.get("at"), a.get("on"))
                elif do == "stack":
                    self.place(a.get("obj"), on=a.get("on"))
                elif do == "give":
                    self.give(a.get("obj"))
                elif do == "pass":
                    self.pass_to(a.get("obj"), a.get("to", "left"))
                elif do == "toss":
                    self.toss(a.get("obj"), a.get("to"), a.get("height", 0.25))
                elif do == "move_hand":
                    self.move_hand(a.get("hand", "right"), a.get("to"), a.get("seconds", 1.0))
                elif do == "grip":
                    self.grip_cmd(a.get("hand", "right"), float(a.get("amount", 0.8)))
                elif do == "joints":
                    self.joints(a.get("set"), a.get("seconds", 1.0))
                elif do == "point":
                    self.point(a.get("obj"))
                elif do == "push":
                    self.push(a.get("obj"), a.get("dir", "toward"))
                elif do == "look":
                    self.look(a.get("obj"))
                elif do in GESTURES:
                    self.gesture(do)
                elif do == "gesture":
                    self.gesture(a.get("name"))
                elif do == "say":
                    self.said.append(str(a.get("text", "")))
                elif do == "wait":
                    self.frames.append((float(np.clip(a.get("seconds", 0.5), 0, 5)), self._pose(), None))
                elif do in ("terminate", "end", "done", "stop", "finish"):
                    pass            # models like to close programs with an end marker - harmless, not a problem
                else:
                    self.problems.append(f"step {i + 1}: unknown action '{do}'")
            except Exception as e:           # a malformed step must not crash the robot
                self.problems.append(f"step {i + 1} ({do}): {e}")
            for k in range(n0, len(self.problems)):
                if not self.problems[k].startswith("step"):
                    self.problems[k] = f"step {i + 1}: " + self.problems[k]
        if finish:
            for s in ("right", "left"):
                if self.held[s]:
                    self.place(self.held[s], "front" if s == "right" else "far left")
            self.arm_q = {s: {n: 0.0 for n in q} for s, q in self.arm_q.items()}
            self.grip = {"right": 0.0, "left": 0.0}
            self.frames.append((1.0, self._pose(), None))
        return self


def play(m, d, frames, on_frame):
    """Kinematic playback with object events (attach/detach/give/slide/fly)."""
    import mujoco
    names = {m.actuator(i).name for i in range(m.nu)}
    adr = {n: m.jnt_qposadr[m.actuator_trnid[m.actuator(n).id, 0]] for n in names}
    for _, goal, _ in frames:                     # un-motored joints driven directly (the wheeled base)
        for k in goal:
            if k not in adr:
                try:
                    adr[k] = m.jnt_qposadr[m.joint(k).id]
                except KeyError:
                    pass
    names = set(adr)
    cur = {n: float(d.qpos[adr[n]]) for n in names}
    palms = {s: m.body(reach.palm(s)).id for s in ("right", "left")}
    held = {"right": None, "left": None}
    off = {}
    moc = lambda o: m.body(f"obj_{o}").mocapid[0]
    for seconds, goal, ev in frames:
        start = dict(cur)
        target = {**cur, **{k: v for k, v in goal.items() if k in cur}}
        steps = max(1, int(seconds / 0.02))
        slide0 = d.mocap_pos[moc(ev[1])].copy() if ev and ev[0] == "slide" else None
        if ev and ev[0] == "fly":
            for s in held:
                if held[s] == ev[1]:
                    held[s] = None
        for k in range(1, steps + 1):
            a = k / steps
            a = a * a * (3 - 2 * a)
            for n in cur:
                cur[n] = start[n] + (target[n] - start[n]) * a
                d.qpos[adr[n]] = cur[n]
            mujoco.mj_forward(m, d)
            for s, o in held.items():
                if o:
                    d.mocap_pos[moc(o)] = d.xpos[palms[s]] + off[o]
            if slide0 is not None:
                d.mocap_pos[moc(ev[1])] = slide0 + (np.array(ev[2]) - slide0) * a
            if ev and ev[0] == "fly":
                t = k / steps * ev[4]
                p0, v = np.array(ev[2]), np.array(ev[3])
                p = p0 + v * t + np.array([0, 0, -0.5 * G * t * t])
                if ev[5] is None:
                    p[2] = max(p[2], TABLE_Z + OBJ[ev[1]][3]) if abs(p[0]) < 0.6 else p[2]
                d.mocap_pos[moc(ev[1])] = p
            on_frame()
        if ev and ev[0] == "attach" and ev[2]:
            held[ev[1]] = ev[2]
            off[ev[2]] = d.mocap_pos[moc(ev[2])] - d.xpos[palms[ev[1]]]
        elif ev and ev[0] in ("detach", "give"):
            for s in held:
                if held[s] == ev[1]:
                    held[s] = None
            d.mocap_pos[moc(ev[1])] = ev[2]
        elif ev and ev[0] == "fly" and ev[5] is None:
            d.mocap_pos[moc(ev[1])] = (ev[2][0] + ev[3][0] * ev[4], ev[2][1] + ev[3][1] * ev[4], TABLE_Z + OBJ[ev[1]][3])
        elif ev and ev[0] == "clean":                  # a wiped stain's decal goes away (hand/perceive.py)
            g = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, ev[1])
            if g >= 0:
                m.geom_pos[g][2] = -1.0
        mujoco.mj_forward(m, d)
        on_frame()
