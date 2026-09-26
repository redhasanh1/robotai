"""Servo power budget: will a motion brown out the 6 V rail? (Kimi round 7: an afternoon, not a project.)

MG996R at 6 V (datasheet): ~10 mA idle, 500-900 mA moving (depends on load), 2.5 A stall. The supply is the
SHNITPWR set to 6.0 V, 12 A max. Wiring from supply to PCA9685 V+ and on to the servos adds resistance, so the rail
sags under current: V_rail = 6.0 - R * I. Below ~4.8 V MG996Rs jitter and reset their position loop; if the ESP32
shares a ground with a bouncing rail it can reset too (firmware BOOT line would say reset=BROWNOUT).

    simulate(q_cmds, dt, stall=...)  -> {"peak_a", "mean_a", "min_v", "seconds_over_limit", "trace"}
Current per servo comes from the same grey-box plant the rest of the stack uses: moving -> running current scaled
by how hard it is working, blocked by an object -> toward stall.
"""
import numpy as np

from .plant import ServoPlant

IDLE_A, RUN_A, STALL_A = 0.01, 0.7, 2.5
SUPPLY_V, SUPPLY_A = 6.0, 12.0
WIRE_OHM = 0.06            # ~1 m of 18 AWG there and back + terminals; measure it Monday (volt drop at a known load)
JITTER_V = 4.8


def servo_current(v, v_max, load):
    """v: shaft speed, v_max: its limit, load: 0..1 (1 = full stall). A blocked servo's current follows its position
    error (the servo's own P loop), saturating at stall - see squeeze_load()."""
    moving = np.clip(np.abs(v) / np.maximum(v_max, 1e-6), 0, 1)
    return IDLE_A + RUN_A * moving * (0.5 + 0.5 * load) + (STALL_A - IDLE_A) * load * (1 - moving)


def squeeze_load(cmd, q, stop, full_at=0.1):
    """How hard a finger resting on an object pushes: proportional to how far past the contact the command is,
    reaching stall at full_at flexion units of error (MG996R's P loop saturates quickly)."""
    touching = ~np.isnan(stop) & (q >= np.nan_to_num(stop) - 1e-3)
    return np.where(touching, np.clip((np.asarray(cmd) - q) / full_at, 0, 1), 0.0)


def simulate(q_cmds, dt=0.01, stop=None, hands=1, stagger_s=0.0, servos=None, guard_cls=None):
    """q_cmds: (T, 6) flexion targets for one hand (the same motion is run on `hands` hands, the k-th hand starting
    k*stagger_s later). stop: per-joint flexion where an object blocks the finger (NaN = free)."""
    q_cmds = np.asarray(q_cmds, float)
    T = len(q_cmds)
    total = np.zeros(T)
    for h in range(hands):
        plant = ServoPlant(servos)
        guard = guard_cls() if guard_cls else None
        shift = int(round(h * stagger_s / dt))
        for k in range(T):
            cmd = q_cmds[max(0, k - shift)] if k >= shift else q_cmds[0] * 0 + plant.p
            if guard is not None:
                cmd = guard.update(cmd, plant.q, dt)          # sees the finger state the laptop would estimate
            p0 = plant.p.copy()
            q = plant.step(cmd, dt, stop=stop)
            v = (plant.p - p0) / dt
            blocked = np.zeros_like(q) if stop is None else squeeze_load(cmd, q, stop)
            total[k] += servo_current(v, plant.v_max, blocked).sum()
    rail = SUPPLY_V - WIRE_OHM * total
    return {"peak_a": round(float(total.max()), 2), "mean_a": round(float(total.mean()), 2),
            "min_v": round(float(rail.min()), 2), "seconds_over_limit": round(float((total > SUPPLY_A).sum() * dt), 2),
            "seconds_jitter": round(float((rail < JITTER_V).sum() * dt), 2), "trace": total}


def scenarios(guard_cls=None):
    """The motions we will actually run in week 1-2, on one and on two hands."""
    from . import primitives
    close = np.array([primitives.shape("power", 0.9, 0.9)] * 150)          # 1.5 s: close and hold
    stop_obj = np.array([0.55, 0.6, 0.6, 0.6, 0.6, np.nan])                # a can blocks the fingers half way
    sweep = np.array([np.r_[np.full(5, 0.5 + 0.5 * np.sin(2 * np.pi * k / 50)), 0] for k in range(200)])
    out = {}
    for name, cmds, stop in (("close on nothing", close, None), ("close on a can and squeeze", close, stop_obj),
                             ("DOA sweep, all fingers", sweep, None)):
        for hands, stagger in ((1, 0.0), (2, 0.0), (2, 0.15)):
            r = simulate(cmds, stop=stop, hands=hands, stagger_s=stagger, guard_cls=guard_cls)
            r.pop("trace")
            out[f"{name} | {hands} hand{'s' if hands > 1 else ''}" + (f", {stagger:.2f}s stagger" if stagger else "")] = r
    return out
