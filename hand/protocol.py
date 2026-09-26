"""Laptop <-> ESP32 serial protocol v0.1. Plain text lines so it can be typed by hand in a serial monitor.

Laptop -> ESP32 (one command per line, '\n' terminated):
    V                      version            -> "OK V hand-esp32 0.1"
    H                      heartbeat          -> nothing (any valid command also counts as a heartbeat)
    M us0 us1 .. us5       move all channels to these pulse widths (0 = leave that channel alone)
    S ch us                move one channel
    L ch min max           set the safety clamp for a channel (saved in flash)
    W us_per_s             slew limit, how fast a pulse may change (saved in flash)
    E                      e-stop: outputs off (servos go limp) until R
    R                      resume after an e-stop or watchdog trip
    T                      telemetry          -> "TEL ms state us0 .. us5"

ESP32 -> laptop:
    OK ...                 command accepted
    ERR <reason>           command rejected (bad syntax, channel out of range, ...)
    TEL ms state us0..us5  state = RUN | ESTOP | WATCHDOG | IDLE; us = where the slew limiter is now
    BOOT hand-esp32 0.1    printed once at power-up

Safety lives in the firmware, not here: the clamp, the slew limit and the 200 ms watchdog all run on the ESP32
whether or not the laptop is sane. This module only formats and parses lines.
"""
VERSION = "0.1"
NCH = 6
STATES = ("RUN", "ESTOP", "WATCHDOG", "IDLE")


def move(us):
    assert len(us) == NCH
    return "M " + " ".join(str(int(u)) for u in us) + "\n"


def set_one(ch, us):
    return f"S {int(ch)} {int(us)}\n"


def limit(ch, lo, hi):
    return f"L {int(ch)} {int(lo)} {int(hi)}\n"


def slew(us_per_s):
    return f"W {int(us_per_s)}\n"


HEARTBEAT, ESTOP, RESUME, TELEMETRY, VERSION_Q = "H\n", "E\n", "R\n", "T\n", "V\n"


def parse_reply(line):
    """-> (kind, payload). kind is OK, ERR, TEL, BOOT or '?'."""
    parts = line.strip().split()
    if not parts:
        return "?", None
    k = parts[0]
    if k == "TEL" and len(parts) == 3 + NCH:
        return "TEL", {"ms": int(parts[1]), "state": parts[2], "us": [int(x) for x in parts[3:]]}
    if k in ("OK", "ERR", "BOOT"):
        return k, " ".join(parts[1:])
    return "?", line.strip()


def parse_command(line):
    """Used by the fake ESP32 (and mirrors the firmware parser). -> (cmd, args) or raises ValueError."""
    parts = line.strip().split()
    if not parts:
        raise ValueError("empty")
    c, a = parts[0], parts[1:]
    try:
        nums = [int(x) for x in a]
    except ValueError:
        raise ValueError("not a number")
    want = {"V": 0, "H": 0, "E": 0, "R": 0, "T": 0, "M": NCH, "S": 2, "L": 3, "W": 1}
    if c not in want:
        raise ValueError("unknown command")
    if len(nums) != want[c]:
        raise ValueError("wrong argument count")
    if c in ("S", "L") and not 0 <= nums[0] < NCH:
        raise ValueError("bad channel")
    return c, nums
