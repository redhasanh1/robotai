"""NVIDIA MuJoCo Warp batch vs the CPU reference (skipped without CUDA + mujoco_warp)."""
import numpy as np
import pytest

warp = pytest.importorskip("warp")
pytest.importorskip("mujoco_warp")
if not warp.is_cuda_available():
    pytest.skip("no CUDA GPU", allow_module_level=True)

from hand import sim  # noqa: E402
from hand.gpu_sim import BatchGrasp  # noqa: E402


def test_gpu_batch_matches_cpu_reference():
    rng = np.random.default_rng(0)
    qs = [np.r_[rng.uniform(0, 1, 5), 0] for _ in range(16)]
    gpu = BatchGrasp("can", 16).evaluate(qs)
    cpu = [sim.evaluate(q, "can") for q in qs]
    agree = sum(g["held"] == c["held"] for g, c in zip(gpu, cpu))
    assert agree >= 14            # 50 Hz servo updates on GPU vs 500 Hz on CPU: 15/16 measured
