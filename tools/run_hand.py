"""Run the brain loop on the REAL hand (or the fake ESP32 to practise).

    .venv/Scripts/python tools/run_hand.py fake ball             # fake board, rule brain - practise the flow
    .venv/Scripts/python tools/run_hand.py COM5 ball             # real hand, rule brain
    $env:BRAIN="openai"; .venv/Scripts/python tools/run_hand.py COM5 ball --cam 0
                                                                 # real hand, real AI (BRAIN_URL / key), webcam

Physics predictions still come from the sim (the robot's imagination); the grasp itself runs on the hand. You
place the object and say whether it held. Every attempt goes into logs/memory.sqlite, so the robot's memory
carries over between sessions - that is the "learns with no training" part, on real hardware.
Ctrl+C stops and sends E (outputs off).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hand import brain, loop, memory  # noqa: E402
from hand.recorder import Recorder  # noqa: E402
from hand.hardware import HardwareWorld  # noqa: E402
from hand.link import HandLink  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("port")
    ap.add_argument("object")
    ap.add_argument("--cam", type=int, default=None)
    ap.add_argument("--n", type=int, default=8)
    a = ap.parse_args()
    link = HandLink.open(port="" if a.port == "fake" else a.port)
    world = HardwareWorld(link, camera=a.cam, recorder=Recorder(os.path.join(ROOT, "logs", "episodes")),
                          task=f"pick up the {a.object}", obj=a.object)   # every attempt saved for post-training
    b = brain.make(os.environ.get("BRAIN", "stub:instant"))
    mem = memory.Memory(os.path.join(ROOT, "logs", "memory.sqlite"))
    print(f"memory: {mem.stats()['episodes']} past attempts")
    try:
        r = loop.attempt(f"pick up the {a.object}", a.object, b, mem, n=a.n, world=world, render=a.cam is not None,
                     habits=True)
        for s in r.log:
            if s["step"] == "execute":
                print(f"  try {s['try']}: {s['cand']} -> {'HELD' if s['truth'] else 'dropped'}"
                      f" (robot thought: {'held' if s['believed'] else 'dropped'})")
            elif s["step"] in ("choose", "veto"):
                print(f"  {s['step']}: {s.get('family')} - {s.get('why', '')}")
        print(f"{'SUCCESS' if r.success else 'FAILED'} in {r.tries} tries; brain {r.brain_s:.1f} s")
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        link.estop()


if __name__ == "__main__":
    main()
