# robotai: a legged humanoid on $1,500 CAD

Research date: 2026-09-25. FX used: **1 USD = 1.41 CAD** (USD/CAD 1.4147 on 2026-09-25, per [tradingeconomics](https://tradingeconomics.com/canada/currency), search snippet).
Price tags: **[page]** = I read the price on the vendor page. **[snippet]** = the price came from a search-result snippet or an article, not the vendor page. **[est]** = my estimate with no source. **[analysis]** = my own reasoning or arithmetic.

---

## TL;DR (honest version)

1. **$500 CAD for legs is about $355 USD.** A 12-DOF leg set therefore gets about **$30 USD per joint**. The only actuators at that price that are proven to walk under an RL policy are **Feetech bus servos** (STS3215 at about $14–16, STS3250 at about $43). Any BLDC option (printed cycloidal, GIM6010, RobStride) costs **$60–240 USD per joint** (sources below). That puts BLDC legs at 2–6x the leg budget.
2. With STS3250 knees, the torque sizing caps the robot at **about 0.6–0.65 m tall and about 4–5 kg** [analysis, sec. 3]. That is ToddlerBot size (0.56 m, 3.4 kg, walks with a 3.0 Nm knee servo).
3. **A walking adult-size humanoid, or even a walking 0.9–1.2 m one, is not possible on $1,500 CAD if you build it.** Berkeley Humanoid Lite (0.8 m, 16 kg) has a BOM of **$4,312 USD**. The cheapest *commercial* walker at about 1 m is the Noetix Bumi at **$1,408 USD (about $1,985 CAD)**. That is a price floor held down by Chinese volume, not a DIY BOM.
4. **Recommendation: "ToddlerBot-plus".** A **0.62 m, about 4.2 kg, 27-DOF** Feetech humanoid:
   - 12-DOF legs: 6x STS3250 on hip pitch, knee and ankle pitch; 6x STS3215 on hip yaw, hip roll and ankle roll.
   - 2x 5-DOF arms with grippers, a 1-DOF waist and a 2-DOF neck.
   - A Raspberry Pi 5 on board.
   - RL walking in MuJoCo Playground or mjlab.
   - LeRobot teleop and imitation learning for chores.
5. **The InMoov hands do not fit this robot.** Each hand plus forearm weighs 750 g, which is about 18% of the whole robot's mass per side, and needs more shoulder torque than any cheap servo can hold (sec. 3). Keep them for a Stage-2 stationary counter station.
6. **Chores at this scale** are floor and low-shelf work: tidying toys and socks, fetching light items (<300 g), coffee-table tasks. **Kitchen prep** works in "countertop mode": the robot stands and walks on the counter. It cannot reach a 0.9 m counter from the floor.

---

## 1. Existing open, low-cost legged humanoids

| Robot | Height / mass | DOF | Leg actuator | BOM / price | Walks (RL sim-to-real)? | Sim stack | License / repo |
|---|---|---|---|---|---|---|---|
| **Berkeley Humanoid Lite** (UC Berkeley, 2025) | 0.8 m / 16 kg | 22 (6/leg, 5/arm) | 3D-printed **cycloidal** + BLDC (MAD M6C12 150KV in the "6512" size, a 5010 motor in the small size), B-G431B-ESC1 driver, AS5600 encoder, CAN | **$4,312 USD** (US) / $3,236 (China). 10x 6512 at **$188**, 12x 5010 at **$136**; mini PC $129, 6S battery $70 ([arXiv html](https://arxiv.org/html/2504.17249)) [page] | Yes, zero-shot. Walking used only about 30% of actuator torque. 6512 peak about 20 Nm, backlash 0.023 rad, 60 h endurance test ([arXiv](https://arxiv.org/html/2504.17249)) | Isaac Gym in the paper; the repo follows Isaac Lab ([GitHub](https://github.com/HybridRobotics/Berkeley-Humanoid-Lite)) | Code MIT, assets CC-BY-SA 4.0 ([GitHub](https://github.com/HybridRobotics/Berkeley-Humanoid-Lite)); [site](https://lite.berkeley-humanoid.org/) |
| **ToddlerBot** (Stanford, 2025) | 0.56 m / 3.4 kg | 30 (6/leg, 7/arm, 2 neck, 2 waist) | Dynamixel: hip roll/pitch 2XC430 (1.8 Nm), hip yaw XC330 (1.0 Nm), **knee XM430-W210 (3.0 Nm)**, ankle pitch XM430 (3.0 Nm), ankle roll XC430 (1.9 Nm) | **about $6,000 USD**, 90% of it motors plus the Jetson Orin NX ([arXiv](https://arxiv.org/html/2502.00893v3)) [page] | Yes, zero-shot, after motor sysid. Up to 0.25 m/s ([site](https://toddlerbot.github.io/)) | MJX + Brax PPO, 3e8 steps, 1024 envs ([arXiv](https://arxiv.org/html/2502.00893v3)) | Code MIT, design CC BY-NC-SA 4.0 ([GitHub](https://github.com/hshi74/toddlerbot)); Onshape and MakerWorld CAD |
| **Open Duck Mini v2** (apirrone, BDX clone) | about 0.42 m / not stated | 14 servos (legs + head) | **STS3215 7.4 V** (€14 each) | **under $400**; €347–414 ([README](https://github.com/apirrone/Open_Duck_Mini/blob/v2/README.md), [BOM snippet](https://www.scribd.com/document/861565028/BOM-Open-Duck-Mini-V2)) [snippet] | Yes. ONNX walking policies published, running on a Pi Zero 2W ([GitHub](https://github.com/apirrone/Open_Duck_Mini)) | MuJoCo Playground ([Open_Duck_Playground](https://github.com/apirrone/Open_Duck_Playground)) | Apache-2.0 |
| **K-Scale Zeroth-01 / Z-Bot** | about 0.40 m | about 16 | **STS3250** in the legs (STS3215 at 45 RPM was "no longer sufficient" for the legs), STS3215 in the arms ([build log](https://github.com/Justin-Riekehof/zeroth-01-build)) | BOM from **$350** ([X](https://x.com/kscalelabs/status/1856155245967192471)); Z-Bot kit was $999 ([snippet](https://www.awesomerobots.xyz/robots/kscale-zbot)) | RL walking in MuJoCo/ksim, deployed on a Pi 4 | ksim (MuJoCo) | MIT. **K-Scale shut down in Nov 2025 and open-sourced all its IP** ([Humanoids Daily](https://www.humanoidsdaily.com/news/k-scale-labs-cancels-k-bot-orders-open-sources-all-ip-after-funding-fails)), so the project is unmaintained |
| **LeRobot Humanoid** (Hugging Face, May 2026) | not stated / legs only | 12 leg motors | **RobStride** QDD: 2x RS00, 2x RS02, 4x RS03, 4x RS05 ([bom_buy.csv](https://github.com/huggingface/lerobot-humanoid-hardware)) | **about $2,500 USD, legs only** ([HF blog](https://huggingface.co/blog/VirgileBatto/lerobot-humanoid)) | **Only an early standing policy.** Locomotion is still experimental ([Humanoids Daily](https://www.humanoidsdaily.com/news/hugging-face-drops-a-2-500-3d-printed-humanoid-for-open-robot-learning)) | **mjlab** + lerobot-legged-zoo | [GitHub](https://github.com/huggingface/lerobot-humanoid) |
| **HopeJR** (HF + TheRobotStudio) | "full-size" | 66 claimed | not specified in the sources | about $2,500–3,000 ([TechCrunch](https://techcrunch.com/2025/05/29/hugging-face-unveils-two-new-humanoid-robots/)) [snippet] | The repo's active work is the **Arm/** branch (LeRobot teleop). I found no evidence of RL walking ([GitHub](https://github.com/TheRobotStudio/HOPEJr)) | — | [GitHub](https://github.com/TheRobotStudio/HOPEJr) |
| **Microduck** (Pollen/HF, Aug 2026) | 0.25 m / <0.8 kg | 15 | Dynamixel XL330-class | **$399 retail** ([CNX](https://www.cnx-software.com/2026/08/28/microduck-a-duck-like-biped-robot-designed-for-physical-ai-experimentation-and-fun/)) [snippet] | Yes, ships with walk, kick, grab and recovery skills | RL stack included | open |
| **Asimov v1** (Menlo) | 1.2 m / 35 kg | 25 | Encos QDD | **about $16k** BOM; legs alone about $10k ([snippet](https://docs.menlo.ai/asimov/1/bom)) | Pre-trained walking policy | — | [GitHub](https://github.com/asimovinc/asimov-1) |

**Commercial price references**

| Robot | Height / mass | Price |
|---|---|---|
| **Noetix Bumi** | 0.94 m / 12 kg | **$1,408 USD** ([SCMP](https://www.scmp.com/tech/tech-trends/article/3330046/chinese-robotics-start-noetix-debuts-family-friendly-us1400-humanoid)) [snippet] |
| **Unitree R1** | 1.22 m / 25 kg, 26 DOF | **$5,900** ([humanoid.guide](https://humanoid.guide/product/unitree-r1/)) [snippet] |
| **Booster K1** | — | $4,999–5,999 ([Humanoids Daily](https://www.humanoidsdaily.com/news/booster-robotics-launches-k1-robocup-champion-platform)) |
| **Booster T1** | — | about $29.8–34k ([snippet](https://botinfo.ai/articles/booster-t1-robot)) |
| **Robotis OP3** | — | $11,969 ([robotis.us](https://www.robotis.us/robotis-op3-us/)) [snippet] |

**What the table shows [analysis]:** every open humanoid that walks under an RL policy and costs under $1k USD is **at or below 0.45 m** and uses Feetech STS servos. At 0.56 m (ToddlerBot) you need about 3 Nm knees. At 0.8 m (BHL) you are into BLDC-plus-reducer actuators and $3–4k.

---

## 2. Leg actuator options

### 2a. Feetech bus servos (TTL daisy chain, magnetic encoder, position/speed/load/current feedback)

| Servo | Stall torque | Mass | Speed | Price | Notes |
|---|---|---|---|---|---|
| **STS3215 12 V (C018)** | 30 kg·cm ≈ **2.94 Nm** | about 55 g [est] | about 45 RPM (K-Scale called it too slow for knees) | **$15.99 each, $14.99 at 5+, $13.99 at 10+** ([WowRobo](https://shop.wowrobo.com/products/feetech-sts3215-servo-12v-30kg-high-torque-servo-for-so-arm100)) [page] | The SO-101 / LeRobot standard servo; 1/345 gearing |
| STS3215 7.4 V | 19 kg·cm ≈ 1.86 Nm | — | — | €14 (Open Duck BOM) [snippet] | Used as the LeRobot leader-arm servo |
| **STS3250** | 50 kg·cm ≈ **4.9 Nm** @12 V; stall 4.2 A | **74.5 g** | 0.13 s/60° ≈ **77 RPM** ([servodatabase](https://servodatabase.com/servo/feetech/sts3250)) | **$43.00** ([WowRobo](https://shop.wowrobo.com/products/feetech-sts3250-c002-servo-12v-50kg-1-345-servo)) [page]; AliExpress about $48–55 [snippet] | Independent test: 48 kg·cm peak, **only about 25 kg·cm sustained** before protection trips, 0.43° backlash, warms about 3.75 °C/min at 40% load ([Robonine](https://robonine.com/feetech-sts3250-smart-actuator-evaluation-of-accuracy-torque-and-backlash/)) |
| STS3235 | about 35 kg·cm | — | — | from $56 ([AIFITLAB](https://aifitlab.com/collections/feetech)) [snippet] | Costs more than the STS3250 for less torque, so skip it |
| HLS3930M | 35 kg·cm @12 V, stall 2.8 A, current-loop / constant-force mode | — | — | not found | True current control is useful for RL, but I found no verified price |
| SM120BL | 120 kg·cm, RS485/Modbus | — | — | not found ([AIFITLAB](https://aifitlab.com/products/feetech-sm120bl-servo-motor)) | Industrial servo, heavy and pricey; overkill here |
| Bus adapter | — | — | — | **Waveshare Bus Servo Adapter (A): $4.99** ([Waveshare](https://www.waveshare.com/bus-servo-adapter-a.htm)) [page] | USB/UART, 9–12.6 V in |

The STS3250 is a better knee servo than ToddlerBot's Dynamixel knee:
- It has 4.9 Nm of stall torque against the XM430-W210's 3.0 Nm, at a similar no-load speed.
- It costs about $43 against Dynamixel's $200+.
- The catch is sustained torque. The STS3250 holds only about 50% of peak continuously, and its internal PID loop gives a worse torque-control model. Plan for motor sysid, the way ToddlerBot and Open Duck both did.

### 2b. BLDC + reducer (cost per joint)

| Option | Torque | Unit cost | 12 leg joints |
|---|---|---|---|
| **BHL 6512 cycloidal** (M6C12 + printed cycloid + B-G431B-ESC1 + AS5600) | about 20 Nm peak, about 90% efficient, 0.023 rad backlash | **$188** (US) / $157 (CN) ([arXiv](https://arxiv.org/html/2504.17249)) [page]. The motor alone is $129 ([MAD store](https://store.mad-motor.com/products/mad-m6c12-eee-brushless-motor-for-the-long-flight-time-multirotor-hexacopter-octopter)) [snippet] | $2,256 USD ≈ **$3,180 CAD** |
| **DIY 5010 cycloid** (cheap 5010 motor + B-G431B-ESC1 + AS5600 + bearings) | unknown; the BHL 5010 variant is its low-torque actuator | motor $12–24 ([AliExpress](https://www.aliexpress.com/item/32652929168.html)) [snippet] + ESC $29.25 ([DigiKey](https://www.digikey.com/en/products/detail/stmicroelectronics/B-G431B-ESC1/10321670)) [snippet] + about $10 in encoder and bearings [est] ≈ **$55–65**. A MakerWorld design claims $40 ([Hackaday comments](https://hackaday.com/2026/08/30/lower-cost-humanoid-robot-leverages-diy-actuators/)) | about $700 USD ≈ **$990 CAD**, before any failures |
| **SteadyWin GIM6010-8** (planetary 8:1, driver included) | **5 Nm rated / 11 Nm peak**, 388 g | $70.35 (listed sold out) ([SteadyWin](https://steadywin-motor.com/products/built-in-star-gear-motor-motor-robot-joint-driver-actuator-controller-motor)) [page]; eBay $88–95 with driver ([snippet](https://www.ebay.com/itm/397474989754)) | about $1,000 USD ≈ **$1,430 CAD** |
| **RobStride 02** (QDD, 17 Nm) / **RobStride 05** (5.5 Nm) | 17 Nm / 5.5 Nm | $240 / $110 ([robstride.com](https://robstride.com/)) [snippet] | about $2,000 USD. This is what the LeRobot Humanoid uses |
| Drivers for reference | — | ODESC v4.2 $29–39 ([Flipsky](https://www.flipskyo.com/products/odesc-v4-2-24v-56v-controller)) [snippet]. SimpleFOC Mini is about 2.5 A class, too weak for 5010-class leg motors [analysis] | — |

**Verdict [analysis]:** every BLDC path costs at least 2x the leg budget, and the DIY cycloid path also costs weeks of actuator R&D. BHL spent a paper's worth of work on backlash and endurance. For a 16-week, 2-person project that also has to do manipulation, Feetech is the only option that fits both the money and the timeline.

---

## 3. Torque sizing: how big can the robot be? [analysis]

Reference points:
- ToddlerBot walks with a **3.0 Nm knee** at **3.4 kg, 0.56 m**.
- BHL walks at 16 kg / 0.8 m using about 30% of a 20 Nm actuator, so about **6 Nm in use**.
- K-Scale notes that joint torque scales roughly as **L⁴** for geometrically similar robots (mass ∝ L³, lever arm ∝ L) ([build log](https://github.com/Justin-Riekehof/zeroth-01-build)).

Define a margin ratio `R = τ_stall / (m · g · L_leg)`, with leg length L_leg ≈ 0.45·H.
- ToddlerBot: 3.0 / (3.4 · 9.81 · 0.25) ≈ **0.36**. Proven to walk.
- To keep R ≥ 0.36 with an STS3250 knee (4.9 Nm), you need m·L ≤ 1.39 kg·m.

| Height H | Mass (∝H³ from ToddlerBot) | L_leg | m·L | R with STS3250 knee | Verdict |
|---|---|---|---|---|---|
| 0.56 m | 3.4 kg | 0.25 m | 0.85 | 0.59 | lots of margin |
| **0.62 m** | **4.2–4.6 kg** | 0.28 m | 1.2–1.3 | **0.38–0.42** | **recommended** |
| 0.70 m | 6.6 kg | 0.32 m | 2.1 | 0.24 | marginal; needs 2 servos per knee or a 2:1 printed stage (costs speed) |
| 0.90 m | 14 kg | 0.40 m | 5.6 | 0.09 | impossible on servos; needs about 15–20 Nm BLDC (BHL class) |
| 1.2 m+ | 25–35 kg | 0.55 m | 14–19 | — | R1 / Asimov class: $6k–$16k |

Continuous-torque check at 0.62 m: walking needs about 0.1·m·g·L ≈ 1.2 Nm, and the STS3250's sustained capacity is about 2.45 Nm. That is fine, as long as the policy is not trained to crouch deeply.

**Arms at this scale.** With STS3215 shoulders (about 1.5 Nm sustained) and a 0.2 m arm, the payload is about 150–300 g at full reach.

**Why the InMoov hands don't fit:**
- The InMoov hand plus forearm weighs **0.75 kg** ([Wevolver](https://www.wevolver.com/specs/inmoov-3d-printed-hand-and-forarm)) [snippet].
- One of them at a 0.2 m reach already needs about 1.5 Nm static, which uses the shoulder's entire sustained budget before lifting any object.
- Two of them would add 1.5 kg (about 35%) to a 4.2 kg biped, at the ends of its arms. That wrecks balance and the knee margin (R drops to about 0.28).
- The hand is also life-size. It is about 40% of a 0.62 m robot's height.
- **Do not mount them on the walker.**

---

## 4. Recommended design: "robotai v1"

**Target: 0.62 m, about 4.2 kg, 27 actuated DOF, Feetech-only, one TTL bus per limb group.**

This is ToddlerBot's joint layout and proportions, with Feetech servos in place of Dynamixels. Fork the Onshape CAD, or redesign it under your own license, because ToddlerBot's design files are NC. Every joint meets or beats ToddlerBot's torque at a 1.2–1.3x mass budget.

| Group | Joint | Servo | ToddlerBot equivalent |
|---|---|---|---|
| Leg (x2) | hip yaw | STS3215 12 V (2.94 Nm) | XC330, 1.0 Nm |
| | hip roll | STS3215 12 V (2.94 Nm) | 2XC430, 1.8 Nm |
| | hip pitch | **STS3250** (4.9 Nm) | 2XC430, 1.8 Nm |
| | knee | **STS3250** (4.9 Nm) | XM430, 3.0 Nm |
| | ankle pitch | **STS3250** (4.9 Nm) | XM430, 3.0 Nm |
| | ankle roll | STS3215 12 V | XC430, 1.9 Nm |
| Arm (x2) | shoulder pitch, shoulder roll, elbow, wrist, gripper | 5x STS3215 12 V | — |
| Torso | waist yaw | STS3215 | — |
| Head | neck yaw/pitch | 2x STS3215 | — |

Mass estimate [analysis]:

| Item | Mass |
|---|---|
| Servos: 6 × 74.5 g + 21 × about 55 g | 1.6 kg |
| Printed PETG structure (TPU feet) | about 1.8 kg |
| 3S 5000 mAh LiPo | 0.35 kg ([Ovonic](https://www.ovonicshop.com/products/ovonic-11-1v-5000mah-3s-50c-lipo-battery-pack-with-xt60-plug)) |
| Pi, cameras, IMU | about 0.15 kg |
| Bearings and fasteners | about 0.3 kg |
| **Total** | **about 4.2 kg** |

The 3S pack gives 11.1–12.6 V, which drives the 12 V servos directly.

### Cost table (CAD, pre-tax, pre-shipping)

**LEGS (budget $500)**

| Item | Qty | Unit | CAD | Tag |
|---|---|---|---|---|
| Feetech STS3250 ([WowRobo](https://shop.wowrobo.com/products/feetech-sts3250-c002-servo-12v-50kg-1-345-servo)) | 6 | $43.00 USD | 364 | [page] |
| Feetech STS3215 12 V at the 10+ price ([WowRobo](https://shop.wowrobo.com/products/feetech-sts3215-servo-12v-30kg-high-torque-servo-for-so-arm100)) | 6 | $13.99 USD | 118 | [page] |
| Waveshare Bus Servo Adapter (A) ([Waveshare](https://www.waveshare.com/bus-servo-adapter-a.htm)) | 1 | $4.99 USD | 7 | [page] |
| **Legs subtotal** | | | **$489** | |

Fallback if the landed cost goes over: drop ankle roll and go 10-DOF, Open-Duck style. That saves $39.

**ARMS + UPPER BODY (budget $500)**

| Item | Qty | Unit | CAD | Tag |
|---|---|---|---|---|
| STS3215 12 V, follower arms (2 × 5 DOF + gripper) | 12 | $13.99 USD | 237 | [page] |
| STS3215 12 V, waist + neck | 3 | $13.99 USD | 59 | [page] |
| STS3215 7.4 V, **one** SO-101-style leader arm for LeRobot teleop, mirrored to either side (Open Duck BOM price) | 6 | €14 ≈ $23 CAD | 138 | [snippet] |
| Bus adapter for the upper body + leader | 2 | $4.99 USD | 14 | [page] |
| Spare STS3215 | 2 | $13.99 USD | 40 | [page] |
| **Arms subtotal** | | | **$488** | |

**EVERYTHING ELSE (budget $500)**

| Item | CAD | Tag |
|---|---|---|
| Raspberry Pi 5 4 GB ([PiShop.ca](https://www.pishop.ca/product/raspberry-pi-5-4gb/), currently out of stock; the 8 GB costs about $280+ now after memory price rises) | 154 | [page] |
| Adafruit BNO085 IMU, $29.50 USD ([Adafruit](https://www.adafruit.com/product/4754)) | 42 | [snippet] |
| 3S 5000 mAh 50C LiPo, XT60 (Ovonic, AUD 46.89 ≈ CAD 43) ([Ovonic](https://www.ovonicshop.com/products/ovonic-11-1v-5000mah-3s-50c-lipo-battery-pack-with-xt60-plug)) | 45 | [page] |
| LiPo balance charger | 45 | [est] |
| 12 V→5 V 5 A buck for the Pi, fuse, power switch, e-stop, XT60s, servo extension cables | 55 | [est] |
| Head camera: Arducam OV9782 global-shutter USB ([Arducam](https://www.arducam.com/120fps-global-shutter-color-usb-camera-board-1mp-ov9782-uvc-webcam-module-with-low-distortion-m12-lens-without-microphones-for-computer-laptop-android-device-and-raspberry-pi-arducam.html); page returned 403) | 55 | [est] |
| 2x cheap wrist USB cameras | 40 | [est] |
| Bearings (608/6804 style), heat-set inserts, M2–M4 screws, shoulder bolts | 60 | [est] |
| Filament | 0 | free at school |
| **Rest subtotal** | **$496** | |

**Totals**
- **Grand total: about $1,473 CAD** before shipping and tax.
- With 13% HST and AliExpress/WowRobo shipping, expect **about $1,600–1,700 CAD landed** [analysis].
- If you need to cut, in this order: drop the wrist cameras (−$40), go 10-DOF legs (−$39), skip the spare servos (−$40).

Compute note [analysis]:
- The Pi 5 runs the walking MLP at 50 Hz and the bus I/O. ToddlerBot runs a Jetson; Open Duck runs a Pi Zero 2W.
- LeRobot ACT / SmolVLA manipulation policies run on the team's laptop GPU over Wi-Fi. That is the normal LeRobot setup.
- A Jetson (about $350+) does not fit the "rest" budget.

### What to do with the InMoov hands (Stage 2)

- Build a **stationary "counter station"**: two larger arms on a fixed stand at counter height, carrying the InMoov hands, driven by the existing ESP32 + PCA9685, with the same LeRobot data pipeline. The hands' life size matches a real kitchen.
- The walker handles floor and fetch tasks. The station handles cook prep.
- This gives you "physical AI in the home" within budget, instead of pretending a $500 leg set can carry adult hands to a counter.
- Stage 2 is **outside** the $1,500.

---

## 5. Walking software path

| Stack | Used by | Notes |
|---|---|---|
| **MuJoCo Playground** (JAX/MJX) | Open Duck ([Open_Duck_Playground](https://github.com/apirrone/Open_Duck_Playground)), Berkeley Humanoid transferred to real hardware ([Playground](https://playground.mujoco.org/)) | Open Duck v2: **300M steps in 1 h 11 min on an RTX 3090**. A usable gait takes about 1–2 h at 4096 envs ([build log](https://github.com/soyeon24/open-duck-mini-v2-build)) [snippet] |
| **ToddlerBot codebase** (MJX + Brax PPO) | ToddlerBot | 3e8 steps, 1024 envs, zero-shot after sysid. Pip-installable, MIT code ([GitHub](https://github.com/hshi74/toddlerbot)). **Best template: same joint layout as our design** |
| **mjlab** (Isaac Lab API on MuJoCo-Warp) | LeRobot Humanoid (lerobot-legged-zoo) | Needs an NVIDIA GPU. Has a `Mjlab-Velocity-Flat-*` humanoid task ([GitHub](https://github.com/mujocolab/mjlab)). Good if you want Isaac Lab ergonomics without Omniverse |
| **Isaac Lab** | Berkeley Humanoid Lite | Heavier install. Best if you later move to BLDC legs |
| Genesis | — | I found no sim-to-real reference for a small Feetech biped [analysis]; don't be the first on a 16-week clock |

**Pipeline** [analysis, based on what ToddlerBot and Open Duck did]:
1. Export the Onshape design to MJCF with onshape-to-robot. Get the masses right by weighing the printed parts.
2. **Motor sysid** on STS3250/3215: step and chirp tests on a test pendulum, then fit the servo's PID, friction and backlash. Open Duck and Microduck use actuator models of this kind. This is where most Feetech sim-to-real failures come from.
3. Train a velocity-tracking PPO policy with domain randomization over mass, friction, latency, Kp and backlash.
4. Export to ONNX and run it on the Pi 5 at 50 Hz. The IMU gives gravity vector and angular velocity; bus reads give joint positions and velocities.
5. Test in a harness, then on the floor.

**Time to first steps [analysis]:**
- A ToddlerBot assembly took 3 days, including printing, for one CS student ([arXiv](https://arxiv.org/html/2502.00893v3)).
- Parts ship from China in about 2–3 weeks.
- Realistic plan:

| Weeks | Work |
|---|---|
| 1–2 | CAD fork + order parts |
| 3–5 | Print, assemble, sysid |
| 4–6 | Build and train the sim model, in parallel with assembly |
| **7–8** | **First RL steps** |
| 9–12 | Arms, teleop, LeRobot datasets (floor tidy, fetch) |
| 13–16 | Imitation-learning policies + demo; Stage-2 counter station if time allows |

- The mech engineer owns the CAD, printing and sysid rig. The software/AI person owns the MJCF, the training and the LeRobot integration.

---

## Sources (primary)
- Berkeley Humanoid Lite: https://arxiv.org/html/2504.17249 · https://github.com/HybridRobotics/Berkeley-Humanoid-Lite · https://lite.berkeley-humanoid.org/
- ToddlerBot: https://arxiv.org/html/2502.00893v3 · https://github.com/hshi74/toddlerbot
- Open Duck Mini: https://github.com/apirrone/Open_Duck_Mini · https://github.com/apirrone/Open_Duck_Playground
- Zeroth-01 / K-Scale: https://github.com/Justin-Riekehof/zeroth-01-build · https://www.humanoidsdaily.com/news/k-scale-labs-cancels-k-bot-orders-open-sources-all-ip-after-funding-fails
- LeRobot Humanoid: https://huggingface.co/blog/VirgileBatto/lerobot-humanoid · https://github.com/huggingface/lerobot-humanoid-hardware
- Feetech: https://shop.wowrobo.com/products/feetech-sts3250-c002-servo-12v-50kg-1-345-servo · https://shop.wowrobo.com/products/feetech-sts3215-servo-12v-30kg-high-torque-servo-for-so-arm100 · https://servodatabase.com/servo/feetech/sts3250 · https://robonine.com/feetech-sts3250-smart-actuator-evaluation-of-accuracy-torque-and-backlash/
- BLDC: https://steadywin-motor.com/products/built-in-star-gear-motor-motor-robot-joint-driver-actuator-controller-motor · https://robstride.com/ · https://www.digikey.com/en/products/detail/stmicroelectronics/B-G431B-ESC1/10321670
- Commercial: https://www.scmp.com/tech/tech-trends/article/3330046/chinese-robotics-start-noetix-debuts-family-friendly-us1400-humanoid · https://humanoid.guide/product/unitree-r1/
- MuJoCo Playground: https://playground.mujoco.org/ · mjlab: https://github.com/mujocolab/mjlab
