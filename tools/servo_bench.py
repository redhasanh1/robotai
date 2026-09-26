"""Monday bench session: test every servo, find its safe range, save the calibration.

    .venv/Scripts/python tools/servo_bench.py doa COM5          # dead-on-arrival test, one channel at a time
    .venv/Scripts/python tools/servo_bench.py range COM5 1      # find channel 1's usable pulse range by hand
    .venv/Scripts/python tools/servo_bench.py show              # print hand_calibration.json
    add --side left to any of these for the second hand (its own board and calibration file)

BEFORE ANYTHING: power supply set to 6.0 V on its display, 2200 uF cap across PCA9685 V+/GND (stripe to GND),
ESP32 GND tied to supply GND, servos WITHOUT horns/tendons attached for the DOA test. Never leave it powered
unattended (no fuse on this build). Ctrl+C at any point sends E (all outputs off).

doa:   for each of the 6 channels in turn, sweeps 1300 -> 1700 -> 1500 us slowly. Plug the servo under test into
       that channel when asked. You watch and answer y/n: did it move smoothly and quietly? Buzzing, stalling,
       jitter or no movement = n -> set it aside for return (Amazon window).
range: nudges one channel with the keyboard (a/d = -/+ 10 us, A/D = 50 us). Put the horn on, find where the
       finger is fully OPEN and fully CLOSED without the servo straining (listen: straining hums), press o / c
       to record each, q to save. Those become the firmware clamp - the servo can never be driven past them.
       With tendons on: mark CLOSED a little SHORT of fully closed. The tendon model (results/tendon.md) has the
       servo at 73% of stall at 90% closure and stalling ~0.2 rad (~12 deg, ~130 us) later, where the line starts
       fighting the finger's end stops. If it hums at your CLOSED mark, back off 50-100 us.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hand import config, protocol  # noqa: E402
from hand.link import FakeTransport, SerialTransport  # noqa: E402


def open_port(port):
    if port in ("", "fake"):
        print("(fake ESP32 - practice run)")
        return FakeTransport(config.HandConfig())
    return SerialTransport(port, 115200)


def hold(tr, seconds, dt=0.05):
    """Keep the watchdog fed while waiting."""
    end = time.time() + seconds
    while time.time() < end:
        tr.write(protocol.HEARTBEAT)
        tr.advance(dt) if isinstance(tr, FakeTransport) else time.sleep(dt)
        for ln in tr.lines():
            if ln.startswith("ERR"):
                print("  !", ln)


def sweep(tr, ch, a, b, seconds):
    steps = max(1, int(seconds / 0.05))
    for k in range(steps + 1):
        us = int(a + (b - a) * k / steps)
        tr.write(protocol.set_one(ch, us))
        hold(tr, 0.05)


def doa(port):
    tr = open_port(port)
    tr.write(protocol.slew(600))            # gentle
    results = {}
    try:
        for ch, name in enumerate(config.JOINTS):
            input(f"\nPlug a servo into channel {ch} ({name}) and press Enter...")
            tr.write(protocol.RESUME)
            sweep(tr, ch, 1500, 1300, 1.0)
            sweep(tr, ch, 1300, 1700, 2.0)
            sweep(tr, ch, 1700, 1500, 1.0)
            tr.write(protocol.ESTOP)
            ok = input("Smooth and quiet the whole way? [y/n] ").strip().lower().startswith("y")
            results[name] = ok
            print("  ->", "OK" if ok else "SET ASIDE FOR RETURN")
    finally:
        tr.write(protocol.ESTOP)
    print("\nDOA:", results)
    bad = [k for k, v in results.items() if not v]
    print("all good" if not bad else f"return these: {bad}")


def getch():
    try:
        import msvcrt
        return msvcrt.getwch()
    except ImportError:
        return input()[:1]


def find_range(port, ch, side="right"):
    cfg = config.load(side=side)
    s = cfg.servos[ch]
    tr = open_port(port)
    tr.write(protocol.limit(ch, 600, 2400))   # wide clamp only while YOU are driving it by hand
    tr.write(protocol.slew(400))
    us = 1500
    print(f"channel {ch} ({s.name}): a/d = -/+10 us, A/D = -/+50 us, o = mark OPEN, c = mark CLOSED, q = save, x = abort")
    print("  tip: mark CLOSED slightly before fully closed - if the servo hums there, back off 50-100 us")
    try:
        while True:
            tr.write(protocol.set_one(ch, us))
            hold(tr, 0.05)
            print(f"\r  {us} us   open={s.us_open} closed={s.us_closed}   ", end="", flush=True)
            k = getch()
            us += {"a": -10, "d": 10, "A": -50, "D": 50}.get(k, 0)
            us = max(600, min(2400, us))
            if k == "o":
                s.us_open = us
            elif k == "c":
                s.us_closed = us
            elif k == "q":
                cfg.save()
                lo, hi = sorted((s.us_open, s.us_closed))
                tr.write(protocol.limit(ch, lo, hi))
                print(f"\nsaved to {config.cal_path(side)}; firmware clamp for ch{ch} now {lo}..{hi}")
                return
            elif k == "x":
                print("\naborted, nothing saved")
                return
    finally:
        tr.write(protocol.ESTOP)


def main():
    side = "right"
    if "--side" in sys.argv:                          # --side left for the second hand's board
        i = sys.argv.index("--side")
        side = sys.argv[i + 1]
        del sys.argv[i:i + 2]
    if len(sys.argv) < 2 or sys.argv[1] not in ("doa", "range", "show"):
        print(__doc__)
        return
    if sys.argv[1] == "show":
        for s in config.load(side=side).servos:
            print(f"ch{s.channel} {s.name:7s} open {s.us_open} us  closed {s.us_closed} us  v_max {s.v_max}  tau {s.tau}")
        return
    port = sys.argv[2] if len(sys.argv) > 2 else ""
    try:
        if sys.argv[1] == "doa":
            doa(port)
        else:
            find_range(port, int(sys.argv[3]), side)
    except KeyboardInterrupt:
        print("\nstopped (E sent)")


if __name__ == "__main__":
    main()
