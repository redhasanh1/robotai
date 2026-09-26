"""Protocol, fake ESP32 safety behaviour and the laptop link. Run: .venv/Scripts/python -m pytest tests"""
import numpy as np
import pytest

from hand import config, protocol
from hand.fake_esp32 import FakeESP32
from hand.link import HandLink
from hand.plant import ServoPlant


def test_protocol_roundtrip():
    assert protocol.move([1500] * 6) == "M 1500 1500 1500 1500 1500 1500\n"
    assert protocol.parse_command("S 3 1600") == ("S", [3, 1600])
    k, t = protocol.parse_reply("TEL 1234 RUN 1500 0 1500 1500 1500 1500")
    assert k == "TEL" and t["state"] == "RUN" and t["us"][1] == 0
    for bad in ["S 9 1500", "M 1 2", "X", "S a b", ""]:
        with pytest.raises(ValueError):
            protocol.parse_command(bad)


def test_clamp_and_slew():
    d = FakeESP32()
    d.write("M 2400 0 0 0 0 0\n")          # far outside the default 1300..1700 clamp
    d.advance(0.01)
    assert d.target[0] == 1700 and d.cur[0] == 1700      # first pulse jumps (no feedback), then slews
    d.write("M 1300 0 0 0 0 0\n")
    d.advance(0.1)                          # 1500 us/s * 0.1 s = 150 us of travel
    assert d.cur[0] == pytest.approx(1550, abs=16)


def test_watchdog_and_resume():
    d = FakeESP32()
    d.write("M 1500 1500 1500 1500 1500 1500\n")
    d.advance(0.15)
    assert d.state == "RUN"
    d.advance(0.1)                          # 250 ms since last command
    assert d.state == "WATCHDOG" and all(c == 0 for c in d.cur)
    d.write("M 1600 0 0 0 0 0\n")
    assert d.lines()[-1].startswith("ERR WATCHDOG")      # moves refused until R
    d.write("R\n")
    d.advance(0.05)
    assert d.state == "RUN"


def test_estop():
    d = FakeESP32()
    d.write("M 1500 1500 1500 1500 1500 1500\n")
    d.write("E\n")
    assert d.state == "ESTOP"
    d.advance(0.05)
    assert all(c == 0 for c in d.cur)


def test_staggered_start():
    d = FakeESP32()
    d.write("M 1500 1500 1500 0 0 0\n")
    d.advance(0.01)
    assert [c > 0 for c in d.cur[:3]] == [True, False, False]
    d.write("H\n")
    d.advance(0.15)
    assert [c > 0 for c in d.cur[:3]] == [True, True, False]


def test_link_moves_fake_hand():
    link = HandLink.open(port="")
    link.move([0.0, 1.0, 1.0, 0.0, 0.0, 0.0])
    link.wait(1.5)
    q = link.fake.q_true
    assert q[1] > 0.9 and q[2] > 0.9 and q[3] < 0.05
    t = link.telemetry()
    assert t["state"] == "RUN" and t["q_cmd"][1] == pytest.approx(1.0, abs=0.01)
    assert link.version() == "V hand-esp32 " + protocol.VERSION


def test_plant_backlash_and_rate_limit():
    p = ServoPlant()
    p.step([1, 0, 0, 0, 0, 0], 0.1)
    s = config.HandConfig().servos[0]
    assert p.p[0] <= s.v_max * 0.1 + 1e-9                 # speed limit respected
    p.reset()
    up = p.rollout(np.zeros(6), np.zeros(6), [[0.5] * 6] * 100, 0.01)[-1, 0]
    p.reset(np.full(6, 1.0))
    down = p.rollout(np.ones(6), np.ones(6), [[0.5] * 6] * 100, 0.01)[-1, 0]
    assert up < 0.5 < down and down - up == pytest.approx(s.backlash + 2 * s.deadband, abs=0.005)   # slack + deadband hysteresis


def test_heartbeat_thread_keeps_real_board_alive(monkeypatch):
    """A blocked program (e.g. waiting for keyboard input) must not let the watchdog trip on real hardware."""
    import time as _t
    from hand import link as L

    class FakeSerial(L.SerialTransport):
        def __init__(self):
            self.dev = FakeESP32()
            self.t0 = _t.monotonic()

        def write(self, data):
            self.dev.advance(max(0.0, _t.monotonic() - self.t0 - self.dev.t))   # device clock = wall clock
            self.dev.write(data)

        def lines(self):
            return self.dev.lines()

        def advance(self, dt):
            _t.sleep(dt)

    tr = FakeSerial()
    link = L.HandLink(tr, config.HandConfig())
    link.move([0, 0.5, 0, 0, 0, 0])
    _t.sleep(0.6)                                  # "blocked" 3x longer than the watchdog timeout
    tr.write("H\n")
    assert tr.dev.state == "RUN"
    link.close()
