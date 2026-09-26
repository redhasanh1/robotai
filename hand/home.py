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

import mujoco
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
# where a spill lands on each counter: inside the strip the sponge hand sweeps (it reaches x 0.06..0.22, y -0.26..-0.34
# - the back of the counter is 13-29 cm out of reach) and clear of that room's objects and containers
STAIN_SPOTS = {"kitchen": (0.13, -0.33), "laundry": (0.13, -0.34), "living room": (0.18, -0.30)}
STAIN_R = 0.03
SPONGE_HALF = 0.03                             # half the sponge's length: how wide a stroke cleans
RAISES = (0.0, 0.01, 0.02, 0.03, 0.04, 0.06, 0.08, 0.10)    # m: how far a hand may lift to clear what it would hit
PATH_SAMPLES = (0.12, 0.25, 0.37, 0.5, 0.62, 0.75, 0.87)    # where along a move the path is checked
CARRY_AT = {"right": (-0.16, -0.08, TABLE_Z + 0.12), "left": (0.16, -0.08, TABLE_Z + 0.12)}   # robot frame
_CARRY = {}
CLEARANCE = 0.005                              # m: the planner keeps the arm this far from things (the replay checks contact)
FLAT_H = 0.035                                 # m: thinner than this and the hand can't get round it on a counter
FIST_H = 0.035                                 # m: grasp point of a fist above what its knuckles rest on
COUNTER_EDGE = -0.19                           # room-local y of the counter top's front edge
PRESHAPE = 0.6                                 # half-curled hand while reaching in (grip 0 = flat open)
SIGMAS = 2.0                                   # margin around a seen object = this many camera sigmas
AUTO_CLEAR = True                              # move a blocking object aside before a grasp (tools/clutter.py ablates it)
LOOK_H = 0.7                                   # counter camera height above the counter top


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


def _seg_dist(p, a, b):
    t = np.clip(np.dot(p - a, b - a) / max(np.dot(b - a, b - a), 1e-9), 0.0, 1.0)
    return float(np.linalg.norm(p - (a + t * (b - a))))


def scene_xml():
    out = ['<light pos="0 0 3" dir="0 0 -1" diffuse="0.6 0.6 0.6" castshadow="false"/>',
           '<geom type="box" size="2.6 2.4 0.01" pos="0 0.3 -0.01" rgba="0.55 0.5 0.45 1"/>']
    out.append('<geom type="box" size="2.6 0.02 0.4" pos="0 2.7 0.4" rgba="0.8 0.8 0.78 1"/>')
    for room in ("kitchen", "laundry", "living room"):
        c = to_world(room, (0, -0.33))
        yaw = ROOMS[room][2]
        colour = {"kitchen": "0.45 0.35 0.28 1", "laundry": "0.5 0.55 0.6 1", "living room": "0.4 0.3 0.25 1"}[room]
        # a real counter, not a solid block: 4 cm top, cabinet set back 2 cm, and a kick space under it (13 cm high,
        # 11 cm deep - a little deeper than the usual 7.5 cm) where the wheeled base tucks in, like feet at a counter.
        # Body frame +y faces the robot; the top's front edge is at +0.14.
        top_h, kick_h = 0.02, 0.065
        cab_h = (TABLE_Z - 2 * top_h - 2 * kick_h) / 2
        out.append(f'<body name="counter_{room.replace(" ", "_")}" pos="{c[0]:.3f} {c[1]:.3f} 0" euler="0 0 {yaw:.4f}">'
                   f'<geom type="box" size="0.46 0.14 {top_h}" pos="0 0 {TABLE_Z - top_h:.3f}" rgba="{colour}"/>'
                   f'<geom type="box" size="0.45 0.13 {cab_h:.3f}" pos="0 -0.01 {2 * kick_h + cab_h:.3f}" '
                   f'rgba="{colour}"/>'
                   f'<geom type="box" size="0.45 0.085 {kick_h}" pos="0 -0.055 {kick_h}" rgba="0.2 0.18 0.16 1"/>'
                   f'</body>')
        # a stain decal (hidden under the floor until perceive.set_messes shows it) and a camera looking straight down
        # at the counter: the robot learns about messes from pixels, not from being told (hand/perceive.py)
        s = to_world(room, STAIN_SPOTS[room])
        tag = room.replace(" ", "_")
        out.append(f'<geom name="mess_{tag}" type="cylinder" size="{STAIN_R} 0.0015" pos="{s[0]:.3f} {s[1]:.3f} -1" '
                   f'rgba="0.3 0.18 0.05 1" contype="0" conaffinity="0"/>')
        out.append(f'<camera name="look_{tag}" pos="{c[0]:.3f} {c[1]:.3f} {TABLE_Z + LOOK_H:.3f}" fovy="60" euler="0 0 {yaw:.4f}"/>')
    for name, (room, loc, half, rgba) in CONTAINERS.items():
        c = to_world(room, loc)
        yaw = ROOMS[room][2]                    # radians: the InMoov model compiles with angle="radian"
        out.append(f'<body name="cont_{name}" pos="{c[0]:.3f} {c[1]:.3f} {TABLE_Z + half[2]:.3f}" euler="0 0 {yaw:.4f}">'
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
        self.grasp_dir = {}                   # object -> (approach, dz) it is held with
        self.grip_at = {}                     # object -> where to grasp it, if not its centre (a slid-out overhang)
        self.grasp_off = {}                   # held object -> (centre-to-grasp offset, base yaw when picked)
        for s in ("right", "left"):
            self.arm_q[s][reach.wrist_flex(s)] = 0.0

    # ---- geometry overrides
    def _pose(self):
        return {**super()._pose(), "base_x": self.base[0], "base_y": self.base[1], "base_yaw": self.base[2]}

    def _side_for(self, xyz, hand="auto"):
        if hand in ("right", "left"):
            return hand
        return "left" if to_local(self.base, xyz[:2])[0] > -0.02 else "right"

    def move(self, side, xyz, seconds=None, event=None, why="", grasp=None):
        """IK to xyz, then make sure the arm isn't inside anything (hand/collide.py): raise the hand 1 cm at a time
        until it is clear. Grasping (grasp=obj): the counter can be cleared by raising, but another object in the
        way can't - the hand would miss what it's reaching for - so that is reported by name."""
        r = self._solve_clear(side, xyz, grasp)
        q, dz = (self._full(side, r["q"]) if r["q"] is not None else None), r["dz"]
        if r["status"] == "unreachable":
            self.problems.append(f"{why or 'move_hand'}: {side} hand cannot reach that from the {self.room} "
                                 f"({r['err'] * 100:.0f} cm short)")
            return False
        if r["status"] == "in_way":
            self.problems.append(f"{why or 'pick ' + grasp}: the {r['in_way'][0][1][4:].replace('_', ' ')} is in the "
                                 f"way of the {grasp}")
        elif r["status"] == "blocked":
            thing = r["hits"][0][1].replace("counter_", "").replace("cont_", "").replace("_", " ")
            self.problems.append(f"{why or 'move_hand'}: the {side} arm would hit the {thing}")
        self._detour(side, q, grasp, np.asarray(xyz) + (0, 0, dz))
        need = max(abs(q[n] - self.arm_q[side].get(n, 0.0)) for n in q) / motor.ARM_SPEED
        self.arm_q[side] = q
        self.frames.append((max(seconds or 0.0, need, 0.3), self._pose(), event))
        return True

    def _solve_clear(self, side, xyz, grasp=None):
        """IK to xyz, lifted 1 cm at a time until the arm is clear of the house. Pure - nothing is committed, so the
        same answer serves move() and the look-ahead in _blockers(). status: ok / unreachable / in_way / blocked."""
        q, dz, hits = None, 0.0, []
        for dz in RAISES:
            q2, err = reach.solve(self.m, np.asarray(xyz) + (0, 0, dz), side=side, base=self.base)
            if q2 is None:
                if q is None:
                    return {"status": "unreachable", "err": err, "q": None, "dz": 0.0, "hits": [], "in_way": []}
                break
            q, hits = q2, self._hits(side, q2, grasp)
            in_way = [h for h in hits if h[1].startswith("obj_")]
            if grasp and in_way:
                return {"status": "in_way", "q": q, "dz": dz, "hits": hits, "in_way": in_way}
            if not hits:
                return {"status": "ok", "q": q, "dz": dz, "hits": [], "in_way": []}
        return {"status": "blocked", "q": q, "dz": dz, "hits": hits, "in_way": []}

    def _path_hits(self, side, q0, q1, grasp=None, exact=()):
        """Hits partway along the joint-space path (playback interpolates joints; the ends alone can be clear)."""
        for a in PATH_SAMPLES:
            hits = self._hits(side, {n: q0.get(n, 0.0) + a * (q1[n] - q0.get(n, 0.0)) for n in q1}, grasp, exact)
            if hits:
                return hits
        return []

    def _detour(self, side, q, grasp=None, xyz=None, extra=()):
        """If going straight to q would sweep the arm through something, go by one or two waypoints instead: lift
        straight up from where the hand is, straight above the target (then come down onto it), or the READY pose
        (hand pulled in above the counter's front edge). The first route whose every leg is clear wins."""
        if not self._path_hits(side, self.arm_q[side], q, grasp):
            return
        points = []
        if xyz is not None:
            points += [np.asarray(xyz) + (0, 0, h) for h in (0.15, 0.25)]
        here = self._hand_xyz(side)
        points += [here + (0, 0, h) for h in (0.12, 0.22)]
        points += [self._local_xyz((0.18 if side == "left" else -0.18, -0.12), TABLE_Z + z) for z in (0.22, 0.32)]
        vias = [self._full(side, v) for v in extra if v is not None and not self._hits(side, self._full(side, v), grasp)]
        for p in points:
            v, _ = reach.solve(self.m, p, side=side, base=self.base)
            v = self._full(side, v) if v is not None else None
            if v is not None and not self._hits(side, v, grasp):
                vias.append(v)
        routes = [[v] for v in vias] + [[a, b] for a in vias for b in vias if a is not b]
        for route in routes:
            legs = [self.arm_q[side]] + route + [q]
            if not any(self._path_hits(side, a, b, grasp) for a, b in zip(legs, legs[1:])):
                for v in route:
                    need = max(abs(v[n] - self.arm_q[side].get(n, 0.0)) for n in v) / motor.ARM_SPEED
                    self.arm_q[side] = v
                    self.frames.append((max(need, 0.3), self._pose(), None))
                return
        thing = self._path_hits(side, self.arm_q[side], q, grasp)[0][1]
        self.problems.append(f"the {side} arm would sweep through the "
                             f"{thing.replace('counter_', '').replace('cont_', '').replace('_', ' ')} on the way")

    def _carry_q(self, side):
        """CARRY pose: forearm bent, hand in front of the chest above counter height. Hanging arms put the fingertips
        1 cm from the counter's front, so every reach from there swept through it; from here reaches start above it.
        Joint angles only depend on the robot's own frame, so solve once."""
        if side not in _CARRY:
            q, _ = reach.solve(self.m, to_world((0, 0, 0), CARRY_AT[side])[:2].tolist() + [CARRY_AT[side][2]],
                               side=side, base=(0.0, 0.0, 0.0))
            _CARRY[side] = q or {n: 0.0 for n in self.arm_q[side]}
        return dict(_CARRY[side])

    def _to_rest(self, seconds):
        """Both arms to the carry pose (a detour first if the straight way would go through something)."""
        for s in ("right", "left"):
            q = self._full(s, self._carry_q(s))
            if any(abs(q[n] - self.arm_q[s].get(n, 0.0)) > 1e-6 for n in q):
                self._detour(s, q)
                self.arm_q[s] = q
        self.frames.append((seconds, self._pose(), None))

    def _hits(self, side, q, grasp=None, exact=()):
        """What this arm would be inside, at pose q, with the objects where the robot believes they are."""
        from . import collide
        arm_q = dict(self.arm_q)
        arm_q[side] = self._full(side, q)          # a palm-only pose has the wrist straight
        saved, self.arm_q = self.arm_q, arm_q
        try:
            pose = self._pose()
        finally:
            self.arm_q = saved
        objs = {o: None if self.where[o][0] in ("held", "given") else self.pos[o] for o in OBJECTS}
        ignore = {mocap_name(o) for o in ({grasp} | getattr(self, "handling", set())) if o in OBJECTS}
        # an object the robot has only SEEN gets a margin of SIGMAS x how unsure the camera is about where it is
        margins = {mocap_name(o): SIGMAS * s for o, s in getattr(self, "pos_sigma", {}).items()
                   if self.where[o][0] not in ("held", "given")}
        return [h for h in collide.pose_hits(self.m, pose, objs, ignore, tol=0.0, clearance=CLEARANCE,
                                             obj_margin=margins, exact=exact) if h[0].lower().startswith(side)]

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
        self._to_rest(0.6)                                       # arms in before driving
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
        g = self._plan_grasp(o, side)
        if g is None and AUTO_CLEAR and not getattr(self, "_clearing", False):
            # something else where the hand has to go: move it aside first, then take what we came for
            for b in self._grasp_blockers(o, side):
                self.said.append(f"moving the {b} out of the way")
                self._clearing = True
                try:
                    self.put_on(b, room, away_from=p)
                finally:
                    self._clearing = False
                if self.held[side]:
                    side = "left" if side == "right" else "right"
            g = self._plan_grasp(o, side)
        for shift in (0.0, 0.10, -0.10, 0.18, -0.18):        # too close to the middle: step sideways, like a person
            if g is not None:
                break
            if shift:
                self._shift(shift)
            # either free hand: after a side-step the other hand is often the one that fits (the sponge: right hand
            # at +10 cm, left hand at -10 cm)
            for s in [side] + [x for x in ("left", "right") if x != side and self.held[x] is None]:
                g = self._plan_grasp(o, s) if shift or s != side else g
                if g is None and self._flat(o) and self.where[o][0] in ("on", "in"):
                    # this hand can't pinch (thumb and index stay 4 cm apart), so a flat thing is slid to the
                    # counter's edge and taken by the half that sticks out - how people pick up a card or a coin
                    blockers = []
                    slid = self._slide_to_edge(o, s, blockers)
                    if not slid and blockers and AUTO_CLEAR and not getattr(self, "_clearing", False):
                        for b in blockers:                     # neighbours in the way of the slide: move them first
                            self.said.append(f"moving the {b} out of the way")
                            self._clearing = True
                            try:
                                self.put_on(b, room, away_from=p)
                            finally:
                                self._clearing = False
                        slid = self._slide_to_edge(o, s)
                    if slid:
                        g = self._plan_grasp(o, s)
                if g is not None:
                    side = s
                    break
        if g is None:
            return self.problems.append(f"pick {o}: no clean way to get a hand round it")
        pre, q, an, dz = g
        p = self.grip_at.get(o, p)
        self.set_grip(side, PRESHAPE, None, 0.3)               # pre-shape: straight open fingers hit the counter
        high = [self._gsolve(side, p + (0, 0, dz + 0.03 + up) - an * 0.08, an, loose=True) for up in (0.12, 0.22)]
        self._go_q(side, pre, why=f"pick {o}", grasp=o, vias=high)   # in from above at the grasp angle
        self._go_q(side, q, 0.6, grasp=o)
        if self.where[o][0] == "in":
            self.filled[self.where[o][1]] -= 1
        self.held[side], self.where[o] = o, ("held", side)
        self.set_grip(side, 0.8, ("attach", side, mocap_name(o)[4:]))
        self.grasp_dir[o] = (an, dz)                           # how it is held: placing it uses the same grasp
        self.grasp_off[o] = (np.asarray(p) - self.pos[o], self.base[2])   # where on it the hand is (an overhang)
        self.grip_at.pop(o, None)
        lift = self._gsolve(side, p + (0, 0, dz + 0.10), an, loose=True)
        if lift is not None:
            self._go_q(side, lift, 0.6)

    # ---- grasping with the fingers, not the palm (Kimi round 12)
    def _gsolve(self, side, target, approach, loose=False):
        """Joint angles that put the GRASP POINT (where the closed fingers meet) on target, hand along approach.
        Cached per task: the same grasp gets re-planned after an obstacle is moved or the base steps aside."""
        key = (side, tuple(np.round(target, 3)), tuple(np.round(approach, 3)), tuple(np.round(self.base, 3)), loose)
        cache = self.__dict__.setdefault("_gcache", {})
        if key not in cache:
            cache[key], _, _ = reach.solve_grasp(self.m, target, approach, side=side, base=self.base,
                                                 closed=self._fingers(side, 0.8),
                                                 accept=(0.03, 0.5) if loose else (0.012, 0.35))  # waypoints: rough
        q = cache[key]
        return dict(q) if q is not None else None

    def _approaches(self, side, p):
        """Ways in, most natural first: from the shoulder towards the object, tipped 40-60 deg down, or turned 30 deg."""
        sh = to_world(self.base, (0.2 if side == "left" else -0.2, 0.0))
        f = np.asarray(p[:2]) - sh
        f = f / (np.linalg.norm(f) + 1e-9)
        out = []
        for tilt in (-0.3, 0.0, -0.6, -1.0):                  # level-ish first: the hand wraps round from the side
            for yaw in (0.0, 0.5, -0.5, 1.0, -1.0):
                c, s = np.cos(yaw), np.sin(yaw)
                a = np.array([c * f[0] - s * f[1], s * f[0] + c * f[1], tilt])
                out.append(a / np.linalg.norm(a))
        return out

    def _grasp_poses(self, o, side):
        """(pre-grasp, grasp, approach, dz) candidates that the arm can reach, in order - collision not checked."""
        p = self.grip_at.get(o, self.pos[o])            # a slid-out flat thing is taken by its overhang
        for dz in (0.0, 0.01):
            for an in self._approaches(side, p):
                q = self._gsolve(side, p + (0, 0, dz), an)
                if q is None:
                    continue
                pre = self._gsolve(side, p + (0, 0, dz + 0.03) - an * 0.08, an, loose=True)
                if pre is not None:
                    yield pre, q, an, dz

    def _flat(self, o):
        return 2 * OBJECTS[o][5] < FLAT_H

    def _extent(self, o, room):
        """Half size of o along the counter's depth (objects are world-aligned, counters are turned per room)."""
        typ, size = OBJECTS[o][2], [float(v) for v in OBJECTS[o][3].split()]
        if typ in ("sphere", "cylinder"):
            return size[0]
        yaw = ROOMS[room][2]
        dy = np.array([-np.sin(yaw), np.cos(yaw)])          # the room's local y (towards the robot) in world
        return abs(dy[0]) * size[0] + abs(dy[1]) * size[1]

    def _slide_to_edge(self, o, side, blockers=None):
        """Knuckles on top of o, slide it towards the robot until half of it sticks out over the counter's front
        edge; afterwards pick() takes it by that half, where there is air underneath. Checked like every move."""
        room = self._room_of(o)
        frame = ROOMS[room]
        p = self.pos[o]
        loc = to_local(frame, p[:2])
        ext = self._extent(o, room)
        edge = COUNTER_EDGE
        if self.where[o][0] == "in":                         # on top of a container: its own front edge
            _, (cx, cy), (hx, hy, hz), _ = CONTAINERS[self.where[o][1]]
            edge = cy + hy
        if loc[1] + ext >= edge + 0.8 * ext:                 # already sticking out enough
            new_loc = loc
        else:
            new_loc = np.array([loc[0], edge])                # centre on the edge: half on, half over the air
        new = np.array([*to_world(frame, new_loc), p[2]])
        if not self._slide(o, side, new, blockers):
            return False
        overhang = to_world(frame, (new_loc[0], edge + ext / 2))
        self.grip_at[o] = np.array([overhang[0], overhang[1], p[2]])
        return True

    def _edge_of(self, where, room):
        """Room-local y of the front edge of what o stands on: the counter top, or a container's top."""
        if where[0] == "in":
            _, (cx, cy), (hx, hy, hz), _ = CONTAINERS[where[1]]
            return cy + hy
        return COUNTER_EDGE

    def _slide(self, o, side, new, blockers=None):
        """Knuckles (a fist) on top of o, slide it along its surface to new. Every pose and the way there checked."""
        p = self.pos[o]
        fist = self._fingers(side, 1.0)
        surf = {self._surface(o)}

        def solve(xyz, an, loose=False):
            q, _, _ = reach.solve_grasp(self.m, xyz, an, side=side, base=self.base, closed=fist,
                                        accept=(0.03, 0.6) if loose else (0.015, 0.5))
            return q
        plan = None
        closed, self.grip[side] = self.grip[side], 1.0     # checked as a fist
        try:
            for fh in (0.03, 0.045, 0.06):                 # the arm can't point a fist straight down: come in like a grasp
                top = OBJECTS[o][5] + fh
                for down in self._approaches(side, p):
                    on = solve(p + (0, 0, top), down)
                    drag = solve(new + (0, 0, top), down) if on is not None else None
                    above = solve(p + (0, 0, top + 0.08), down, True) if drag is not None else None
                    if above is None:
                        continue
                    hits = (self._hits(side, on, o, surf) + self._hits(side, drag, o, surf) +
                            self._path_hits(side, above, on, o, surf) + self._path_hits(side, on, drag, o, surf))
                    if not hits:
                        plan = (on, drag, above, top, down)
                        break
                    if blockers is not None and not blockers:     # what is in the way of the most natural slide
                        blockers += list(dict.fromkeys(h[1][4:].replace("_", " ") for h in hits
                                                       if h[1].startswith("obj_") and
                                                       h[1][4:].replace("_", " ") in OBJECTS))
                if plan:
                    break
        finally:
            self.grip[side] = closed
        if plan is None:
            return False
        on, drag, above, top, down = plan
        self.set_grip(side, 1.0, None, 0.3)                   # a fist: short, hard knuckles
        self._go_q(side, above, why=f"slide {o}", grasp=o)
        self._go_q(side, on, 0.5, grasp=o)
        self._go_q(side, drag, 0.8, ("slide", mocap_name(o)[4:], tuple(new)), grasp=o)
        self.pos[o] = np.asarray(new, float)
        self._go_q(side, solve(new + (0, 0, top + 0.08), down, True) or above, 0.4)
        self.set_grip(side, 0.0, None, 0.3)
        return True

    def _grasp_clear(self, o, side, pre, q):
        """Hits for a grasp: open hand coming in (pre-grasp, the way in, at the object) and the hand closed on it.
        The surface the object stands on may be approached closely - a hand picking up a plate is near the table -
        but never entered (no safety margin there, only real contact counts)."""
        ex = {self._surface(o)}
        opened, self.grip[side] = self.grip[side], PRESHAPE        # the hand comes in half-curled, not flat open
        try:
            hits = self._hits(side, pre, o) + self._hits(side, q, o, ex) + self._path_hits(side, pre, q, o, ex)
        finally:
            self.grip[side] = opened
        open_, self.grip[side] = self.grip[side], 0.8
        try:
            hits += self._hits(side, q, o, ex)
        finally:
            self.grip[side] = open_
        return hits

    def _surface(self, o, where=None):
        """The body o stands on: a counter, or a container it is in."""
        w = where or self.where[o]
        return "cont_" + w[1] if w[0] == "in" else "counter_" + str(self._room_of(o) or self.room).replace(" ", "_")

    def _plan_grasp(self, o, side):
        for pre, q, an, dz in self._grasp_poses(o, side):
            if not self._grasp_clear(o, side, pre, q):
                return pre, q, an, dz
        return None

    def _grasp_blockers(self, o, side):
        """Other objects in the way of the most natural reachable grasp."""
        for pre, q, an, dz in self._grasp_poses(o, side):
            hits = self._grasp_clear(o, side, pre, q)
            return list(dict.fromkeys(h[1][4:].replace("_", " ") for h in hits
                                      if h[1].startswith("obj_") and h[1][4:].replace("_", " ") in OBJECTS))
        return []

    def _shift(self, dx):
        """Roll the base to dx metres along the counter from its parked spot (arms tucked first). Absolute, not
        relative: the old relative steps +10, -10, +18, -18 cm visited +10, 0, +18, 0 and never the other side."""
        if self.room not in ROOMS or self.room == "you":
            return
        self._to_rest(0.4)
        xy = to_world(ROOMS[self.room], (dx, 0.0))
        moved = float(np.hypot(xy[0] - self.base[0], xy[1] - self.base[1]))
        self.base = (float(xy[0]), float(xy[1]), self.base[2])
        self.frames.append((max(moved / DRIVE_V, 0.3), self._pose(), None))

    def _full(self, side, q):
        """Every arm pose names the wrist bend too (palm-only solves leave it straight)."""
        return {reach.wrist_flex(side): 0.0, **q}

    def _go_q(self, side, q, seconds=None, event=None, grasp=None, why="", vias=()):
        q = self._full(side, q)
        self._detour(side, q, grasp, extra=vias)
        need = max(abs(q[n] - self.arm_q[side].get(n, 0.0)) for n in q) / motor.ARM_SPEED
        self.arm_q[side] = q
        self.frames.append((max(seconds or 0.0, need, 0.3), self._pose(), event))

    def _blockers(self, o, side, xyz):
        """Other objects the hand would go through coming down onto o at xyz - above it, the way down, the grip
        (checked on the body, nothing moved)."""
        # exactly the two moves pick() makes - the approach (8 cm higher) and the grip - via the same solver as move()
        down = self._solve_clear(side, xyz, grasp=o)
        up = self._solve_clear(side, np.asarray(xyz) + (0, 0, 0.08), grasp=o)
        q, above = down["q"], up["q"]
        if q is None:
            return []
        hits = down["in_way"] + up["in_way"] + self._hits(side, q, grasp=o)
        if above is not None:
            hits += self._path_hits(side, above, q, grasp=o)
        open_, self.grip[side] = self.grip[side], 0.8          # curling fingers sweep sideways into a neighbour
        try:
            hits += self._hits(side, q, grasp=o)
        finally:
            self.grip[side] = open_
        return list(dict.fromkeys(h[1][4:].replace("_", " ") for h in hits
                                  if h[1].startswith("obj_") and h[1][4:].replace("_", " ") in OBJECTS))

    def _holding(self, o):
        side = next((s for s, v in self.held.items() if v == o), None)
        if side is None:
            self.pick(o)
            side = next((s for s, v in self.held.items() if v == o), None)
        return side

    def _held_off(self, o):
        """From o's centre to where the hand holds it (non-zero for a flat thing taken by its overhang), turned with
        the base since it was picked up."""
        off, yaw0 = self.grasp_off.get(o, (np.zeros(3), self.base[2]))
        a = self.base[2] - yaw0
        c, s = np.cos(a), np.sin(a)
        return np.array([c * off[0] - s * off[1], s * off[0] + c * off[1], off[2]])

    def _place_poses(self, o, xyz, side):
        """(above, place, approach, dz) that set o down with its centre at xyz + its half height, held the way it was
        picked up (the grasp point carries the object - it lands ON the surface instead of dropping from the air)."""
        c = np.array([xyz[0], xyz[1], xyz[2] + OBJECTS[o][5]]) + self._held_off(o)   # grasp point, not centre
        held = self.grasp_dir.get(o)
        tries = ([held] if held else []) + [(a, 0.0) for a in self._approaches(side, c)]
        for an, dz in tries:
            q = self._gsolve(side, c + (0, 0, dz + 0.004), an)
            above = self._gsolve(side, c + (0, 0, dz + 0.10), an, loose=True) if q is not None else None
            if above is not None:
                yield above, q, an, dz

    def _drop_at(self, o, xyz, where, side):
        held_off = self.grasp_off.get(o, (np.zeros(3), 0))[0]
        if self._flat(o) and np.linalg.norm(held_off) > 0.01:
            # held by its overhang: the fingers are under it, so it goes down half over the front edge (the way it
            # came up) and is then pushed in to the spot with the knuckles
            room = where[1] if where[0] == "on" else CONTAINERS[where[1]][0]
            frame = ROOMS[room]
            loc = to_local(frame, np.asarray(xyz[:2]))
            surf = {"cont_" + where[1] if where[0] == "in" else "counter_" + room.replace(" ", "_")}
            edge_xy = None
            for dx in (0.0, 0.03, -0.03, 0.06, -0.06):     # along the edge until the hand can set it down cleanly
                cand = to_world(frame, (loc[0] + dx, self._edge_of(where, room)))
                if self._drop_clear(o, (cand[0], cand[1], xyz[2]), side, surf=surf):
                    edge_xy = cand
                    break
            if edge_xy is None:
                self.problems.append(f"put {o}: no clean way to set it down on that edge")
                return False
            if not self._drop_at_exact(o, (edge_xy[0], edge_xy[1], xyz[2]), where, side):
                return False
            target = np.array([xyz[0], xyz[1], xyz[2] + OBJECTS[o][5]])
            if np.linalg.norm(target[:2] - edge_xy) > 0.01:
                self._slide(o, side, target)                   # if it can't be pushed in, it stays at the edge
            return True
        return self._drop_at_exact(o, xyz, where, side)

    def _drop_at_exact(self, o, xyz, where, side):
        h = OBJECTS[o][5]
        x, y, z = xyz
        plan = next((pl for pl in self._place_poses(o, xyz, side)
                     if not (self._hits(side, pl[0], o) or self._hits(side, pl[1], o, {self._surface(o, where)})
                             or self._path_hits(side, pl[0], pl[1], o, {self._surface(o, where)}))), None)
        if plan is None:                   # no silent unchecked fallback: that is how a hand ended up 5 mm in the sink
            self.problems.append(f"put {o}: the {side} hand can't set it down there without touching something")
            return False
        above, q, an, dz = plan
        g0 = np.array([x, y, z + h]) + self._held_off(o)          # the grasp point when it is in place
        high = [self._gsolve(side, g0 + (0, 0, dz + up), an, loose=True) for up in (0.2, 0.3)]
        self._go_q(side, above, why=f"put {o}", vias=high)       # come down onto the spot at the grasp angle
        self._go_q(side, q, 0.6)
        self.pos[o] = np.array([x, y, z + h])
        self.held[side], self.where[o] = None, where
        self.grasp_dir.pop(o, None)
        # let go by opening only to the half-curled pre-shape (flat open fingers poked 3-5 mm into the basket), lift
        # straight up at the same angle, and relax the hand later, away from everything
        self.set_grip(side, PRESHAPE, ("detach", mocap_name(o)[4:], (x, y, z + h)))
        up = self._gsolve(side, g0 + (0, 0, dz + 0.12), an, loose=True)
        self.grasp_off.pop(o, None)
        self._go_q(side, up if up is not None else above, 0.5)
        return True

    def set_grip(self, side, amount, event=None, seconds=0.5):
        """Open fingers are longer than curled ones: letting go right above a box put them 3.5 cm into it. Before
        opening, check the open hand; if it would hit something, lift until it clears, then let go."""
        if amount < self.grip[side] - 1e-6 and hasattr(self, "handling"):
            closed, self.grip[side] = self.grip[side], amount
            blocked = self._hits(side, self.arm_q[side])
            q = None
            if blocked:
                here = self._hand_xyz(side)
                for dz in RAISES[1:]:
                    q2, _ = reach.solve(self.m, here + (0, 0, dz), side=side, base=self.base)
                    q2 = self._full(side, {**self.arm_q[side], **q2}) if q2 is not None else None
                    if q2 is not None and not self._hits(side, q2):
                        q = q2
                        break
            self.grip[side] = closed
            if q is not None:
                need = max(abs(q[n] - self.arm_q[side].get(n, 0.0)) for n in q) / motor.ARM_SPEED
                self.arm_q[side] = q
                self.frames.append((max(need, 0.3), self._pose(), None))
            elif blocked:
                self.problems.append(f"opening the {side} hand would hit the "
                                     f"{blocked[0][1].replace('counter_', '').replace('cont_', '').replace('_', ' ')}")
        super().set_grip(side, amount, event, seconds)

    def _drop_clear(self, o, xyz, side, into=None, surf=None):
        """Would dropping o at xyz (down from above, release, back up) keep this hand clear of everything already
        there? Checked on the body before choosing the spot - nothing is committed."""
        surf = surf or ({"cont_" + into} if into else set())
        for above, q, an, dz in self._place_poses(o, xyz, side):
            if not (self._hits(side, above, o) or self._hits(side, q, o, surf) or self._path_hits(side, above, q, o, surf)):
                return True
        return False

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
        z = TABLE_Z + 2 * half[2] + 0.01 * (n // len(offs))
        # the next free spot first, then the others: take the first one the hand can drop into without brushing
        # what is already in there (the plate going in next to the cup)
        spots = [offs[(n + k) % len(offs)] for k in range(len(offs))]
        xy = to_world(room, (loc[0] + spots[0][0], loc[1] + spots[0][1]))
        for dx, dy in spots:
            cand = to_world(room, (loc[0] + dx, loc[1] + dy))
            want = self._side_for((cand[0], cand[1], z))
            use = want if (want == side or self.held[want] is None) else side
            if self._drop_clear(o, (cand[0], cand[1], z), use, into):
                xy = cand
                break
        want = self._side_for((xy[0], xy[1], z))
        if want != side and self.held[want] is None:
            self.pass_to(o, want)
            side = want
        if self._drop_at(o, (xy[0], xy[1], z), ("in", into), side):
            self.filled[into] += 1

    def put_on(self, o, room, away_from=None):
        """away_from (xy): clearing an obstacle - use the free spot farthest from what the hand is going for."""
        room = {"living": "living room", "table": "living room", "counter": "kitchen"}.get(room, room)
        if room not in ROOMS or room == "you":
            return self.problems.append(f"put_on: no counter in '{room}'")
        side = self._holding(o)
        if side is None:
            return
        self.go(room)
        side = next((s for s, v in self.held.items() if v == o), side)
        spots = FREE_SPOTS if away_from is None else \
            sorted(FREE_SPOTS, key=lambda s: -np.linalg.norm(to_world(room, s) - np.asarray(away_from)[:2]))
        free = []
        for loc in spots:
            xy = to_world(room, loc)
            clear_objs = all(np.linalg.norm(self.pos[k][:2] - xy) > 0.07 for k in self.pos if k != o and
                             self.where[k][0] != "held")
            clear_boxes = all(np.linalg.norm(to_world(r, c) - xy) > 0.13 for r, c, *_ in CONTAINERS.values() if r == room)
            if clear_objs and clear_boxes:
                free.append(xy)
        # the first free spot the hand can really set it down on (it used to take the first free spot, then find the
        # hand couldn't place there)
        xy = free[0] if free else to_world(room, spots[0])
        surf = {"counter_" + room.replace(" ", "_")}
        found = False
        for shift in (0.0, 0.10, -0.10, 0.18, -0.18):        # nowhere this hand can place: step sideways, like pick
            if shift:
                self._shift(shift)
            for cand in free:
                want = self._side_for((cand[0], cand[1], TABLE_Z))
                use = want if (want == side or self.held[want] is None) else side
                if self._drop_clear(o, (cand[0], cand[1], TABLE_Z), use, surf=surf):
                    xy, found = cand, True
                    break
            if found:
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
        if room in self.messes:               # it knows where the stain is: wipe with the hand on that side
            want = "left" if STAIN_SPOTS[room][0] > 0 else "right"
            if side != want and self.held[want] is None:
                self.pass_to("sponge", want)
                side = next((s for s, v in self.held.items() if v == "sponge"), side)
        xs = (-0.22, -0.06) if side == "right" else (0.06, 0.22)          # the middle 10 cm is out of reach
        path = [(lx, ly) for k, ly in enumerate((-0.26, -0.30, -0.34)) for lx in (xs if k % 2 == 0 else xs[::-1])]
        for p in path:
            self.move(side, self._local_xyz(p, TABLE_Z + 0.05), 0.5, why="wipe")
        self.wiped.add(room)
        if room in self.messes:
            # only what the sponge actually went over gets clean: distance from the stain to the stroke path
            st = np.array(STAIN_SPOTS[room])
            gap = min(_seg_dist(st, np.array(a), np.array(b)) for a, b in zip(path, path[1:]))
            if gap <= STAIN_R + SPONGE_HALF:
                self.messes.pop(room)
                self.frames.append((0.2, self._pose(), ("clean", "mess_" + room.replace(" ", "_"))))
            else:
                self.problems.append(f"wipe: the sponge never went over the stain in the {room} "
                                     f"({100 * (gap - STAIN_R - SPONGE_HALF):.0f} cm away)")
        back = home[1] if home[0] == "on" else "kitchen"
        self.put_on("sponge", back)

    def toss(self, o, to=None, height=0.25):
        side = self._holding(o)
        if side is None:
            return
        # reuse the table-top toss in the robot's own frame: temporarily treat the parked frame as the origin
        # juggle at chest height near the body, 25 cm over the counter - at 7 cm the hands went into the counter and
        # the things on it (tools/collisions.py)
        release = self._local_xyz((-0.12 if side == "right" else 0.12, -0.24), TABLE_Z + 0.25)
        to = to if to in ("right", "left") else side
        catch = self._local_xyz((-0.12 if to == "right" else 0.12, -0.24), TABLE_Z + 0.25)
        if not self.move(side, release, 0.8, why="toss"):
            return
        vz = np.sqrt(2 * motor.G * float(np.clip(height, 0.05, 0.5)))
        tf = 2 * vz / motor.G
        v = ((catch[0] - release[0]) / tf, (catch[1] - release[1]) / tf, vz)
        self.held[side] = None
        q, _ = reach.solve(self.m, catch - [0, 0, 0.02], side=to, base=self.base)
        need = max(abs(q[n] - self.arm_q[to].get(n, 0.0)) for n in q) / motor.ARM_SPEED if q else 1e9
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
        if not hasattr(self, "pos0"):              # where things were when the program started (for replays)
            self.pos0 = {o: p.copy() for o, p in self.pos.items()}
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
        self.step_at = []                     # (first frame, step index, action): lets hand/collide.py name the step
        for i, a in enumerate(program if isinstance(program, list) else []):
            self.step_at.append((len(self.frames), i, a))
            # what this step handles is not an obstacle during it (a wipe fetches the sponge)
            self.handling = ({a.get("obj")} | ({"sponge"} if a.get("do") == "wipe" else set())) \
                if isinstance(a, dict) else set()
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
                # one action at a time, so motor.Body calls every step "step 1": renumber to its real place
                n0 = len(self.problems)
                super().run([a], finish=False)
                for k in range(n0, len(self.problems)):
                    self.problems[k] = re.sub(r"^step 1\b", f"step {i + 1}", self.problems[k])
        if finish:
            for s in ("right", "left"):
                if self.held[s]:
                    self.put_on(self.held[s], self.room if self.room in ("kitchen", "laundry", "living room")
                                else "living room")
            self._to_rest(1.0)
            self.grip = {"right": 0.0, "left": 0.0}          # relax the hands only once they are tucked in
            self.frames.append((0.4, self._pose(), None))
        return self
