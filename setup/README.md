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

Real InMoov look in the full-robot sim (one time, ~1 min, 290 parts, kept in `logs\`, not in git because of the
GPL license): `.venv\Scripts\python tools\fetch_inmoov_meshes.py`. Without it the full robot shows as a skeleton.

## 4. When the ESP32 arrives

1. Plug it in with a **data** USB cable. A new COM port should appear in Device Manager.
   Nothing? → [drivers.md](drivers.md) (Freenove boards use the CH340 driver).
2. Flash the firmware: `powershell -ExecutionPolicy Bypass -File setup\flash.ps1`
   You should see `BOOT hand-esp32 0.1`. Type `V`, get `OK V hand-esp32 0.1`.
3. Wire the PCA9685 (pins are at the top of `firmware/hand_esp32/hand_esp32.ino`):
   VCC→3V3, GND→GND, SDA→GPIO21, SCL→GPIO22, OE→GPIO25. Reset the ESP32: if it prints `ERR PCA9685 not found`,
   check those four wires.

## 5. When the servos arrive (Monday) — safety first

**Easiest:** `.venv\Scripts\python tools\monday.py` walks through all of this in order (finds the COM port, flashes,
checks the link, safety checklist, servo test, range, speed) and stops before each step. `--side left` for the second
hand, `--from 5` to pick up where you left off. The individual steps, if you'd rather run them yourself:

1. Set the power supply to **6.0 V** on its display *before* connecting anything.
2. 2200 µF capacitor across the PCA9685 V+ / GND terminal, **stripe to GND**.
3. Supply GND and ESP32 GND connected together.
4. Test every servo, no horns or tendons on yet:
   `.venv\Scripts\python tools\servo_bench.py doa COM5`
   Anything that buzzes, stalls or jitters → set aside for return.
5. With the horn on, find each finger's open/closed pulse:
   `.venv\Scripts\python tools\servo_bench.py range COM5 1` (channel 1 = index; 0 thumb … 4 pinky, 5 wrist).
   These become a hard limit in the firmware: the servo can never be driven past them.
6. Measure the USB link before trusting the 0.2 s watchdog:
   `.venv\Scripts\python tools\link_jitter.py COM5` (add `--apply` to set the timeout it recommends).
7. Measure each servo's real speed (marker on the horn, webcam on it):
   `.venv\Scripts\python tools\servo_characterize.py COM5 1` — one run per channel. Cheap clone servos all
   differ; the physics needs each one's own numbers.
8. If the ESP32 ever restarts by itself, look at its first line: `BOOT hand-esp32 0.1 reset=BROWNOUT` means the
   power sagged (servos starting together, a loose capacitor), not a code bug. Re-seat the 2200 µF cap.
9. Before any tendon goes on: bend every printed finger by hand. A stiff hinge makes the servo stall and get hot.
10. **Never leave it powered while you're away.** There's no fuse on this build.

## Two hands

Same firmware on both ESP32 boards. Put a sticker on each board (R / L). The first time a board is used, the tool
you run names it after `--side` (right is the default) and keeps it in the board's memory. After that, opening the
wrong board for a hand is refused ("this board is the left hand, not the right hand - wrong COM port?").
Every tool takes `--side left` for the second hand, and each hand has its own calibration file
(`hand_calibration.json` right, `hand_calibration_left.json` left).

## 6. Run the brain on the real hand

`.venv\Scripts\python tools\run_hand.py COM5 ball --cam 0`: same brain as the sim. You put the object in the
palm and answer y/n; memory is kept in `logs\memory.sqlite`, so it gets better across sessions.
The control panel (`.venv\Scripts\pythonw tools\panel.py`) has a big **STOP ALL** button for anything running.

## Where things live

| Folder | What |
|---|---|
| `firmware/hand_esp32/` | ESP32 code: servo board driver, safety (clamp, slew, watchdog, e-stop) |
| `hand/` | laptop code: protocol, servo physics, sim, estimator, brain, memory, loop |
| `tools/` | things you run: demo, console, servo bench, benchmark, estimator eval, Cerebras latency |
| `tests/` | `.venv\Scripts\python -m pytest` |
| `setup/` | this folder |
