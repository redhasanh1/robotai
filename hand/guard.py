"""Squeeze guard: stop a finger from stalling against an object.

Found by hand/power.py: a power grasp commands 0.9 flexion, a can stops the fingers at ~0.6, and five MG996Rs push
at near-stall (~2.5 A each) for as long as the grasp is held - 12.5 A on a 12 A supply, and hot servos. The servos
report nothing, but the estimator does: when a finger has stopped moving while its command is still well ahead of
it, it is touching something. The guard then pulls that finger's command back to contact + `squeeze`, which keeps a
firm hold (the servo still pushes, proportionally) without stalling. Opening the hand clears it.

    g = SqueezeGuard()
    cmd_to_send = g.update(cmd, q_estimate, dt)       # every control tick

It needs a real finger estimate: in sim that is exact; on the hardware it needs the fingertip-marker camera or the
pot-wiper mod (MG996Rs report nothing, and the physics-only estimate cannot see an object). Until then, keep grasp
holds short on the real hand.
"""
import numpy as np


class SqueezeGuard:
    def __init__(self, squeeze=0.04, still_speed=0.05, lead=0.08, settle_s=0.15):
        self.squeeze, self.still, self.lead, self.settle = squeeze, still_speed, lead, settle_s
        self.q_prev = None
        self.still_for = None
        self.contact = None               # per joint: flexion where it met the object, NaN = free

    def update(self, cmd, q, dt):
        cmd, q = np.asarray(cmd, float).copy(), np.asarray(q, float)
        if self.q_prev is None:
            self.q_prev, self.still_for = q.copy(), np.zeros_like(q)
            self.contact = np.full_like(q, np.nan)
        speed = np.abs(q - self.q_prev) / max(dt, 1e-6)
        self.q_prev = q.copy()
        pushing = (cmd - q > self.lead) & (speed < self.still)
        self.still_for = np.where(pushing, self.still_for + dt, 0.0)
        new = np.isnan(self.contact) & (self.still_for >= self.settle)
        self.contact = np.where(new, q, self.contact)
        released = ~np.isnan(self.contact) & (cmd < self.contact - 0.02)      # hand opening: forget the contact
        self.contact = np.where(released, np.nan, self.contact)
        limit = self.contact + self.squeeze
        cmd[:5] = np.where(np.isnan(limit[:5]), cmd[:5], np.minimum(cmd[:5], limit[:5]))   # fingers only, not wrist
        return cmd
