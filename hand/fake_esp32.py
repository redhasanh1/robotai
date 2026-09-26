"""A software ESP32 that speaks protocol v0.1 exactly like firmware/hand_esp32, driving a ServoPlant.

Everything above the serial line (laptop code, tests, sim, benchmarks) runs against this until the real board
is plugged in; then hand.link swaps it for a serial port and nothing else changes. It reproduces the firmware's
clamp, slew limit, staggered start, 200 ms watchdog and e-stop, so the safety behaviour can be tested here too.

Time is simulated: call advance(dt), or let it follow a clock function (default: none, fully deterministic).
"""
from collections import deque

import numpy as np

from . import config, protocol

WATCHDOG_S, STAGGER_S, TICK_S = 0.200, 0.150, 0.010


class FakeESP32:
    def __init__(self, cfg=None, plant=None):
        from .plant import ServoPlant
        self.cfg = cfg or config.HandConfig()
        self.plant = plant or ServoPlant(self.cfg.servos)
        self.t = 0.0
        self.lo = [1300] * protocol.NCH
        self.hi = [1700] * protocol.NCH
        self.slew = 1500.0
        self.cur = [0.0] * protocol.NCH
        self.target = [0] * protocol.NCH
        self.enable_at = [0.0] * protocol.NCH
        self.state = "IDLE"
        self.commanded = False
        self.last_rx = 0.0
        self.out = deque(["BOOT hand-esp32 " + protocol.VERSION])
        self.stop = None          # per-joint obstacle flexion (set by a scene), NaN = free

    # ---- serial-like interface ----
    def write(self, data):
        for line in data.split("\n"):
            if line.strip():
                self._handle(line)

    def readline(self):
        return (self.out.popleft() + "\n") if self.out else ""

    def lines(self):
        got = list(self.out)
        self.out.clear()
        return got

    # ---- the firmware, in Python ----
    def _stop_all(self, why):
        self.cur = [0.0] * protocol.NCH
        self.state = why

    def _start(self):
        k = 0
        for i in range(protocol.NCH):
            self.enable_at[i] = self.t + STAGGER_S * k if self.target[i] else 0.0
            k += bool(self.target[i])
        self.state = "RUN"

    def _handle(self, line):
        try:
            c, a = protocol.parse_command(line)
        except ValueError as e:
            self.out.append(f"ERR {e}")
            return
        self.last_rx = self.t
        if c == "V":
            self.out.append("OK V hand-esp32 " + protocol.VERSION)
        elif c == "T":
            self.out.append(f"TEL {int(self.t * 1000)} {self.state} " + " ".join(str(int(u + 0.5)) for u in self.cur))
        elif c == "E":
            self._stop_all("ESTOP")
            self.out.append("OK E")
        elif c == "R":
            if self.state in ("ESTOP", "WATCHDOG"):
                self._start()
            self.out.append("OK R")
        elif c == "W":
            self.slew = float(min(max(a[0], 50), 20000))
            self.out.append(f"OK W {int(self.slew)}")
        elif c == "L":
            ch, lo, hi = a
            if lo < 500 or hi > 2500 or lo >= hi:
                self.out.append("ERR bad limit")
                return
            self.lo[ch], self.hi[ch] = lo, hi
            self.out.append(f"OK L {ch} {lo} {hi}")
        elif c in ("S", "M"):
            pairs = [(a[0], a[1])] if c == "S" else [(i, u) for i, u in enumerate(a) if u > 0]
            for ch, us in pairs:
                self.target[ch] = int(min(max(us, self.lo[ch]), self.hi[ch]))
            self.commanded = True
            if self.state == "IDLE":
                self._start()
            self.out.append("OK" if self.state == "RUN" else f"ERR {self.state}, send R")

    def advance(self, dt):
        """Run the firmware tick loop and the physics for dt seconds."""
        end = self.t + dt
        while self.t < end - 1e-12:
            h = min(TICK_S, end - self.t)
            self.t += h
            if self.state == "RUN" and self.commanded and self.t - self.last_rx > WATCHDOG_S:
                self._stop_all("WATCHDOG")
                self.out.append("ERR WATCHDOG no command for 200 ms, outputs off, send R")
            if self.state == "RUN":
                step = self.slew * h
                for i in range(protocol.NCH):
                    if not self.target[i] or (self.enable_at[i] and self.t < self.enable_at[i]):
                        continue
                    c, tg = self.cur[i], self.target[i]
                    self.cur[i] = tg if c == 0 else (min(c + step, tg) if c < tg else max(c - step, tg))
            self.plant.step(self.shaft_cmd(), h, stop=self.stop)

    def shaft_cmd(self):
        """What each servo is being told, in flexion units. A limp servo (no pulse) just keeps its position."""
        return np.array([s.from_us(u) if u > 0 else self.plant.p[i]
                         for i, (s, u) in enumerate(zip(self.cfg.servos, self.cur))])

    @property
    def q_true(self):
        return self.plant.q.copy()
