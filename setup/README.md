# Setup: everything the hand needs, in one place

Do these in order. Steps 1–3 need no hardware.

## 1. Install the software (once, ~15 min, mostly downloads)

Open PowerShell in the `robotai` folder and run:

```powershell
powershell -ExecutionPolicy Bypass -File setup\install.ps1
```

It installs, in your user folder only:

| What | Why |
|---|---|
| Python 3.12 venv in `.venv` (via `uv`) | all the robot code |
| MuJoCo | the physics simulator (same model runs on NVIDIA MuJoCo Warp later) |
| PyTorch + CUDA 12.6 | the small learned models, on the GTX 1660 Ti |
| OpenCV | the webcam fingertip tracking |
| pyserial | talking to the ESP32 over USB |
| arduino-cli + ESP32 board support | compiling and uploading the ESP32 firmware (no Arduino IDE needed) |

It finishes by compiling the firmware and running the tests. Green at the end = ready.

## 2. VS Code (optional, nicer)

Open the `robotai` folder in VS Code. It will offer to install the recommended extensions: accept.

- Python, Pylance, Python Debugger: run and debug the robot code
- C/C++: reading the ESP32 firmware
- Serial Monitor: see what the ESP32 prints

Then **Terminal → Run Task** has one-click buttons: install everything, compile firmware, flash to ESP32,
console, servo test, watch the sim hand, tests, benchmark.

## 3. Try it with no hardware

```powershell
.venv\Scripts\python tools\demo.py              # watch the sim hand choose, check and grasp 4 objects
.venv\Scripts\python tools\console.py           # practice talking to a fake ESP32 (type V, T, S 1 1500, E)
.venv\Scripts\python tools\bench.py --quick     # the capstone numbers
```

## 4. When the ESP32 arrives

1. Plug it in with a **data** USB cable. A new COM port should appear in Device Manager.
   Nothing? → [drivers.md](drivers.md) (Freenove boards use the CH340 driver).
2. Flash the firmware: `powershell -ExecutionPolicy Bypass -File setup\flash.ps1`
   You should see `BOOT hand-esp32 0.1`. Type `V`, get `OK V hand-esp32 0.1`.
3. Wire the PCA9685 (pins are at the top of `firmware/hand_esp32/hand_esp32.ino`):
   VCC→3V3, GND→GND, SDA→GPIO21, SCL→GPIO22, OE→GPIO25. Reset the ESP32: if it prints `ERR PCA9685 not found`,
   check those four wires.

## 5. When the servos arrive (Monday) — safety first

1. Set the power supply to **6.0 V** on its display *before* connecting anything.
2. 2200 µF capacitor across the PCA9685 V+ / GND terminal, **stripe to GND**.
3. Supply GND and ESP32 GND connected together.
4. Test every servo, no horns or tendons on yet:
   `.venv\Scripts\python tools\servo_bench.py doa COM5`
   Anything that buzzes, stalls or jitters → set aside for return.
5. With the horn on, find each finger's open/closed pulse:
   `.venv\Scripts\python tools\servo_bench.py range COM5 1` (channel 1 = index; 0 thumb … 4 pinky, 5 wrist).
   These become a hard limit in the firmware: the servo can never be driven past them.
6. **Never leave it powered while you're away.** There's no fuse on this build.

## Where things live

| Folder | What |
|---|---|
| `firmware/hand_esp32/` | ESP32 code: servo board driver, safety (clamp, slew, watchdog, e-stop) |
| `hand/` | laptop code: protocol, servo physics, sim, estimator, brain, memory, loop |
| `tools/` | things you run: demo, console, servo bench, benchmark, estimator eval, Cerebras latency |
| `tests/` | `.venv\Scripts\python -m pytest` |
| `setup/` | this folder |
