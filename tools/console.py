"""Tiny serial console for the hand ESP32: type protocol commands, see replies. Ctrl+C to quit.

    .venv/Scripts/python tools/console.py COM5
    .venv/Scripts/python tools/console.py            # no port: talks to the fake ESP32 (practice mode)

Handy lines: V (version)  T (telemetry)  S 1 1500 (index servo to 1500 us)  E (stop)  R (resume)
Moves need a line at least every 200 ms or the watchdog turns outputs off - this console sends H for you
every 100 ms after your first move, so a servo you set stays set while you look at it.
"""
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hand.link import FakeTransport, SerialTransport  # noqa: E402
from hand import config  # noqa: E402


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else ""
    tr = SerialTransport(port, 115200) if port else FakeTransport(config.HandConfig())
    print(f"connected to {port or 'FAKE ESP32'} - type commands, Ctrl+C to quit")
    alive, moving = [True], [False]
    lock = threading.Lock()

    def pump():
        while alive[0]:
            with lock:
                if moving[0]:
                    tr.write("H\n")
                tr.advance(0.0 if port else 0.1)
                for ln in tr.lines():
                    if ln != "OK":
                        print("  <", ln)
            time.sleep(0.1)

    threading.Thread(target=pump, daemon=True).start()
    try:
        while True:
            cmd = input("> ").strip()
            if not cmd:
                continue
            with lock:
                tr.write(cmd + "\n")
                if cmd[0].upper() in "MS":
                    moving[0] = True
                if cmd[0].upper() == "E":
                    moving[0] = False
    except (KeyboardInterrupt, EOFError):
        alive[0] = False
        tr.write("E\n")
        print("\nsent E (outputs off). bye")


if __name__ == "__main__":
    main()
