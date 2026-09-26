"""One place for every number that describes the physical hand.

Channels follow the PCA9685 outputs on the right-hand board. Flexion is 0.0 (open) .. 1.0 (closed) for fingers
and -1.0 .. 1.0 for the wrist. Pulse widths are microseconds; the defaults are a deliberately narrow, safe band
until tools/servo_calibrate.py measures the real ends of each servo (then they live in hand_calibration.json).

Servo physics defaults are the MG996R datasheet (0.17 s / 60 deg at 6 V, ~1 deg deadband). They are the
starting values of the grey-box model; tools/servo_calibrate.py and hand.sysid replace them with measured ones.
"""
import json
import os
from dataclasses import dataclass, field, asdict

FINGERS = ["thumb", "index", "middle", "ring", "pinky"]
JOINTS = FINGERS + ["wrist"]
N = len(JOINTS)

HERE = os.path.dirname(os.path.abspath(__file__))
CAL_PATH = os.path.join(os.path.dirname(HERE), "hand_calibration.json")


@dataclass
class Servo:
    name: str
    channel: int
    us_open: int = 1300           # pulse at flexion 0 (wrist: at -1)
    us_closed: int = 1700         # pulse at flexion 1 (wrist: at +1)
    travel_deg: float = 180.0     # servo shaft degrees between us 500 and 2500 (MG996R ~180)
    v_max: float = 3.5            # flexion units / s at no load  (0.17 s/60 deg over a ~120 deg stroke)
    tau: float = 0.05             # s, first-order lag of the servo's internal loop
    deadband: float = 0.01        # flexion units
    backlash: float = 0.03        # tendon slack, flexion units (makes open/close paths differ)
    load_slow: float = 0.6        # fraction of speed lost at stall load

    def lo(self):
        return -1.0 if self.name == "wrist" else 0.0

    def to_us(self, q):
        q = min(max(q, self.lo()), 1.0)
        f = (q - self.lo()) / (1.0 - self.lo())
        return int(round(self.us_open + f * (self.us_closed - self.us_open)))

    def from_us(self, us):
        f = (us - self.us_open) / float(self.us_closed - self.us_open)
        return self.lo() + f * (1.0 - self.lo())


@dataclass
class HandConfig:
    servos: list = field(default_factory=lambda: [Servo(n, i) for i, n in enumerate(JOINTS)])
    port: str = ""                # e.g. COM5; empty = fake ESP32
    baud: int = 115200
    heartbeat_s: float = 0.05     # laptop sends at least this often; firmware relaxes after 0.2 s of silence

    def servo(self, name):
        return next(s for s in self.servos if s.name == name)

    def save(self, path=CAL_PATH):
        with open(path, "w") as f:
            json.dump({"port": self.port, "baud": self.baud,
                       "servos": [asdict(s) for s in self.servos]}, f, indent=2)


def load(path=CAL_PATH):
    cfg = HandConfig()
    if os.path.exists(path):
        with open(path) as f:
            d = json.load(f)
        cfg.port, cfg.baud = d.get("port", ""), d.get("baud", 115200)
        cfg.servos = [Servo(**s) for s in d["servos"]]
    return cfg
