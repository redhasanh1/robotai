"""The real hand as a "world" for hand.loop - same interface as the sim (grasp_test, render), so the brain loop
that was tested in simulation drives the hardware unchanged.

    world = HardwareWorld(HandLink.open("COM5"), camera=0)
    loop.attempt("pick up the ball", "ball", brain, memory, n=8, world=world, render=True)

grasp_test(q): opens the hand, asks you to place the object, closes smoothly (the firmware slew limit applies on
top), holds, then asks you to turn the hand over (until it is on an arm) and reports whether it held. The
"held" answer comes from you (y/n) - that is ground truth for the benchmark; the brain's own verdict from the
camera is still asked separately by the loop, so we can score how often the AI's self-check is right.
slip_t is None here until the 30 Hz object-marker tracker is on the real hand (then the fast path works too).
"""
import time

import numpy as np

from . import primitives


class HardwareWorld:
    def __init__(self, link, camera=None, ask=input, close_s=1.2, hold_s=2.0):
        self.link, self.ask = link, ask
        self.close_s, self.hold_s = close_s, hold_s
        self.cap = None
        if camera is not None:
            from .vision import open_camera
            self.cap = open_camera(camera)

    def render(self, *_a, **_k):
        if self.cap is None:
            return None
        ok, img = self.cap.read()
        return img[:, :, ::-1] if ok else None          # BGR -> RGB like the sim renderer

    def _go(self, q, seconds):
        start = np.array(self.link.q_cmd, float)
        q = np.asarray(q, float)
        steps = max(1, int(seconds / 0.02))
        for k in range(1, steps + 1):
            self.link.move(start + (q - start) * k / steps)   # smooth ramp; firmware clamps + slew-limits too
            self.link.tick(0.02)

    def grasp_test(self, q):
        self._go(primitives.OPEN, 0.8)
        self.ask("Put the object in the open palm, then press Enter ")
        self._go(q, self.close_s)
        self.link.wait(0.5)
        self.ask("Now turn the hand over (palm down) and shake gently, then press Enter ")
        held = self.ask("Is it still in the hand? [y/n] ").strip().lower().startswith("y")
        self._go(primitives.REST, 0.8)
        return {"held": held, "dist": float("nan"), "touching": [], "slip_t": None,
                "flexion": np.round(self.link.q_cmd, 3).tolist()}
