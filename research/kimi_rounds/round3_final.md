# Kimi round 3 (final) + InMoov-legs survey - 2026-09-25

## Final v1 build (life-size torso + arms on a hoverboard base)
The full priced list is in `data/bom.json` (phase2) and in the "Phase 2" sheet of `robotai_BOM.xlsx`.
**C$1,341.49 pre-tax vs C$1,500** (C$158.51 buffer).

| Subsystem | Spend | Budget |
|---|---|---|
| Arms | C$798.42 | 500 (over; the base and electronics cover it) |
| Base | C$210.00 | 500 |
| Electronics + sensing | C$333.07 | 500 |
| Compute | C$0 (laptop) | - |

### Arm joints
| Joint | Motor | Ratio | Needed | Rated |
|---|---|---|---|---|
| Shoulder pitch | NFP 5840-31ZY-EN | 1000:1 | 71.4 kg-cm | 100 |
| Shoulder roll | NFP 5840-31ZY-EN | 1000:1 | 71.4 kg-cm | 100 |
| Shoulder yaw | NFP 5840-31ZY-EN | 500:1 | ~25 kg-cm | 70 |
| Elbow | NFP 5840-31ZY-EN | 500:1 | 44 kg-cm | 70 |
| Wrist rotation | STS3215 | - | ~7 kg-cm | 10 |
| Hand | owned | - | - | - |

The hand is 5x MG996R + PCA9685 + ESP32 (already owned). The shoulder pitch/roll motors mount in the torso. The 1000:1 shoulders move at about 36°/s, slow but self-locking, so the arms hold with no power.

### Week-1 bench test (1x 1000:1 + 1x 500:1, before buying the other 6)
- **Torque:** 8 kg on a 10 cm arm, 20 reps of 90°, below 60 °C, 2.5 A or less.
- **Speed:** 90° in 3 s or less at 40 kg-cm.
- **Backlash:** 1.5° or less is a pass; 1.5-2.5° passes with software compensation; above 2.5° fails.
- **Self-lock:** less than 1° of movement under 71 kg-cm with the power off.
- **Control:** ESP32 + BTS7960 + AS5600 at 50 Hz settles within 2 s, with 2° or less error.
- **Thermal:** 30 min at 50 kg-cm, below 60 °C.

Any fail on torque, backlash or self-lock means switching to spring-counterbalanced 500:1 everywhere.

### Week-1 purchase order
1. **Day 1 (AliExpress, long lead):**
   - STS3215 6-pack
   - 2x Waveshare adapters
   - 5264 cables
   - BNO085
   - 8x AS5600
   - 1x 1000:1 + 1x 500:1 motor
2. **Days 1-7:** hoverboard in person (single STM32/GD32 mainboard only).
3. **Days 2-3 (Canada):**
   - 8x BTS7960 (Universal-Solder)
   - 30-60 V buck
   - casters, e-stop and wiring
   - EMEET C960
   - hub, screws, clamps
4. **Deferred:**
   - the other 6 motors (after the test)
   - wrist cams (week 3)
   - legs-gate servo packs + LiPo (week 10)

## InMoov-legs survey (Kimi)
**No InMoov has ever walked**, not even Gael Langevin's own.
- **Official InMoov legs** (inmoov.fr/legs-non-motorized) are non-motorized and only stand or pose.
- **Gael's motorized legs** were never finished.
- **Community InMoov legs** (Thingiverse: Bartods, kike1978, Qeebo, ...) are all static.
- **MyRobotLab "walking robots" analysis** concluded it's hard and was never built.
- **Real full-size walking reference:** Menlo Research's Asimov v0 (github.com/menloresearch/asimov-v0). It has 12-DOF QDD legs (hip pitch 120 Nm, knee 75 Nm, ankle 36 Nm peak) and costs under US$25k total.
- **Rejected:**
  - Poppy legs: 40 cm, too small.
  - OpenLoong: an 80 kg industrial robot.

Kimi puts a walking full-size v2 at about C$12k, assuming QDD actuator prices stay flat.
Our response: robotai uses its own leg design (cad/legs.py), not InMoov legs. The week-10 small walker proves the walking code, and full-size walking legs are v2.
