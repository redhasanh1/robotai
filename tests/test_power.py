import numpy as np

from hand import power, primitives
from hand.guard import SqueezeGuard


def test_free_close_is_cheap_and_squeeze_overloads_without_guard():
    s = power.scenarios()
    assert s["close on nothing | 1 hand"]["peak_a"] < 3
    assert s["close on a can and squeeze | 1 hand"]["mean_a"] > power.SUPPLY_A * 0.8     # the problem it found


def test_squeeze_guard_halves_the_current_and_keeps_a_hold():
    close = np.array([primitives.shape("power", 0.9, 0.9)] * 150)
    stop = np.array([0.55, 0.6, 0.6, 0.6, 0.6, np.nan])
    bare = power.simulate(close, stop=stop)
    guarded = power.simulate(close, stop=stop, guard_cls=SqueezeGuard)
    assert guarded["mean_a"] < bare["mean_a"] / 2
    assert guarded["seconds_over_limit"] < 0.3
    g = SqueezeGuard()
    q = np.array([0.55, 0.6, 0.6, 0.6, 0.6, 0.0])
    for _ in range(30):
        cmd = g.update(close[0], q, 0.01)
    assert np.all(cmd[:5] > q[:5]) and np.all(cmd[:5] <= q[:5] + 0.041)     # still pushing, but gently
