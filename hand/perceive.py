"""Seeing messes: RGB + depth from a camera over each counter. One-shot learning, no training.

The robot looks at each counter once while it is clean and remembers the picture (colour and depth). Later, a mess is
what has CHANGED HUE WITHOUT CHANGING DEPTH: a stain is flat, so the surface is where it was, only a different colour; a shadow keeps
the hue and only darkens.
Anything that changes depth is an object arriving or leaving (a cup put down, a shirt picked up), not a mess. The same
rule works on a real depth camera (RealSense-class) with the remembered frame taken on a clean day.

    eyes = Eyes(m); eyes.learn()                 # counters are clean now: remember them
    set_messes(m, {"living room"})               # sim only: put a stain in the world
    eyes.survey()                                # -> {"living room": "a dark stain about 9 cm across"}  (from pixels)
"""
import mujoco
import numpy as np

from . import home

W, H = 160, 120
DEPTH_TOL = 0.004          # m: a stain is 3 mm thick; an object is at least ~1.5 cm
COLOUR_TOL = 15            # 0-255 RGB distance from the remembered pixel: a spill on a brown table is only ~25
CHROMA_TOL = 9             # x255, change in r:g:b proportions. Stains measured 13-35, shadows 4-10 (median)
MIN_PIXELS = 30            # ~1.3 cm^2 at this range: smaller is noise; a lone crumb goes unseen
OBJ_MIN_H = 0.006          # m: standing this far above the empty surface = an object (a plate is 1.6 cm)
OBJ_MIN_PIXELS = 8
TOP_BAND = 0.01            # m: pixels this close to the highest point are the top face
MATCH_MAX = 6.0            # worse than this and a blob is not called anything
ROOMS = ("kitchen", "laundry", "living room")


def _chroma(rgb):
    x = rgb.astype(float) + 1.0
    return x / x.sum(axis=-1, keepdims=True)


def _tag(room):
    return room.replace(" ", "_")


def _components(mask, colour=None, tol=12.0, depth=None, step=0.01):
    """4-connected blobs of a boolean image -> list of [(row, col), ...] (no scipy on this machine)."""
    seen = np.zeros_like(mask, dtype=bool)
    out = []
    for v0, u0 in zip(*np.nonzero(mask)):
        if seen[v0, u0]:
            continue
        stack, pix = [(v0, u0)], []
        seen[v0, u0] = True
        while stack:
            v, u = stack.pop()
            pix.append((v, u))
            for dv, du in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                a, b = v + dv, u + du
                if 0 <= a < mask.shape[0] and 0 <= b < mask.shape[1] and mask[a, b] and not seen[a, b] and \
                        (colour is None or np.linalg.norm(colour[a, b] - colour[v, u]) * 255 < tol) and \
                        (depth is None or abs(depth[a, b] - depth[v, u]) < step):
                    seen[a, b] = True
                    stack.append((a, b))
        out.append(pix)
    return out


def _looks(o):
    """What object o should look like from above: chroma of its colour, height, top-view area."""
    typ, size, rgba = home.OBJECTS[o][2], [float(x) for x in home.OBJECTS[o][3].split()], home.OBJECTS[o][4]
    rgb = np.array([float(x) for x in rgba.split()[:3]]) * 255
    area = np.pi * size[0] ** 2 if typ in ("sphere", "cylinder") else 4 * size[0] * size[1]
    return {"chroma": _chroma(rgb[None])[0], "height": 2 * home.OBJECTS[o][5], "area": area}


def set_messes(m, rooms):
    """Put stain decals in the world (the sim's ground truth). Hidden ones sit under the floor."""
    for room in ROOMS:
        g = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, f"mess_{_tag(room)}")
        m.geom_pos[g][2] = home.TABLE_Z + 0.0015 if room in rooms else -1.0


class Eyes:
    def __init__(self, m, d=None):
        self.m, self.d = m, d if d is not None else mujoco.MjData(m)
        self.memory = {}

    def _snap(self, r, room):
        r.update_scene(self.d, camera=f"look_{_tag(room)}")
        rgb = r.render().astype(np.int16)
        r.enable_depth_rendering()
        depth = r.render().copy()
        r.disable_depth_rendering()
        return rgb, depth

    def _each(self, fn):
        mujoco.mj_forward(self.m, self.d)
        r = mujoco.Renderer(self.m, H, W)
        try:
            return {room: fn(*self._snap(r, room)) for room in ROOMS}
        finally:
            r.close()

    def learn(self):
        """Remember every counter as it looks now (call when clean)."""
        self.memory = self._each(lambda rgb, depth: (rgb, depth))
        return self

    def changes(self):
        """{room: mask of pixels that changed colour but not depth}."""
        def diff(rgb, depth, room):
            rgb0, depth0 = self.memory[room]
            same_place = np.abs(depth - depth0) < DEPTH_TOL
            # a shadow makes the surface darker but keeps its hue; a spill changes the hue. Needing both keeps the
            # shadow of a cup that was just moved from being called a stain.
            recoloured = (np.linalg.norm(rgb - rgb0, axis=-1) > COLOUR_TOL) & \
                (np.linalg.norm(_chroma(rgb) - _chroma(rgb0), axis=-1) * 255 > CHROMA_TOL)
            return same_place & recoloured, rgb, rgb0
        out = {}
        mujoco.mj_forward(self.m, self.d)
        r = mujoco.Renderer(self.m, H, W)
        try:
            for room in ROOMS:
                out[room] = diff(*self._snap(r, room), room)
        finally:
            r.close()
        return out

    # ---- where things are (Kimi round 11: poses from the cameras, with how sure it is)
    def learn_empty(self):
        """Remember every counter with nothing on it (sim: objects moved away for the snapshot, then put back)."""
        saved = self.d.mocap_pos.copy()
        self.d.mocap_pos[:] = (0.0, 0.0, -5.0)
        try:
            self.empty = self._each(lambda rgb, depth: (rgb, depth))
        finally:
            self.d.mocap_pos[:] = saved
        return self

    def blobs(self):
        """Everything standing on a counter now: [{room, xyz of its top, height, area, chroma, pixels}]."""
        out = []
        mujoco.mj_forward(self.m, self.d)
        r = mujoco.Renderer(self.m, H, W)
        try:
            for room in ROOMS:
                rgb, depth = self._snap(r, room)
                rgb0, depth0 = self.empty[room]
                above = depth < depth0 - OBJ_MIN_H
                cam = self.m.cam(f"look_{_tag(room)}").id
                cpos = self.d.cam_xpos[cam]
                for pix in _components(above, _chroma(rgb), depth=depth):   # colour or height edges split what touches
                    if len(pix) < OBJ_MIN_PIXELS:
                        continue
                    vs, us = np.array(pix).T
                    zt = float(depth[vs, us].min())                       # the object's top, from the camera
                    s = 2 * zt * np.tan(np.radians(30)) / H              # metres per pixel at that distance
                    # centre from the TOP face only: seen at an angle, a tall can shows its side too, which dragged
                    # the centroid 2 cm outward
                    top = depth[vs, us] <= zt + TOP_BAND
                    cx = (us[top].mean() + 0.5 - W / 2) * s               # camera frame: x right, y up the image
                    cy = (H / 2 - vs[top].mean() - 0.5) * s
                    axes = self.d.cam_xmat[cam].reshape(3, 3)             # turned with the counter
                    xy = cpos[:2] + axes[:2, 0] * cx + axes[:2, 1] * cy
                    out.append({"room": room, "top": np.array([xy[0], xy[1], cpos[2] - zt]),
                                "height": float(np.median(depth0[vs, us]) - zt), "area": len(pix) * s * s,
                                "chroma": _chroma(rgb[vs, us]).mean(axis=0), "px": s})
        finally:
            r.close()
        return out

    def locate(self, names=None):
        """{object: (xyz centre, sigma m)} for the objects it can see, matched by colour, height and size."""
        names = list(names or home.OBJECTS)
        bl = self.blobs()
        cost = []
        for i, b in enumerate(bl):
            for o in names:
                want = _looks(o)
                c = (np.linalg.norm(b["chroma"] - want["chroma"]) * 20 + abs(b["height"] - want["height"]) / 0.01
                     + abs(np.log(max(b["area"], 1e-6) / want["area"])))
                cost.append((c, i, o))
        out, used_b, used_o = {}, set(), set()
        for c, i, o in sorted(cost):                                     # greedy: best matches first
            if i in used_b or o in used_o or c > MATCH_MAX:
                continue
            used_b.add(i)
            used_o.add(o)
            b = bl[i]
            xyz = b["top"] - (0, 0, home.OBJECTS[o][5])
            out[o] = (xyz, b["px"] / np.sqrt(12) + 0.002 * np.sqrt(c))  # pixel quantisation + worse for poor matches
        return out

    def survey(self):
        """Look at every counter -> {room: description} for the ones with a mess."""
        if not self.memory:
            raise RuntimeError("Eyes.learn() first, on clean counters")
        px = 2 * home.LOOK_H * np.tan(np.radians(30)) / H          # metres per pixel on the counter (fovy 60)
        out = {}
        for room, (mask, rgb, rgb0) in self.changes().items():
            n = int(mask.sum())
            if n < MIN_PIXELS:
                continue
            across = 2 * np.sqrt(n * px * px / np.pi) * 100
            darker = rgb0[mask].mean() - rgb[mask].mean()
            out[room] = f"a {'dark' if darker > 0 else 'light'} stain about {across:.0f} cm across"
        return out
