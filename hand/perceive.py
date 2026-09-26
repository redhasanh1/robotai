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
ROOMS = ("kitchen", "laundry", "living room")


def _chroma(rgb):
    x = rgb.astype(float) + 1.0
    return x / x.sum(axis=-1, keepdims=True)


def _tag(room):
    return room.replace(" ", "_")


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
            recoloured = (np.linalg.norm(rgb - rgb0, axis=-1) > COLOUR_TOL) &                          (np.linalg.norm(_chroma(rgb) - _chroma(rgb0), axis=-1) * 255 > CHROMA_TOL)
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
