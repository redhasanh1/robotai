# robotai v1 architecture (decided 2026-09-25)

Cordless robot (a power cord is OK for v1). All compute is onboard: the owner's laptop rides on the robot in a
laptop tray on the base / back of the torso. The only link off the robot is Wi-Fi to the Cerebras API.

| Layer | Runs on | Rate | Job |
|---|---|---|---|
| Servo control + safety stop | ESP32 + PCA9685 (owned) | 50-100 Hz | move joints; e-stop cuts servo power in hardware |
| Motor policy (ACT, then SmolVLA) | laptop GTX 1660 Ti 6 GB, onboard | 30-50 Hz | camera images -> joint targets for one skill |
| Brain | **Cerebras API** (OpenAI-compatible), image-capable model | 1-10 Hz | voice -> plan -> pick next skill -> check success -> re-plan; best-of-N move selection |

Never in the cloud: servo control and safety (Wi-Fi drops must not freeze a grasp).
Training: ACT trains on the laptop; SmolVLA fine-tuning (~22 GB) needs a rented cloud GPU or Cerebras access.
Jetson Orin Nano: deferred to the week-10 legs gate or a later fully-battery version (~C$350, doesn't fit v1's C$106 buffer, not faster than the laptop GPU).
Week 1: `python tools/cerebras_latency.py photo.jpg 20` sets how fast the brain loop can run.
