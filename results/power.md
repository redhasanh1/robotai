# Servo power budget (hand/power.py)

MG996R at 6 V: 10 mA idle, ~0.7 A moving, 2.5 A stall; supply 6.0 V / 12 A per hand (one PSU each); wiring 0.06 ohm (assumed - measure Monday). A finger resting on an object draws current in proportion to how far past the contact it is commanded, saturating at stall.

| scenario | guard | peak A | mean A | rail min V | s over 12 A |
|---|---|---|---|---|---|
| close on nothing | 1 hand | none | 1.81 | 0.36 | 5.89 | 0.0 |
| close on nothing | 2 hands | none | 3.62 | 0.71 | 5.78 | 0.0 |
| close on nothing | 2 hands, 0.15s stagger | none | 3.62 | 0.71 | 5.78 | 0.0 |
| close on a can and squeeze | 1 hand | none | 12.51 | 11.28 | 5.25 | 1.32 |
| close on a can and squeeze | 2 hands | none | 25.02 | 22.57 | 4.5 | 1.33 |
| close on a can and squeeze | 2 hands, 0.15s stagger | none | 25.02 | 21.32 | 4.5 | 1.32 |
| DOA sweep, all fingers | 1 hand | none | 1.81 | 1.53 | 5.89 | 0.0 |
| DOA sweep, all fingers | 2 hands | none | 3.62 | 3.06 | 5.78 | 0.0 |
| DOA sweep, all fingers | 2 hands, 0.15s stagger | none | 3.62 | 2.96 | 5.78 | 0.0 |
| close on nothing | 1 hand | squeeze | 1.81 | 0.36 | 5.89 | 0.0 |
| close on nothing | 2 hands | squeeze | 3.62 | 0.71 | 5.78 | 0.0 |
| close on nothing | 2 hands, 0.15s stagger | squeeze | 3.62 | 0.71 | 5.78 | 0.0 |
| close on a can and squeeze | 1 hand | squeeze | 12.51 | 5.45 | 5.25 | 0.14 |
| close on a can and squeeze | 2 hands | squeeze | 25.02 | 10.89 | 4.5 | 0.16 |
| close on a can and squeeze | 2 hands, 0.15s stagger | squeeze | 19.43 | 10.39 | 4.83 | 0.3 |
| DOA sweep, all fingers | 1 hand | squeeze | 1.81 | 1.53 | 5.89 | 0.0 |
| DOA sweep, all fingers | 2 hands | squeeze | 3.62 | 3.06 | 5.78 | 0.0 |
| DOA sweep, all fingers | 2 hands, 0.15s stagger | squeeze | 3.62 | 2.96 | 5.78 | 0.0 |

Takeaways: free motion (closing on nothing, the DOA sweep) never gets near the limit, even with both hands on one supply. Squeezing an object without the guard stalls all five servos (~12.5 A for one hand, over the supply). The squeeze guard (hand/guard.py) halves the mean current; what remains is the ~0.15 s before contact is detected. On the real hand the guard needs a finger estimate that sees the object (fingertip markers or the pot mod) - until then, keep grasps short.
