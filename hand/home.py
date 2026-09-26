"""A small simulated home for the full InMoov on its wheeled base: kitchen, laundry, living room, and you.

    body = HomeBody(model); body.run(program)       # same action language as hand/motor.py, plus:
      {"do": "go", "to": "kitchen|laundry|living room|you"}
      {"do": "put_in", "obj": "cup", "into": "rack"}            containers: sink, rack, washer, basket
      {"do": "put_on", "obj": "apple", "room": "living room"}   free spot on that room's counter/table
      {"do": "wipe", "room": "kitchen"}                          takes the sponge, wipes, puts it back
      {"do": "give", "obj": "apple"}                              drives to you and hands it over
    Picking something in another room drives there first. Arms go to rest before the base moves; anything held
    rides along in the hand.

The robot faces its local -y. A room's counter is 0.9 m wide at 0.98 m, 0.34 m in front of where the robot parks;
positions below are in that parked frame (x = robot's left, y = forward is negative). The base drives through the
hall (0, 0) between rooms at 0.6 m/s and turns at 1.5 rad/s. This is the wheeled base from the build plan - legs
come later, so it drives rather than walks.
"""
import re

import numpy as np

from . import motor, reach

TABLE_Z = 0.98                 # bar-height counters: at 0.88 m the arms only reached a 6 cm deep strip
ROOMS = {  # parked base pose (x, y, yaw): yaw turns the robot's front (-y) to face the counter
    "kitchen": (1.6, 0.0, np.pi / 2),
    "laundry": (-1.6, 0.0, -np.pi / 2),
    "living room": (0.0, 1.6, np.pi),
    "you": (0.0, -0.6, 0.0),
}
PERSON = (0.0, -1.35)                         # where you stand
CONTAINERS = {  # room, local (x, y), half size (x, y, z) of the box, colour
    "sink": ("kitchen", (0.26, -0.34), (0.09, 0.08, 0.04), "0.6 0.65 0.7 1"),
    "rack": ("kitchen", (-0.30, -0.34), (0.09, 0.08, 0.02), "0.8 0.8 0.85 1"),
    "washer": ("laundry", (-0.28, -0.34), (0.1, 0.09, 0.05), "0.95 0.95 0.97 1"),
    "basket": ("laundry", (0.28, -0.34), (0.09, 0.08, 0.04), "0.6 0.45 0.3 1"),
}
OBJECTS = {  # room, local (x, y), geom type, size, rgba, half height, kind
    "cup": ("kitchen", (-0.14, -0.26), "cylinder", "0.025 0.04", "0.95 0.95 0.95 1", 0.04, "dish"),
    "plate": ("kitchen", (-0.04, -0.32), "cylinder", "0.05 0.008", "0.9 0.9 0.8 1", 0.008, "dish"),
    "apple": ("kitchen", (0.10, -0.26), "sphere", "0.03", "0.8 0.1 0.1 1", 0.03, "food"),
    "sponge": ("kitchen", (0.06, -0.33), "box", "0.03 0.02 0.012", "0.95 0.9 0.2 1", 0.012, "tool"),
    "red shirt": ("laundry", (-0.10, -0.27), "box", "0.05 0.04 0.012", "0.85 0.2 0.2 1", 0.012, "dirty clothes"),
    "white shirt": ("laundry", (0.0, -0.34), "box", "0.05 0.04 0.012", "0.97 0.97 0.97 1", 0.012, "dirty clothes"),
    "towel": ("laundry", (0.11, -0.27), "box", "0.045 0.035 0.015", "0.3 0.6 0.9 1", 0.015, "clean clothes"),
    "ball": ("living room", (-0.30, -0.30), "sphere", "0.03", "0.9 0.5 0.1 1", 0.03, "toy"),
    "book": ("living room", (-0.10, -0.33), "box", "0.04 0.03 0.012", "0.2 0.3 0.6 1", 0.012, "book"),
    "remote": ("living room", (0.10, -0.30), "box", "0.02 0.05 0.01", "0.1 0.1 0.1 1", 0.01, "remote"),
    "soda can": ("living room", (0.30, -0.33), "cylinder", "0.028 0.045", "0.2 0.7 0.3 1", 0.045, "trash"),
}
FREE_SPOTS = [(-0.12, -0.27), (0.12, -0.27), (0.0, -0.26), (-0.06, -0.34), (0.06, -0.34), (-0.18, -0.33),
              (0.18, -0.33), (-0.34, -0.27), (0.34, -0.27)]
DRIVE_V, TURN_V = 0.6, 1.5


def to_world(room_or_pose, local):
    x, y, yaw = ROOMS[room_or_pose] if isinstance(room_or_pose, str) else room_or_pose
    c, s = np.cos(yaw), np.sin(yaw)
    return np.array([x + c * local[0] - s * local[1], y + s * local[0] + c * local[1]])


def to_local(pose, xy):
    x, y, yaw = pose
    c, s = np.cos(yaw), np.sin(yaw)
    dx, dy = xy[0] - x, xy[1] - y
    return np.array([c * dx + s * dy, -s * dx + c * dy])


def mocap_name(o):
    return "obj_" + o.replace(" ", "_")


def scene_xml():
    out = ['<light pos="0 0 3" dir="0 0 -1" diffuse="0.6 0.6 0.6" castshadow="false"/>',
           '<geom type="box" size="2.6 2.4 0.01" pos="0 0.3 -0.01" rgba="0.55 0.5 0.45 1"/>']
    out.append('<geom type="box" size="2.6 0.02 0.4" pos="0 2.7 0.4" rgba="0.8 0.8 0.78 1"/>')
    for room in ("kitchen", "laundry", "living room"):
        c = to_world(room, (0, -0.33))
        yaw = ROOMS[room][2]
        colour = {"kitchen": "0.45 0.35 0.28 1", "laundry": "0.5 0.55 0.6 1", "living room": "0.4 0.3 0.25 1"}[room]
        out.append(f'<body name="counter_{room.replace(" ", "_")}" pos="{c[0]:.3f} {c[1]:.3f} {TABLE_Z / 2}" '
                   f'euler="0 0 {np.degrees(yaw):.1f}"><geom type="box" size="0.46 0.14 {TABLE_Z / 2}" '
                   f'rgba="{colour}"/></body>')
    for name, (room, loc, half, rgba) in CONTAINERS.items():
        c = to_world(room, loc)
        yaw = np.degrees(ROOMS[room][2])
        out.append(f'<body name="cont_{name}" pos="{c[0]:.3f} {c[1]:.3f} {TABLE_Z + half[2]:.3f}" euler="0 0 {yaw:.1f}">'
                   f'<geom type="box" size="{half[0]} {half[1]} {half[2]}" rgba="{rgba}"/></body>')
    out.append(f'<body name="person" pos="{PERSON[0]} {PERSON[1]} 0.85"><geom type="capsule" size="0.16 0.6" '
               f'rgba="0.55 0.6 0.75 1"/><geom type="sphere" size="0.11" pos="0 0 0.78" rgba="0.85 0.72 0.6 1"/></body>')
    for o, (room, loc, typ, size, rgba, h, kind) in OBJECTS.items():
        c = to_world(room, loc)
        out.append(f'<body name="{mocap_name(o)}" mocap="true" pos="{c[0]:.3f} {c[1]:.3f} {TABLE_Z + h:.3f}">'
                   f'<geom type="{typ}" size="{size}" rgba="{rgba}"/></body>')
    return "".join(out)


def describe_world(body):
    lines = []
    for o in OBJECTS:
        w = body.where[o]
        lines.append(f"- {o} ({OBJECTS[o][6]}): " + {"in": f"in the {w[1]}", "on": f"on the {w[1]} counter",
                                                      "held": f"in the robot's {w[1]} hand",
                                                      "given": "with the person"}[w[0]])
    seen = [f"- {r} surface: {what}" for r, what in body.messes.items()] or ["- nothing dirty in view"]
    return ("Rooms: kitchen (sink, rack), laundry (washer, basket), living room (table), and the person.\n"
            f"The robot is at: {body.room}.\nObjects:\n" + "\n".join(lines) +
            "\nWhat the camera sees on the surfaces:\n" + "\n".join(seen))


class HomeBody(motor.Body):
    """motor.Body on a wheeled base in the home. World coordinates everywhere; IK knows where the base is."""

    def __init__(self, m, messes=None):
        super().__init__(m)
        # perceived facts, what the camera would report ({room: "sticky puddle"}): the planner can only reason about
        # dirt it is told about (results/house.md: without this, "I spilled something" was a guess)
        self.messes = dict(messes or {})
        self.base = (0.0, 0.0, 0.0)
        self.room = "hall"
        self.pos, self.where = {}, {}
        for o, (room, loc, *_rest) in OBJECTS.items():
            xy = to_world(room, loc)
            self.pos[o] = np.array([xy[0], xy[1], TABLE_Z + OBJECTS[o][5]])
            self.where[o] = ("on", room)
        self.filled = {k: 0 for k in CONTAINERS}
        self.wiped = set()

    # ---- geometry overrides
    def _pose(self):
        return {**super()._pose(), "base_x": self.base[0], "base_y": self.base[1], "base_yaw": self.base[2]}

    def _side_for(self, xyz, hand="auto"):
        if hand in ("right", "left"):
            return hand
        return "left" if to_local(self.base, xyz[:2])[0] > -0.02 else "right"

    def move(self, side, xyz, seconds=None, event=None, why=""):
        q, err = reach.solve(self.m, xyz, side=side, base=self.base)
        if q is None:
            self.problems.append(f"{why or 'move_hand'}: {side} hand cannot reach that from the {self.room} "
                                 f"({err * 100:.0f} cm short)")
            return False
        need = max(abs(q[n] - self.arm_q[side][n]) for n in q) / motor.ARM_SPEED
        self.arm_q[side] = q
        self.frames.append((max(seconds or 0.0, need, 0.3), self._pose(), event))
        return True

    def _local_xyz(self, local, z):
        xy = to_world(self.base, local)
        return np.array([xy[0], xy[1], z])

    # ---- moving around
    def go(self, room):
        room = re.sub(r"\s+(counter|table|area|room)$", "", room) if room not in ROOMS else room
        room = {"living": "living room", "lounge": "living room", "person": "you", "me": "you",
                "laundry room": "laundry"}.get(room, room)
        if room not in ROOMS:
            return self.problems.append(f"go: no place called '{room}' (kitchen, laundry, living room, you)")
        if room == self.room:
            return
        self.arm_q = {s: {n: 0.0 for n in q} for s, q in self.arm_q.items()}
        self.frames.append((0.6, self._pose(), None))          # arms in before driving
        target = ROOMS[room]
        for wp in ([(0.0, 0.0)] if self.room != "hall" else []) + [target[:2]]:
            dx, dy = wp[0] - self.base[0], wp[1] - self.base[1]
            dist = float(np.hypot(dx, dy))
            if dist < 1e-3:
                continue
            heading = float(np.arctan2(dx, -dy))                # yaw that points the robot's front (-y) along the path
            turn = abs(np.angle(np.exp(1j * (heading - self.base[2]))))
            self.base = (self.base[0], self.base[1], self.base[2] + np.angle(np.exp(1j * (heading - self.base[2]))))
            self.frames.append((max(turn / TURN_V, 0.2), self._pose(), None))
            self.base = (wp[0], wp[1], self.base[2])
            self.frames.append((dist / DRIVE_V, self._pose(), None))
        turn = np.angle(np.exp(1j * (target[2] - self.base[2])))
        self.base = (target[0], target[1], self.base[2] + turn)
        self.frames.append((max(abs(turn) / TURN_V, 0.2), self._pose(), None))
        self.room = room

    def _room_of(self, o):
        w = self.where[o]
        if w[0] == "on":
            return w[1]
        if w[0] == "in":
            return CONTAINERS[w[1]][0]
        return None

    def _mess_note(self, o):
        """Grasping a mess fails the way it would for real - nothing solid to close on. Say so, the way a failed
        grasp would, so the repair round knows what kind of thing it tried to pick."""
        for room, what in self.messes.items():
            if any(w and w in what for w in str(o).lower().split()):
                return f" - the {o} is part of the mess on the {room} surface, nothing solid to grasp"
        return ""

    # ---- skills (world coordinates)
    def pick(self, o, hand="auto"):
        if o not in self.pos:
            return self.problems.append(f"pick: there is no {o}" + self._mess_note(o))
        if self.where[o][0] == "held":
            return
        if self.where[o][0] == "given":
            return self.problems.append(f"pick: the {o} is with the person")
        room = self._room_of(o)
        if room != self.room:
            self.go(room)
        side = self._side_for(self.pos[o], hand)
        other = "left" if side == "right" else "right"
        if self.held[side] and not self.held[other]:
            side = other
        elif self.held[side]:
            self.put_on(self.held[side], self.room)
        p, h = self.pos[o], OBJECTS[o][5]
        top = p[2] + h
        if not self.move(side, (p[0], p[1], top + 0.12), why=f"pick {o}"):
            return
        self.move(side, (p[0], p[1], top + 0.04), 0.6)
        if self.where[o][0] == "in":
            self.filled[self.where[o][1]] -= 1
        self.held[side], self.where[o] = o, ("held", side)
        self.set_grip(side, 0.8, ("attach", side, mocap_name(o)[4:]))
        self.move(side, (p[0], p[1], top + 0.14), 0.6)

    def _holding(self, o):
        side = next((s for s, v in self.held.items() if v == o), None)
        if side is None:
            self.pick(o)
            side = next((s for s, v in self.held.items() if v == o), None)
        return side

    def _drop_at(self, o, xyz, where, side):
        h = OBJECTS[o][5]
        x, y, z = xyz
        if not self.move(side, (x, y, z + h + 0.14), why=f"put {o}"):
            return False
        self.move(side, (x, y, z + h + 0.04), 0.6)
        self.pos[o] = np.array([x, y, z + h])
        self.held[side], self.where[o] = None, where
        self.set_grip(side, 0.0, ("detach", mocap_name(o)[4:], (x, y, z + h)))
        self.move(side, (x, y, z + h + 0.16), 0.5)
        return True

    def put_in(self, o, into):
        if into not in CONTAINERS:
            return self.problems.append(f"put_in: no container '{into}' ({', '.join(CONTAINERS)})")
        if o not in self.pos:
            return self.problems.append(f"put_in: there is no {o}")
        side = self._holding(o)
        if side is None:
            return
        room, loc, half, _ = CONTAINERS[into]
        self.go(room)
        side = next((s for s, v in self.held.items() if v == o), side)
        n = self.filled[into]
        offs = [(0, 0), (-0.035, 0.03), (0.035, -0.03), (0.035, 0.03), (-0.035, -0.03)]
        dx, dy = offs[n % len(offs)]
        xy = to_world(room, (loc[0] + dx, loc[1] + dy))
        z = TABLE_Z + 2 * half[2] + 0.01 * (n // len(offs))
        want = self._side_for((xy[0], xy[1], z))
        if want != side and self.held[want] is None:
            self.pass_to(o, want)
            side = want
        if self._drop_at(o, (xy[0], xy[1], z), ("in", into), side):
            self.filled[into] += 1

    def put_on(self, o, room):
        room = {"living": "living room", "table": "living room", "counter": "kitchen"}.get(room, room)
        if room not in ROOMS or room == "you":
            return self.problems.append(f"put_on: no counter in '{room}'")
        side = self._holding(o)
        if side is None:
            return
        self.go(room)
        side = next((s for s, v in self.held.items() if v == o), side)
        for loc in FREE_SPOTS:
            xy = to_world(room, loc)
            clear_objs = all(np.linalg.norm(self.pos[k][:2] - xy) > 0.07 for k in self.pos if k != o and
                             self.where[k][0] != "held")
            clear_boxes = all(np.linalg.norm(to_world(r, c) - xy) > 0.13 for r, c, *_ in CONTAINERS.values() if r == room)
            if clear_objs and clear_boxes:
                break
        want = self._side_for((xy[0], xy[1], TABLE_Z))
        if want != side and self.held[want] is None:
            self.pass_to(o, want)
            side = want
        self._drop_at(o, (xy[0], xy[1], TABLE_Z), ("on", room), side)

    def give(self, o):
        side = self._holding(o)
        if side is None:
            return
        self.go("you")
        side = next((s for s, v in self.held.items() if v == o), side)
        target = self._local_xyz((-0.12 if side == "right" else 0.12, -0.5), 1.15)
        if self.move(side, target, 1.2, why="give"):
            self.held[side], self.where[o] = None, ("given",)
            self.pos[o] = np.array([PERSON[0] + (-0.1 if side == "right" else 0.1), PERSON[1] + 0.15, 1.1])
            self.set_grip(side, 0.0, ("give", mocap_name(o)[4:], tuple(self.pos[o])))
            self.said.append(f"here's the {o}")

    def pass_to(self, o, to):
        frm = next((s for s, v in self.held.items() if v == o), None)
        if frm is None or frm == to:
            return
        a = self._local_xyz((-0.03 if frm == "right" else 0.03, -0.36), 1.10)
        b = self._local_xyz((0.05 if to == "left" else -0.05, -0.36), 1.12)
        if self.move(frm, a, 1.0, why="pass") and self.move(to, b, 1.0, why="pass"):
            self.held[to], self.held[frm], self.where[o] = o, None, ("held", to)
            self.set_grip(to, 0.8, ("attach", to, mocap_name(o)[4:]), 0.4)
            self.set_grip(frm, 0.0, None, 0.4)

    def wipe(self, room):
        room = {"table": "living room", "counter": "kitchen", "living": "living room"}.get(room, room)
        if room not in ("kitchen", "laundry", "living room"):
            return self.problems.append(f"wipe: no counter in '{room}'")
        home = self.where["sponge"]
        side = self._holding("sponge")
        if side is None:
            return
        self.go(room)
        side = next((s for s, v in self.held.items() if v == "sponge"), side)
        xs = (-0.22, -0.06) if side == "right" else (0.06, 0.22)          # the middle 10 cm is out of reach
        for k, ly in enumerate((-0.26, -0.30, -0.34)):
            for lx in (xs if k % 2 == 0 else xs[::-1]):
                self.move(side, self._local_xyz((lx, ly), TABLE_Z + 0.05), 0.5, why="wipe")
        self.wiped.add(room)
        self.messes.pop(room, None)
        back = home[1] if home[0] == "on" else "kitchen"
        self.put_on("sponge", back)

    def toss(self, o, to=None, height=0.25):
        side = self._holding(o)
        if side is None:
            return
        # reuse the table-top toss in the robot's own frame: temporarily treat the parked frame as the origin
        release = self._local_xyz((-0.12 if side == "right" else 0.12, -0.36), 1.05)
        to = to if to in ("right", "left") else side
        catch = self._local_xyz((-0.12 if to == "right" else 0.12, -0.36), 1.05)
        if not self.move(side, release, 0.8, why="toss"):
            return
        vz = np.sqrt(2 * motor.G * float(np.clip(height, 0.05, 0.5)))
        tf = 2 * vz / motor.G
        v = ((catch[0] - release[0]) / tf, (catch[1] - release[1]) / tf, vz)
        self.held[side] = None
        q, _ = reach.solve(self.m, catch - [0, 0, 0.02], side=to, base=self.base)
        need = max(abs(q[n] - self.arm_q[to][n]) for n in q) / motor.ARM_SPEED if q else 1e9
        caught = q is not None and (need <= tf or to == side)
        if q:
            self.arm_q[to] = q
        self.frames.append((tf, self._pose(), ("fly", mocap_name(o)[4:], tuple(release), v, tf, to if caught else None)))
        if caught:
            self.held[to], self.where[o] = o, ("held", to)
            self.set_grip(to, 0.8, ("attach", to, mocap_name(o)[4:]), 0.15)
        else:
            self.problems.append(f"toss: missed the catch - the {o} fell")
            self.where[o] = ("on", self.room)
            self.pos[o] = np.array([catch[0], catch[1], TABLE_Z + OBJECTS[o][5]])

    def point(self, o):
        if o not in self.pos:
            return self.problems.append(f"point: no {o}")
        if self._room_of(o) and self._room_of(o) != self.room:
            self.go(self._room_of(o))
        super().point(o)

    def look(self, o):
        if o in self.pos:
            loc = to_local(self.base, self.pos[o][:2])
            turn = float(np.clip(-np.arctan2(loc[0], 0.5), -0.34, 0.34))
            self.frames.append((1.0, {**self._pose(), motor.TURN: turn}, None))

    def _hand_xyz(self, side):
        import mujoco
        d = mujoco.MjData(self.m)
        for n, v in {**self.arm_q[side], "base_x": self.base[0], "base_y": self.base[1],
                     "base_yaw": self.base[2]}.items():
            d.qpos[self.m.jnt_qposadr[self.m.joint(n).id]] = v
        mujoco.mj_forward(self.m, d)
        return d.xpos[self.m.body(reach.palm(side)).id].copy()

    def grip_cmd(self, hand, amount):
        super().grip_cmd(hand, amount)
        for side, o in self.held.items():                     # keep the home's bookkeeping in step
            if o and self.where[o][0] != "held":
                if self.where[o][0] == "in":
                    self.filled[self.where[o][1]] -= 1
                self.where[o] = ("held", side)
        for o in OBJECTS:
            if self.where[o][0] == "held" and self.held.get(self.where[o][1]) != o:
                self.where[o] = ("on", self.room if self.room in ROOMS and self.room != "you" else "living room")

    def push(self, o, d):
        self.problems.append("push: not in the home yet (use put_on / put_in)")

    def run(self, program, finish=True):
        saved = motor.OBJ                     # motor.Body's generic actions look up object sizes here
        motor.OBJ = {o: (v[2], v[3], v[4], v[5]) for o, v in OBJECTS.items()}
        try:
            return self._run(program, finish)
        finally:
            motor.OBJ = saved

    def _run(self, program, finish=True):
        extra = {"go": lambda a: self.go(str(a.get("to", "")).lower()),
                 "put_in": lambda a: self.put_in(a.get("obj"), a.get("into")),
                 "put_on": lambda a: self.put_on(a.get("obj"), str(a.get("room", self.room)).lower()),
                 "wipe": lambda a: self.wipe(str(a.get("room", self.room)).lower())}
        rest = []
        for i, a in enumerate(program if isinstance(program, list) else []):
            do = str(a.get("do", "")).lower() if isinstance(a, dict) else ""
            if do in extra:
                n0 = len(self.problems)
                try:
                    extra[do](a)
                except Exception as e:
                    self.problems.append(f"{do}: {e}")
                for k in range(n0, len(self.problems)):
                    self.problems[k] = f"step {i + 1}: " + self.problems[k]
            else:
                super().run([a], finish=False)
        if finish:
            for s in ("right", "left"):
                if self.held[s]:
                    self.put_on(self.held[s], self.room if self.room in ("kitchen", "laundry", "living room")
                                else "living room")
            self.arm_q = {s: {n: 0.0 for n in q} for s, q in self.arm_q.items()}
            self.grip = {"right": 0.0, "left": 0.0}
            self.frames.append((1.0, self._pose(), None))
        return self
