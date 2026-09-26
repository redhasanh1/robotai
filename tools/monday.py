"""Monday bring-up, guided: one command walks through everything in the right order and stops at each step.

    .venv/Scripts/python tools/monday.py                 # right hand (default)
    .venv/Scripts/python tools/monday.py --side left     # second hand, second board
    .venv/Scripts/python tools/monday.py --from 4        # skip ahead (e.g. after a break)

Steps (each asks before it runs; Enter = go, s = skip, q = quit):
  1 find the ESP32's COM port (drivers: setup/drivers.md)
  2 flash the firmware, check the BOOT line (reset=BROWNOUT means the supply sagged, not a bug)
  3 measure the USB link and set the watchdog from it
  4 SAFETY CHECK - PSU at 6.0 V on its display, 2200 uF cap stripe to GND, grounds tied, nothing left powered alone
  5 servo DOA sweep, all six channels, no horns or tendons
  6 range: per channel, find OPEN and CLOSED (mark CLOSED a little short - results/tendon.md)
  7 speed: per channel, horn marker + webcam -> v_max / tau into the calibration file
Everything it measures lands in hand_calibration*.json and logs/, same as running the tools by hand.
"""
import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
CHANNELS = ["thumb", "index", "middle", "ring", "pinky", "wrist"]


def ask(msg):
    r = input(f"\n{msg}\n  [Enter] go   [s] skip   [q] quit > ").strip().lower()
    if r == "q":
        sys.exit("stopped - run again with --from <step> to continue")
    return r != "s"


def run(*args):
    print("  $", " ".join(args), flush=True)
    return subprocess.run([PY, *args], cwd=ROOT).returncode == 0


def find_port():
    try:
        import serial.tools.list_ports as lp
    except ImportError:
        return ""
    ports = [p for p in lp.comports() if "Bluetooth" not in (p.description or "")]
    for p in ports:
        print(f"  {p.device}: {p.description}")
    # only a USB-serial chip counts: the fallback used to pick COM1, the motherboard's own port
    esp = [p.device for p in ports if any(k in (p.description or "") for k in ("CH340", "CH343", "CP210", "USB Serial",
                                                                               "USB-SERIAL", "UART"))]
    return esp[0] if esp else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--side", default="right", choices=("right", "left"))
    ap.add_argument("--from", dest="start", type=int, default=1)
    ap.add_argument("--port", default="")
    a = ap.parse_args()
    side = ["--side", a.side]
    port = a.port
    print(f"Monday bring-up - {a.side} hand. Ctrl+C at any point stops the servos (tools send E).")

    if a.start <= 1 and ask("1/7 Plug the ESP32 in with a DATA cable. Find its COM port?"):
        port = find_port() or port
        print(f"  -> using {port or 'nothing found - see setup/drivers.md'}")
        if not port:
            sys.exit("no COM port - install the CH340 driver (setup/drivers.md), replug, run again")
    port = port or input("COM port (e.g. COM5): ").strip()

    if a.start <= 2 and ask("2/7 Flash the firmware (hold BOOT if it sticks at Connecting...)?"):
        subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", os.path.join(ROOT, "setup", "flash.ps1"),
                        "-Port", port], cwd=ROOT)
    if a.start <= 3 and ask("3/7 Measure the USB link and set the watchdog?"):
        run("tools/link_jitter.py", port, "--apply")
    if a.start <= 4:
        print("\n4/7 SAFETY - check every line before any servo is connected:")
        for line in ("power supply reads 6.0 V on its display", "2200 uF capacitor across PCA9685 V+/GND, stripe to GND",
                     "supply GND and ESP32 GND connected", "PCA9685: VCC->3V3, GND, SDA->21, SCL->22, OE->25",
                     "you will not leave it powered while you are away (no fuse on this build)"):
            if input(f"  [ ] {line}  - ok? (y/n) ").strip().lower() != "y":
                sys.exit("fix that first, then: tools/monday.py --from 4")
    if a.start <= 5 and ask("5/7 Servo DOA sweep - no horns, no tendons. It asks you to plug each servo in turn."):
        run("tools/servo_bench.py", "doa", port, *side)
    if a.start <= 6:
        for ch, name in enumerate(CHANNELS):
            if ask(f"6/7 Range for channel {ch} ({name}) - horn on. Mark CLOSED a little short of fully closed."):
                run("tools/servo_bench.py", "range", port, str(ch), *side)
    if a.start <= 7:
        print("\n7/7 Speed curves need the horn marker: tools/vision.py markers writes the sheet; marker id 20 is in "
              "logs/horn_marker.png once servo_characterize has run once.")
        for ch, name in enumerate(CHANNELS):
            if ask(f"7/7 Measure channel {ch} ({name}) with the webcam on the horn marker?"):
                run("tools/servo_characterize.py", port, str(ch), "--side", a.side)
    print("\nDone. Calibration: hand_calibration.json (right) / hand_calibration_left.json (left); curves: "
          "logs/servo_curves.jsonl. Next: tools/run_hand.py when the printed hand is assembled.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nstopped")
