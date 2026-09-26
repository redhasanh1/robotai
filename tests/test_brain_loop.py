import numpy as np
import pytest

from hand import brain, loop, memory, primitives, sysid
from hand.config import HandConfig
from hand.estimator import Estimator, vision_stream
from hand.plant import ServoPlant


def test_primitives_shapes():
    q = primitives.shape("pinch", 0.7, 0.9)
    assert q[0] == 0.9 and q[1] == 0.7 and q[2] == 0 and q[5] == 0
    assert primitives.shape("hook", 0.9, 0.9)[0] == 0          # hook never uses the thumb
    c = primitives.sample("power", 5, np.random.default_rng(0))
    assert len(c) == 5 and c[0]["s"] == primitives.DEFAULT_PARAMS["power"][0]


def test_memory_recall_and_prompt():
    m = memory.Memory()
    cand = primitives.sample("hook", 1, np.random.default_rng(0))[0]
    m.add("pick up the bar", "bar", cand, False, "slipped out when turned over")
    good = primitives.sample("power", 1, np.random.default_rng(0))[0]
    m.add("pick up the bar", "bar", good, True)
    assert m.best("bar")["family"] == "power"
    txt = m.as_prompt("grab the bar", "bar")
    assert "power" in txt and "HELD" in txt and "slipped" in txt


def test_stub_brain_learns_from_memory_text():
    b = brain.StubBrain()
    assert b.choose("", None, "No past attempts yet.", "bar")["family"] == "hook"
    txt = "- bar: hook s=0.90 t=0.00 -> DROPPED\n- bar: power s=0.85 t=1.00 -> HELD"
    assert b.choose("", None, txt, "bar")["family"] == "power"


def test_loop_selfcheck_and_veto_beat_blind_single_try():
    blind = [loop.attempt("pick up the bar", "bar", brain.StubBrain(), None, n=1, seed=s, verify=False).success
             for s in range(3)]
    smart = [loop.attempt("pick up the bar", "bar", brain.StubBrain(), memory.Memory(), n=8, seed=s).success
             for s in range(3)]
    assert sum(smart) > sum(blind)


def test_memory_never_sees_ground_truth_without_verifier():
    m = memory.Memory()
    loop.attempt("pick up the bar", "bar", brain.StubBrain(), m, n=1, seed=0, verify=False)
    assert m.stats() == {"episodes": 1, "successes": 1}          # it believes it worked; it did not


def test_sysid_recovers_parameters():
    servos = HandConfig().servos
    servos[1].v_max, servos[1].tau, servos[1].backlash = 2.6, 0.08, 0.05
    p = ServoPlant(servos)
    t, cmd = sysid.excite(1500)
    q = np.array([p.step(c, 0.01) for c in cmd]) + np.random.default_rng(1).normal(0, 0.005, (1500, 6))
    f = sysid.fit(t, cmd[:, 1], q[:, 1])
    assert f["v_max"] == pytest.approx(2.6, rel=0.15)
    assert f["tau"] == pytest.approx(0.08, rel=0.3)
    assert f["backlash"] == pytest.approx(0.05, abs=0.015)


def test_estimator_beats_camera_alone():
    rng = np.random.default_rng(0)
    t, cmd = sysid.excite(1500)
    p = ServoPlant()
    qt = np.array([p.step(c, 0.01) for c in cmd])
    z = vision_stream(qt, rng)
    est = Estimator()
    qe = []
    for k, c in enumerate(cmd):
        est.predict(c, 0.01)
        est.update(z[k])
        qe.append(est.q)
    held = z.copy()
    for k in range(1, len(held)):
        held[k] = np.where(np.isnan(held[k]), held[k - 1], held[k])
    err_est = np.sqrt(np.mean((np.array(qe) - qt) ** 2))
    err_cam = np.sqrt(np.mean((np.nan_to_num(held) - qt) ** 2))
    assert err_est < err_cam / 3
    assert np.all(est.std > 0)


def test_loop_drives_hardware_world_on_fake_board():
    from hand.hardware import HardwareWorld
    from hand.link import HandLink
    answers = iter(["", "", "n", "", "", "y", "", "", "y"])
    link = HandLink.open(port="")
    world = HardwareWorld(link, ask=lambda _p: next(answers))
    r = loop.attempt("pick up the can", "can", brain.StubBrain(), memory.Memory(), n=4, seed=0, world=world)
    assert r.success and r.tries == 2                    # "n" then "y": failed once, retried, held
    assert link.fake.state == "RUN" and link.q_cmd[1] < 0.3   # back at rest, watchdog never tripped


def test_habit_forms_after_successes_and_breaks_on_failure():
    from hand import habit
    m = memory.Memory()
    good = primitives.sample("power", 1, np.random.default_rng(0))[0]
    assert habit.lookup(m, "can") is None
    for _ in range(3):
        m.add("pick up the can", "can", good, True)
    h = habit.lookup(m, "can")
    assert h and h["family"] == "power" and h["n"] == 3
    m.add("pick up the can", "can", good, False)             # one fresh failure -> ask the model again
    assert habit.lookup(m, "can") is None


def test_habits_cut_model_calls_without_losing_success():
    counts = {}
    for use in (False, True):
        mem, b = memory.Memory(), brain.StubBrain()
        ok = 0
        for e in range(12):
            r = loop.attempt("pick up the can", "can", b, mem, n=4, seed=e, habits=use)
            ok += r.success
        counts[use] = (len(b.calls), ok)
    assert counts[True][0] < counts[False][0] and counts[True][1] >= counts[False][1] - 1


def test_recorder_writes_episode(tmp_path):
    from hand.recorder import Recorder
    rec = Recorder(str(tmp_path))
    ep = rec.start("pick up the ball", "ball", source="real")
    for k in range(10):
        ep.step(k * 0.02, [0.1 * k] * 6, [0.09 * k] * 6, image=np.zeros((24, 32, 3), np.uint8))
    ep.end(True, family="power", s=0.8, t_thumb=0.9)
    (path, meta), = rec.episodes()
    d = np.load(f"{path}/steps.npz")
    assert meta["success"] and meta["steps"] == 10 and d["action"].shape == (10, 6)
    assert len(list((tmp_path / "000000" / "frames").iterdir())) == 4          # every 3rd frame
