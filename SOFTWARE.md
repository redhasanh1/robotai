# PINN Humanoid: the software, in plain words

## The idea

Big robot companies train huge models on thousands of hours of robot data. We can't, and we don't need to.
Our robot **thinks with ready-made AI at the moment it acts**, **checks every move with physics** before
doing it, **checks itself afterwards**, and **remembers what worked**. Almost nothing is trained.

That only works if thinking is fast. A slow brain can check 1 or 2 options and then has to act. A fast brain
(Cerebras) can check 16 options several times a second and catch its own mistakes mid-move. **That speed gap is
the whole project.**

## How one grasp works

```
camera + "pick up the can"
   |
1. CHOOSE   the AI picks a kind of grasp (power / tripod / pinch / hook / lateral),
            reading past attempts from memory
2. SAMPLE   8 variations of that grasp are made locally
3. PREDICT  physics simulates all 8 (MuJoCo, on the CPU or the NVIDIA GPU)
            if physics says every one drops -> pick a different kind of grasp, before touching anything
4. RANK     the AI ranks all 8 in ONE call, using the camera and the physics predictions
5. DO IT    the best one runs on the hand
6. CHECK    fast: a local slip check at 50 Hz (did the object move off the palm?)
            slow: the AI looks at the camera ("is it still in the hand?")
7. REMEMBER success or failure (and why) goes into memory; on failure try the next best
```

## The physics-informed part

The servos can't report where they are, and the camera often can't see a finger (it's behind the object).
So the robot keeps an estimate:

- **Physics** of the servo and tendon predicts where each finger should be from the commands we sent.
- **The camera** corrects it whenever it can see.
- **A tiny learned model** fixes what the physics gets wrong about this particular hand.

On test hands with physics we never designed for, this is **6 to 20 times more accurate than the camera alone**
(1-3 degrees vs about 16).

## Results so far (simulation)

| What | Without | With |
|---|---|---|
| Pick the best of 8 instead of 1 | 48% | 71% |
| Self-check and retry | 58% | 98% |
| Physics veto (don't try grasps physics says will drop) | 71% | 94% |
| Everything together, on a contact model nothing was tuned on | 44% (blind single try) | 92% |
| Finger position estimate vs camera alone | ~16 deg error | 1-3 deg |
| NVIDIA GPU sim on the laptop's GTX 1660 Ti | - | 1024 grasps checked in 1.9 s |

Brain speed per decision:
- **Measured:** small AI on the laptop (SmolVLM-500M): ~14 s
- **Estimated:** rented GPU ~3 s, Cerebras ~0.6 s (to be measured, needs the API key)

Full tables: `results/bench.md`, `results/estimator_and_gpu.md`.

## What runs where

| Part | Runs on | Speed |
|---|---|---|
| Servo control and safety (clamp, speed limit, watchdog, e-stop) | ESP32 | 100 times a second |
| Physics, estimator, slip check, memory | laptop | 50+ times a second |
| Thinking: choose, rank, check | AI endpoint: laptop, rented GPU, or Cerebras (one setting) | 0.1 to 1 times a second |

## Files

| Where | What |
|---|---|
| `firmware/hand_esp32/` | ESP32 code |
| `hand/` | the robot code: `protocol`, `plant` (servo physics), `sim` (MuJoCo), `gpu_sim` (NVIDIA MuJoCo Warp), `estimator`, `sysid`, `vision`, `primitives`, `brain`, `memory`, `loop` |
| `tools/` | things to run: `demo`, `console`, `servo_bench`, `servo_characterize`, `bench`, `estimator_eval`, `brain_live`, `local_vlm_server`, `vision` |
| `setup/` | install everything, drivers, flashing, printable markers |
| `results/` | benchmark tables |
| `tests/` | `.venv\Scripts\python -m pytest` |

## What's honest and what isn't yet

- Everything above is **simulation**. The real hand gets the same tests when it's built.
- Cerebras and rented-GPU speeds are **estimates** until measured.
- The rule-based "stub brain" stands in for the AI in most sim runs. Real models have been run through the same
  loop (`tools/brain_live.py`).
