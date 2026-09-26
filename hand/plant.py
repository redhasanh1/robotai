"""Grey-box physics of a hobby-servo + tendon finger. This is the "physics" in physics-informed.

An MG996R is a position servo: we send a target, its own controller drives the shaft there. So the physics
that matters is not tau = M(q)q'' + C + g (a 10 g PLA finger has almost no inertia) but the actuator:

    shaft speed   p' = clip((p_cmd - p) / tau, -v_lim, +v_lim),   v_lim = v_max * (1 - load_slow * load)
    deadband      p' = 0 when |p_cmd - p| < deadband
    tendon slack  finger q follows shaft p through a play (backlash) operator of width b:
                  q = p - b/2 if p - q > b/2 ; q = p + b/2 if q - p > b/2 ; else q unchanged

Backlash is not an ODE - it is a hysteresis operator with memory, which is exactly why closing and opening
paths differ on a tendon hand. Every parameter is measurable on the bench (tools/servo_calibrate.py) and is
re-fitted online by hand/sysid.py. hand/estimator.py learns only what this model gets wrong.
"""
import numpy as np

from . import config


class ServoPlant:
    def __init__(self, servos=None):
        servos = servos or config.HandConfig().servos
        self.names = [s.name for s in servos]
        g = lambda k: np.array([getattr(s, k) for s in servos], dtype=float)
        self.v_max, self.tau, self.db = g("v_max"), g("tau"), g("deadband")
        self.b, self.load_slow = g("backlash"), g("load_slow")
        self.lo = np.array([s.lo() for s in servos])
        self.hi = np.ones(len(servos))
        self.reset()

    def reset(self, q=None):
        q = np.zeros(len(self.names)) if q is None else np.asarray(q, float).copy()
        self.p = q.copy()   # servo shaft, in flexion units
        self.q = q.copy()   # finger (after tendon slack)

    def shaft_rate(self, p, p_cmd, load):
        e = p_cmd - p
        lim = self.v_max * (1.0 - self.load_slow * np.clip(load, 0.0, 1.0))
        v = np.clip(e / self.tau, -lim, lim)
        return np.where(np.abs(e) < self.db, 0.0, v)

    def play(self, p, q):
        h = self.b / 2
        return np.where(p - q > h, p - h, np.where(q - p > h, p + h, q))

    def step(self, p_cmd, dt, load=0.0, stop=None):
        """Advance dt seconds. stop (optional, per joint) is a flexion the finger cannot pass (an object);
        the shaft stalls there too and load goes to 1 for that joint."""
        p_cmd = np.clip(np.asarray(p_cmd, float), self.lo, self.hi)
        load = np.broadcast_to(np.asarray(load, float), self.p.shape).copy()
        n = max(1, int(np.ceil(dt / 0.002)))
        h = dt / n
        for _ in range(n):
            self.p = np.clip(self.p + h * self.shaft_rate(self.p, p_cmd, load), self.lo, self.hi)
            self.q = self.play(self.p, self.q)
            if stop is not None:
                s = np.asarray(stop, float)
                blocked = ~np.isnan(s) & (self.q > s)
                self.q = np.where(blocked, s, self.q)
                self.p = np.where(blocked, np.minimum(self.p, s + self.b / 2), self.p)
                load = np.where(blocked, 1.0, load)
        return self.q.copy()

    def rollout(self, q0, p0, cmds, dt):
        """Pure prediction, does not touch self: cmds is (T, n) targets -> (T, n) finger positions."""
        saved = self.p, self.q
        self.p, self.q = np.array(p0, float), np.array(q0, float)
        out = np.array([self.step(c, dt) for c in cmds])
        self.p, self.q = saved
        return out

    def time_to_reach(self, q_from, q_to):
        """Seconds for an unloaded move - used to reject plans that cannot finish in their time budget."""
        return float(np.max(np.abs(np.asarray(q_to) - np.asarray(q_from)) / self.v_max + 3 * self.tau))
