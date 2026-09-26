"""System identification: measure the grey-box servo parameters from data instead of trusting the datasheet.

fit(t, cmd, q) takes a log of commanded shaft position and measured finger position (vision, or the pot-wiper
mod later) for ONE joint and returns v_max, tau and backlash in under a second (20 s of 100 Hz data), so OnlineFit
can re-run it in the background and the physics stays calibrated as servos wear (Kimi round 3: the
tau-drift-over-a-week plot). Recovers known parameters within ~10% under 5 mm-equivalent noise (tests/).

Method (per joint): output-error fitting. Simulate the grey-box model for K parameter sets at once (the plant
is vectorised, so K=400 sets x 4000 samples is well under a second), keep the set whose simulated finger path
matches the measured one best, then refine around it. Regressing v = e / tau directly does NOT work here:
tendon slack biases e by +-b/2 and noise wrecks the velocity estimate (first try: tau off by 3x).
"""
from collections import deque

import numpy as np


def _simulate(cmd, dt, v_max, tau, b, db, q0):
    """cmd (T,), params (K,) -> finger path (T, K). Same equations as hand.plant.ServoPlant."""
    K = len(v_max)
    p = np.full(K, q0, float)
    q = p.copy()
    out = np.empty((len(cmd), K))
    sub = max(1, int(np.ceil(dt / 0.002)))
    h = dt / sub
    for i, c in enumerate(cmd):
        for _ in range(sub):
            e = c - p
            v = np.clip(e / tau, -v_max, v_max)
            p = p + h * np.where(np.abs(e) < db, 0.0, v)
            q = np.where(p - q > b / 2, p - b / 2, np.where(q - p > b / 2, p + b / 2, q))
        out[i] = q
    return out


def fit(t, cmd, q, db=0.01, k=300, seed=0):
    """-> {"v_max", "tau", "backlash", "rmse"} or None if the joint barely moved."""
    t, cmd, q = (np.asarray(x, float) for x in (t, cmd, q))
    if len(t) < 20 or np.ptp(q) < 0.05:
        return None
    dt = float(np.median(np.diff(t)))
    rng = np.random.default_rng(seed)
    lo, hi = np.array([0.5, 0.01, 0.0]), np.array([8.0, 0.4, 0.15])
    best, best_err = None, np.inf
    for rnd in range(3):
        if best is None:
            P = lo + (hi - lo) * rng.random((k, 3))
        else:
            span = (hi - lo) * (0.25 / (2 ** rnd))
            P = np.clip(best + span * rng.normal(0, 1, (k, 3)), lo, hi)
            P[0] = best
        sim = _simulate(cmd, dt, P[:, 0], P[:, 1], P[:, 2], db, q[0])
        err = np.sqrt(np.mean((sim - q[:, None]) ** 2, axis=0))
        i = int(np.argmin(err))
        if err[i] < best_err:
            best, best_err = P[i].copy(), float(err[i])
    return {"v_max": round(float(best[0]), 3), "tau": round(float(best[1]), 4),
            "backlash": round(float(best[2]), 4), "rmse": round(best_err, 4), "n": int(len(t))}


def _fit_regression(t, cmd, q, db_prior=0.01):
    """Kept for the write-up: the naive regression that tendon slack breaks."""
    t, cmd, q = (np.asarray(x, float) for x in (t, cmd, q))
    v = np.gradient(q, t)
    e = cmd - q
    if len(t) < 20 or np.ptp(q) < 0.05:
        return None                                  # the joint barely moved: nothing to learn
    moving = np.abs(v) > 0.05
    far = np.abs(e) > 0.25
    v_max = float(np.percentile(np.abs(v[far & moving]), 95)) if np.any(far & moving) else float(np.max(np.abs(v)))
    lin = moving & (np.abs(v) < 0.7 * v_max) & (np.abs(e) > 0.02)
    tau = float(np.sum(e[lin] ** 2) / np.sum(e[lin] * v[lin])) if np.sum(lin) > 5 else float("nan")
    # steady samples: nearly stopped, some time after the command last changed
    settled = (np.abs(v) < 0.02) & (np.abs(e) < 0.15)
    dcmd = np.sign(np.gradient(cmd))
    last_dir = np.zeros_like(cmd)
    d = 0.0
    for i, x in enumerate(dcmd):
        d = x if x != 0 else d
        last_dir[i] = d
    up = settled & (last_dir > 0)
    down = settled & (last_dir < 0)
    slack = float(np.mean(e[up]) - np.mean(e[down])) if up.any() and down.any() else float("nan")
    backlash = max(0.0, slack - 2 * db_prior) if np.isfinite(slack) else float("nan")
    return {"v_max": round(v_max, 3), "tau": round(tau, 4), "slack": round(slack, 4),
            "backlash": round(backlash, 4), "n": int(len(t))}


class OnlineFit:
    """Sliding window per joint; refit every `every` samples. Keeps a history for drift plots."""

    def __init__(self, n_joints=6, window=3000, every=500):
        self.buf = [deque(maxlen=window) for _ in range(n_joints)]
        self.every, self.count = every, 0
        self.params = [None] * n_joints
        self.history = []

    def add(self, t, cmd, q):
        for j, b in enumerate(self.buf):
            b.append((t, cmd[j], q[j]))
        self.count += 1
        if self.count % self.every == 0:
            for j, b in enumerate(self.buf):
                a = np.array(b)
                p = fit(a[:, 0], a[:, 1], a[:, 2])
                if p:
                    self.params[j] = p
                    self.history.append({"t": t, "joint": j, **p})
        return self.params


def excite(n_steps=4000, dt=0.01, seed=0, n_joints=6):
    """A test signal that exercises every regime: big jumps (saturation), small steps (linear), both directions."""
    rng = np.random.default_rng(seed)
    cmd = np.zeros((n_steps, n_joints))
    cur = np.full(n_joints, 0.5)
    for k in range(n_steps):
        if k % 60 == 0:
            big = rng.random(n_joints) < 0.5
            cur = np.where(big, rng.uniform(0, 1, n_joints), np.clip(cur + rng.normal(0, 0.08, n_joints), 0, 1))
        cmd[k] = cur
    if n_joints > 5:
        cmd[:, 5] = cmd[:, 5] * 2 - 1                # wrist spans -1..1
    return np.arange(n_steps) * dt, cmd
