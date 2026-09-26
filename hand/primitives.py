"""Grasp primitives: a few named hand shapes with 2 knobs each. The brain chooses the family (semantics - what
kind of grasp suits a ball vs a pen), local sampling fills in the numbers, physics checks them.

Flexion order is config.JOINTS: thumb, index, middle, ring, pinky, wrist.
    s = how far the fingers close (0..1), t = how far the thumb closes (0..1)
"""
import numpy as np

FAMILIES = {
    #            which fingers close        thumb?   note for the brain
    "power":    ((1, 1, 1, 1),              True,    "whole hand wraps the object: balls, cans, bottles"),
    "tripod":   ((1, 1, 0, 0),              True,    "thumb + index + middle: small round things, caps"),
    "pinch":    ((1, 0, 0, 0),              True,    "thumb + index tips: small or thin things"),
    "hook":     ((1, 1, 1, 1),              False,   "fingers only, no thumb: handles, bags, bars"),
    "lateral":  ((1, 1, 1, 1),              True,    "fingers curled, thumb presses from the side: flat or long things"),
}
DEFAULT_PARAMS = {"power": (0.85, 0.9), "tripod": (0.75, 0.9), "pinch": (0.7, 0.9), "hook": (0.9, 0.0),
                  "lateral": (0.95, 0.6)}
OPEN = np.zeros(6)
REST = np.array([0.15, 0.2, 0.2, 0.2, 0.2, 0.0])


def shape(family, s, t, wrist=0.0):
    fingers, thumb = FAMILIES[family][0], FAMILIES[family][1]
    q = np.zeros(6)
    q[0] = t if thumb else 0.0
    q[1:5] = [s * f for f in fingers]
    if family == "lateral":
        q[1:5] = np.clip(np.array(q[1:5]) + 0.05, 0, 1)
    q[5] = wrist
    return np.clip(q, [0] * 5 + [-1], 1)


def sample(family, n, rng, spread=0.12, center=None):
    """n parameter variants of one family around its default (or a remembered good) setting."""
    s0, t0 = center or DEFAULT_PARAMS[family]
    out = []
    for i in range(n):
        if i == 0:
            s, t = s0, t0
        else:
            s, t = s0 + rng.normal(0, spread), t0 + rng.normal(0, spread)
        s, t = float(np.clip(s, 0.3, 1.0)), float(np.clip(t, 0.0, 1.0))
        out.append({"family": family, "s": round(s, 3), "t": round(t, 3), "q": shape(family, s, t).tolist()})
    return out


def describe():
    return "\n".join(f"- {k}: {v[2]}" for k, v in FAMILIES.items())
