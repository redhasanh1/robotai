"""The laptop's handle on the hand: same API whether it is the real ESP32 on a COM port or the fake one.

    link = HandLink.open()           # fake ESP32 (no port configured)
    link = HandLink.open("COM5")     # real board
    link.move([0.2, 0.5, 0.5, 0.5, 0.5, 0.0])   # flexion per joint, order = config.JOINTS
    link.tick()                      # call often (>= 20 Hz); it is also the heartbeat the watchdog wants
    link.telemetry()                 # -> {"ms", "state", "us", "q_cmd"}

For the fake board time only moves when you call tick(dt) or wait(seconds), which keeps tests and benchmarks
deterministic. For the real board tick() just sends the heartbeat and reads replies.
"""
import threading
import time

from . import config, protocol
from .fake_esp32 import FakeESP32


class SerialTransport:
    def __init__(self, port, baud):
        import serial   # pyserial, only needed with real hardware
        self.s = serial.Serial(port, baud, timeout=0.05)
        time.sleep(1.5)            # ESP32 resets when the port opens; wait for BOOT
        self.s.reset_input_buffer()

    def write(self, data):
        self.s.write(data.encode())

    def lines(self):
        got = []
        while self.s.in_waiting:
            got.append(self.s.readline().decode(errors="replace").strip())
        return [g for g in got if g]

    def advance(self, dt):
        time.sleep(dt)


class FakeTransport:
    def __init__(self, cfg):
        self.dev = FakeESP32(cfg)

    def write(self, data):
        self.dev.write(data)

    def lines(self):
        return self.dev.lines()

    def advance(self, dt):
        self.dev.advance(dt)


class HandLink:
    def __init__(self, transport, cfg):
        self.tr, self.cfg = transport, cfg
        self.q_cmd = [0.0] * len(cfg.servos)   # fingers open, wrist centred
        self.log = []               # replies not consumed by a query (ERR WATCHDOG etc.)
        self._lock = threading.RLock()
        self._moved = False
        self._alive = True
        if isinstance(transport, SerialTransport):
            # Real board: a background heartbeat keeps the 200 ms watchdog fed even while the program is blocked
            # (waiting for you to type y/n, loading a model, thinking). Without it the hand goes limp mid-grasp -
            # the fake board could not show this because its clock only moves when the code moves it.
            threading.Thread(target=self._heartbeat, daemon=True).start()

    def _heartbeat(self):
        while self._alive:
            if self._moved:
                with self._lock:
                    self.tr.write(protocol.move([s.to_us(v) for s, v in zip(self.cfg.servos, self.q_cmd)]))
                    self.log.extend(self.tr.lines())
            time.sleep(self.cfg.heartbeat_s)

    def close(self):
        self._alive = False
        self.estop()

    @classmethod
    def open(cls, port=None, cfg=None, side="right"):
        """side picks the calibration file AND is checked against the name stored on the board, so the left
        hand's board can never be driven with the right hand's limits. An unnamed board is named on first use."""
        cfg = cfg or config.load(side=side)
        port = port if port is not None else cfg.port
        tr = SerialTransport(port, cfg.baud) if port else FakeTransport(cfg)
        link = cls(tr, cfg)
        on_board = link._query(protocol.side(), "OK").split()[-1]
        if on_board == "unset":
            link._query(protocol.side(cfg.side), "OK")
        elif on_board != cfg.side:
            link.close()
            raise RuntimeError(f"this board is the {on_board} hand, not the {cfg.side} hand - wrong COM port? "
                               f"(or re-name it: tools/console.py {port or ''} then type N 1 / N 2)")
        link.push_limits()
        return link

    @property
    def fake(self):
        return self.tr.dev if isinstance(self.tr, FakeTransport) else None

    def _send(self, text):
        with self._lock:
            self.tr.write(text)

    def _query(self, text, kind):
        self._send(text)
        for _ in range(40):
            with self._lock:
                got = self.tr.lines()
            for ln in got:
                k, payload = protocol.parse_reply(ln)
                if k == kind:
                    return payload
                self.log.append(ln)
            self.tr.advance(0.005)
        raise TimeoutError(f"no {kind} reply to {text.strip()!r}")

    def push_limits(self):
        """Send each channel's calibrated pulse range as the firmware's hard clamp."""
        for s in self.cfg.servos:
            lo, hi = sorted((s.us_open, s.us_closed))
            self._send(protocol.limit(s.channel, lo, hi))
        self.tr.lines()

    def move(self, q):
        self.q_cmd = list(q)
        us = [s.to_us(v) for s, v in zip(self.cfg.servos, q)]
        self._send(protocol.move(us))
        self._moved = True

    def tick(self, dt=0.02):
        """Heartbeat: re-send the current target (idempotent) and let time pass."""
        self._send(protocol.move([s.to_us(v) for s, v in zip(self.cfg.servos, self.q_cmd)]))
        self.tr.advance(dt)
        self.log.extend(self.tr.lines())

    def wait(self, seconds, dt=0.02):
        for _ in range(max(1, int(round(seconds / dt)))):
            self.tick(dt)

    def estop(self):
        self._moved = False          # stop the heartbeat re-sending moves (the firmware would refuse them anyway)
        self._send(protocol.ESTOP)

    def resume(self):
        self._send(protocol.RESUME)

    def telemetry(self):
        t = self._query(protocol.TELEMETRY, "TEL")
        t["q_cmd"] = [s.from_us(u) if u else None for s, u in zip(self.cfg.servos, t["us"])]
        return t

    def version(self):
        return self._query(protocol.VERSION_Q, "OK")
