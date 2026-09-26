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
| Habits: stop asking the AI once a grasp keeps working | 3.0 AI calls per task | 1.0 AI call, same 100% success |
| Brain's choice of grasp type vs a random one (full system) | 85% (random) | 98% (brain) |

Brain speed per decision:
- **Measured:** Qwen2.5-VL-3B on the laptop: ~25 s (follows instructions 48/48); SmolVLM-500M: ~14 s (4/48)
- **Estimated:** rented GPU ~3 s, Cerebras ~0.6 s (to be measured, needs the API key)

Full tables: `results/bench.md`, `results/estimator_and_gpu.md`.

## The simulated house

The InMoov on its wheeled base drives between a kitchen (sink, dish rack), a laundry (washer, basket), a living room
and you. It does the dishes, the laundry, fetches things, wipes counters, puts things away, juggles, and understands
wishes ("I'm hungry" → brings the apple). Every plan is checked on the body first (reach, joints, grip, catches).

**50-command test** (`results/house.md`): built-in rules pass **47/50**. With the small AI model on the laptop GPU
thinking up the rest, restricted to the robot's own skills and using its past tasks as examples, it's **49/50**.
The one left, "I spilled something in the living room", needs common sense the laptop model doesn't have.

## See it and use it

Open the control panel: `.venv\Scripts\pythonw tools\panel.py`

- **Type a task** or press **🎲 Random task**: the full InMoov plans it from its skills and does it: pick up,
  put on the left/middle/right, stack one thing on another, hand it to you, point at, push, look at, wave, box,
  clap, nod, shake its head, tidy the table. Chain them: "grab the orange and put it on the right, then wave".
- **Sim hand**: grabs the ball, can, block and bar once each, in slow motion.
- **Full robot**: the whole InMoov upper body (57 joints, from the same model as the website). The arm reaches, the
  wrist turns and the hand closes, or open it with sliders and move every joint yourself.
- **STOP ALL**: kills every robot program that's running. To interrupt Claude, press Esc in the terminal.

## What the simulations say about the real hand (read before Monday)

- **Power** (`results/power.md`): moving fingers is cheap (under 2 A per hand). Squeezing an object is not. All
  five servos push at close to stall, about 12.5 A on a 12 A supply, and they heat up. The **squeeze guard**
  (`hand/guard.py`) backs each finger off to just past contact and halves the current. It needs the fingertip
  camera to see contact, so keep real grasps short until that works.
- **Tendons** (`results/tendon.md`): a finger reaches 90% closed at about 2.3 rad (132°) of servo horn, already
  using 73% of the servo's strength. At 2.5 rad the line fights the finger's end stops and the servo stalls.
  **Calibrate each finger's closed position a little short of fully closed.** A few mm of slack is a safety margin.
  The fingertip curls before the base joint.
- **Camera**: the laptop webcam measured 16 fps with exposure locked, not 30. Every frame is timestamped.

## Learning without big training

1. **Memory**: every attempt, and why it failed, goes into the AI's prompt next time.
2. **Habits**: once a grasp keeps working on an object, the robot stops asking the AI (`hand/habit.py`).
   One failure and it asks again.
3. **Its own skills** (`hand/skills.py`): when the AI works out a task the built-in skills don't cover, the program is
   saved as a new named skill with the objects as slots ("hide the remote" -> "hide {0}"). Next time, or with another
   object, the robot does it with no model call, after checking it on the body. One failure and it asks the AI again.
   Rooms are slots too, except when the room is why those objects were picked ("clear the living room table").
   `tools/skill_growth.py`: 7 new tasks, then again (0 model calls), then 6 new wordings (5 free). `results/skill_growth.md`.
4. **Recording**: every real attempt is saved (`logs/episodes`) and converts to a LeRobot dataset
   (`tools/export_lerobot.py`), ready for GR00T / SmolVLA post-training on a rented GPU once the arm exists.

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
