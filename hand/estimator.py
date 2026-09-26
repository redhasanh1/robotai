"""Physics-informed state estimator: where are the fingers, right now, and how sure are we?

The MG996Rs report nothing, and the camera sees fingertip markers only some of the time (30 fps at best, hidden
whenever a finger wraps an object). So:

    predict   grey-box servo model (hand.plant, parameters from hand.sysid) rolls the state forward from the
              commands we sent - exact inputs, known physics. A small learned residual maps the physics state to
              the real finger (tendon routing is nonlinear, friction depends on position): an ensemble of tiny
              MLPs whose disagreement is the model's own uncertainty
    update    whenever a camera measurement arrives, blend it in by relative confidence (per-joint Kalman gain)

Output: q (flexion per joint) and std. During occlusion std grows, and the verifier/brain can see that the hand
is running open-loop. This is "physics-informed state estimation with grey-box residual dynamics" - the physics
is the backbone, learning only fills the gap (Kimi round 2: more defensible than a black box with a physics loss).
"""
import numpy as np

from .plant import ServoPlant


class Residual:
    """Ensemble of tiny MLPs: physics state -> offset of the real finger from the physics prediction.

    An output correction, not a dynamics correction: learning per-step deltas made errors compound and fit
    sensor noise (first try made the estimate worse: RMSE 0.0188 vs 0.0027 without it). Needs torch."""

    def __init__(self, n_models=5, hidden=32, seed=0):
        import torch
        self.torch = torch
        torch.manual_seed(seed)
        mk = lambda: torch.nn.Sequential(torch.nn.Linear(4, hidden), torch.nn.Tanh(), torch.nn.Linear(hidden, hidden),
                                         torch.nn.Tanh(), torch.nn.Linear(hidden, 1))
        self.nets = [mk() for _ in range(n_models)]
        self.dev = "cuda" if torch.cuda.is_available() else "cpu"
        for n in self.nets:
            n.to(self.dev)

    @staticmethod
    def features(q, p, cmd):
        return np.stack([q, p, cmd, cmd - p], -1)

    def fit(self, X, y, epochs=300, lr=3e-3):
        """X (M, 4) open-loop physics state features, y (M,) = measured q - physics q. Bootstrap per member."""
        t = self.torch
        X, y = t.tensor(X, dtype=t.float32, device=self.dev), t.tensor(y, dtype=t.float32, device=self.dev)[:, None]
        rng = np.random.default_rng(0)
        loss = None
        for n in self.nets:
            idx = t.tensor(rng.integers(0, len(X), len(X)), device=self.dev)
            opt = t.optim.Adam(n.parameters(), lr=lr)
            for _ in range(epochs):
                opt.zero_grad()
                loss = t.mean((n(X[idx]) - y[idx]) ** 2)
                loss.backward()
                opt.step()
        return float(loss.detach())

    def __call__(self, F):
        t = self.torch
        with t.no_grad():
            x = t.tensor(F, dtype=t.float32, device=self.dev)
            out = t.stack([n(x)[..., 0] for n in self.nets]).cpu().numpy()
        return out.mean(0), out.var(0)


class Estimator:
    def __init__(self, servos=None, residual=None, q_proc=0.02, r_meas=0.03 ** 2):
        self.plant = ServoPlant(servos)
        self.residual = residual
        self.q_proc, self.r = q_proc, r_meas
        self.P = np.full(len(self.plant.names), 1e-4)
        self.offset = np.zeros(len(self.plant.names))

    def reset(self, q=None):
        self.plant.reset(q)
        self.P[:] = 1e-4
        self.offset[:] = 0

    @property
    def q(self):
        return np.clip(self.plant.q + self.offset, self.plant.lo, 1)

    @property
    def std(self):
        return np.sqrt(self.P)

    def predict(self, cmd, dt):
        self.plant.step(cmd, dt)
        var = 0.0
        if self.residual is not None:
            self.offset, var = self.residual(Residual.features(self.plant.q, self.plant.p,
                                                               np.clip(cmd, self.plant.lo, 1)))
        self.P = self.P + (self.q_proc * dt) ** 2 + var * dt
        return self.q

    def update(self, z, seen=None):
        """z: measured flexion per joint (NaN = not seen this frame)."""
        z = np.asarray(z, float)
        seen = ~np.isnan(z) if seen is None else seen
        K = np.where(seen, self.P / (self.P + self.r), 0.0)
        innov = np.where(seen, np.nan_to_num(z) - self.q, 0.0)
        self.plant.q = self.plant.q + K * innov
        self.plant.p = self.plant.p + K * innov          # the shaft moved with the finger (tendon engaged)
        self.P = (1 - K) * self.P
        return self.q


def vision_stream(q_true, rng, noise=0.03, fps_every=3, occlusion=0.5, burst=40):
    """Fake camera: every `fps_every` control ticks, noisy; hidden in bursts covering ~`occlusion` of the time."""
    T, J = q_true.shape
    z = q_true + rng.normal(0, noise, q_true.shape)
    hidden = np.zeros((T, J), bool)
    for j in range(J):
        k = 0
        while k < T:
            L = int(rng.integers(burst // 2, burst * 2))
            if rng.random() < occlusion:
                hidden[k:k + L, j] = True
            k += L
    mask = np.zeros((T, J), bool)
    mask[::fps_every] = True
    z[~mask | hidden] = np.nan
    return z
