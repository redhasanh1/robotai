"""Measure the real USB-serial round trip before trusting the 200 ms watchdog (Kimi round 5: real links have
10-100 ms spikes; tune the timeout on data, not on the simulator).

    .venv/Scripts/python tools/link_jitter.py COM5            # 500 round trips, prints percentiles + advice
    .venv/Scripts/python tools/link_jitter.py COM5 --apply    # also sets the firmware watchdog (D command)
    .venv/Scripts/python tools/link_jitter.py fake            # practice

Round trip = send "T", wait for the TEL reply. The heartbeat has to arrive within the watchdog timeout even on
the worst spike, so the advice is: timeout = max(200, 3 x worst observed + 50) ms, rounded up to 50.
"""
import argparse
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hand import config, protocol  # noqa: E402
from hand.link import FakeTransport, SerialTransport  # noqa: E402


def measure(tr, n=500):
    rts = []
    for _ in range(n):
        t0 = time.perf_counter()
        tr.write(protocol.TELEMETRY)
        got = False
        while time.perf_counter() - t0 < 2.0:
            if any(ln.startswith("TEL") for ln in tr.lines()):
                got = True
                break
            tr.advance(0.0005)
        if got:
            rts.append((time.perf_counter() - t0) * 1000)
    return rts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("port")
    ap.add_argument("-n", type=int, default=500)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    tr = FakeTransport(config.HandConfig()) if a.port == "fake" else SerialTransport(a.port, 115200)
    rts = measure(tr, a.n)
    if not rts:
        sys.exit("no replies - is the firmware flashed? (setup/flash.ps1)")
    q = lambda p: sorted(rts)[min(len(rts) - 1, int(p * len(rts)))]
    worst = max(rts)
    advice = max(200, int(-(-(3 * worst + 50) // 50) * 50))
    print(f"{len(rts)}/{a.n} replies  median {statistics.median(rts):.1f} ms  p99 {q(0.99):.1f} ms  "
          f"worst {worst:.1f} ms")
    print(f"advice: watchdog {advice} ms" + ("  (default 200 is fine)" if advice == 200 else ""))
    if a.apply:
        tr.write(protocol.watchdog(advice))
        time.sleep(0.2)
        print("firmware:", tr.lines())


if __name__ == "__main__":
    main()
