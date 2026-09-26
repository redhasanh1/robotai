"""NVIDIA MuJoCo Warp: every grasp candidate as its own world, all simulated at once on the GPU.

Same MJCF as hand/sim.py (the CPU MuJoCo model is the reference; Kimi round 2: one-world CPU parity check before
trusting batches). Runs on the GTX 1660 Ti (CUDA sm_75 - Warp needs CUDA, not RTX) and unchanged on a rented GPU.

    from hand.gpu_sim import BatchGrasp
    bg = BatchGrasp("ball", nworld=64)
    results = bg.evaluate(list_of_6_flexion_vectors)      # -> [{"held", "dist"}, ...] one per candidate

The grasp test is the same as SimHand.grasp_test: close 0.8 s through the servo rate model, flip gravity,
shake +-3 m/s^2 sideways, held if the object ends within 7.5 cm of the palm.
"""
import numpy as np
import mujoco

from . import config, sim
from .plant import ServoPlant


class BatchGrasp:
    def __init__(self, obj="ball", nworld=64):
        import warp as wp
        import mujoco_warp as mjw
        self.wp, self.mjw = wp, mjw
        self.obj, self.nworld = obj, nworld
        ref = sim.SimHand(obj)                       # settled start state, identical to the CPU sim
        self.mjm, self.mjd0 = ref.model, ref.data
        self.m = mjw.put_model(self.mjm)
        self.act = ref.act
        self.scale = ref.scale(np.ones(config.N))
        self.dt = self.mjm.opt.timestep
        self.obj_body = self.mjm.body("object").id
        self.hand_body = self.mjm.body("hand").id
        self._graphs, self._data = {}, {}

    def _gravity(self, g):
        self.m.opt.gravity.assign(np.array([g], np.float32))    # warp array of one vec3, shared by all worlds

    def _block(self, d, k):
        """k physics steps as one CUDA graph (captured once per data object, replayed after) - removes the
        per-step Python/launch overhead that made the first version 8.4 s for 16 worlds."""
        wp, mjw = self.wp, self.mjw
        key = (id(d), k)
        if key not in self._graphs:
            mjw.step(self.m, d)                      # warm-up: compile kernels outside the capture
            with wp.ScopedCapture() as cap:
                for _ in range(k):
                    mjw.step(self.m, d)
            self._graphs[key] = cap.graph
        wp.capture_launch(self._graphs[key])

    def evaluate(self, qs, close_s=0.8, hold_s=0.8, ctrl_hz=50):
        """Servo targets update at ctrl_hz (the ESP32 runs at 100 Hz; 50 Hz is plenty for the lag model),
        physics steps in between run as a replayed CUDA graph."""
        mjw = self.mjw
        qs = np.asarray(qs, float)
        n = len(qs)
        if n not in self._data:
            self._data[n] = mjw.put_data(self.mjm, self.mjd0, nworld=n)
        d = self._data[n]
        fresh = mjw.put_data(self.mjm, self.mjd0, nworld=n)
        for name in ("qpos", "qvel", "act", "ctrl", "time"):
            getattr(d, name).assign(getattr(fresh, name))
        mjw.forward(self.m, d)
        servo = ServoPlant()
        servo.p = np.zeros((n, config.N))
        servo.q = np.zeros((n, config.N))
        ctrl = np.zeros((n, self.mjm.nu), np.float32)
        k = max(1, int(round(1.0 / ctrl_hz / self.dt)))
        self._gravity((0, 0, -9.81))
        for _ in range(int(round(close_s * ctrl_hz))):
            servo.step(qs, k * self.dt)
            ctrl[:, self.act] = servo.q * self.scale
            d.ctrl.assign(ctrl)
            self._block(d, k)
        for g in [(0, 3.0, 9.81), (0, -3.0, 9.81), (0, 3.0, 9.81), (0, -3.0, 9.81)]:
            self._gravity(g)
            for _ in range(int(round(hold_s / 4 * ctrl_hz))):
                self._block(d, k)
        xpos = d.xpos.numpy()                        # (n, nbody, 3)
        dist = np.linalg.norm(xpos[:, self.obj_body] - xpos[:, self.hand_body], axis=1)
        return [{"held": bool(x < 0.075), "dist": round(float(x), 4)} for x in dist]
