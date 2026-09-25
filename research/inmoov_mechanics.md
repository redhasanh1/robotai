# InMoov mechanics — how Gael actually does it, and what we copy / change for robotai

Research date: 2026-09-25. Every fact carries a URL. Where a number is my estimate (not sourced) it is marked **[est.]**.
Sources are inmoov.fr build pages, the InMoov Google Group, MyRobotLab, SwanRobotics, a 2015 university thesis that rebuilt the upper body, and one builder's print-tracking spreadsheet. Thingiverse pages block scraping, so remix facts come from search snippets and are marked as such.

Context on the original: InMoov was started in 2011/2012 by French sculptor Gaël Langevin, licensed CC-BY-NC, every part fits a 12x12x12 cm print volume, controlled by MyRobotLab (Java) on Arduino Megas (https://en.wikipedia.org/wiki/InMoov). Gael's own headline: "an average cost is under 1500 euros for the whole robot, including servos, Nervo Boards and accessories", excluding computer, wheels and printer (https://groups.google.com/d/topic/inmoov/ZcarOFYsVbU). The thesis counts "32 hobby servos" and "two Arduino Mega boards" for the published upper body (https://repositori.udl.cat/server/api/core/bitstreams/c52b5719-e48a-4132-87ed-0745f9f1bc79/content).

---

## 1. Full joint list with Gael's servo, mechanism, and range

Servo models below are from the Default Hardware Map + BOM (https://inmoov.fr/default-hardware-map/) unless noted. The "Nervo board" is an Arduino Mega shield that fans out up to 19 servos per side; a full robot needs two sets (https://inmoov.fr/product/nervo-board/, https://inmoov.fr/nervo-board-tutorial/).

| # | Joint (MRL name) | Servo Gael specifies | Mechanism | Range / notes | Source |
|---|---|---|---|---|---|
| 1 | Head yaw (`rothead`) | 1x Hitec HS-805BB (PDI-HV2060MG alt.) | Servo horn screwed to printed `ServoGear`, meshing printed `MainGear` on `NeckHinge`; greased spur pair, no pot hack | servo set to 90 at assembly; full servo 180 minus mechanical stops | https://inmoov.fr/neck-and-jaw/ |
| 2 | Head pitch (`neck`) | 1x HS-805BB | `ThroatPiston` + `ThroatPistonBase` crank-slider from a servo in the torso, 8 mm bolt at the hinge | servo at 90 = head level; limited stroke | https://inmoov.fr/neck-and-jaw/ |
| 3 | Head roll (`rollNeck`, optional) | 2x HK15298B "1 master, 1 slave" | second-generation tilt neck, two servos mirrored | optional; BOM lists it as "Neck tilting" | https://inmoov.fr/default-hardware-map/ |
| 4 | Jaw (`jaw`) | 1x HK15298B (never MG995: "their controller board is terrible. They burn much too easily") | `JawPiston` in `JawHinge` with 1 cm offset, servo set to 0 with hinge at 90° | **"the jaw servo can only turn from 0 to 20°... if more it might break something"** | https://inmoov.fr/neck-and-jaw/ |
| 5 | Eyes X (`eyeX`) | 1x DS929HV (SG92R / HXT900 cheap alts.) | printed linkage, pivots deliberately offset "to avoid a cross-eyed appearance" | default limits eyeX 60-100 | https://inmoov.fr/eye-mechanism/ |
| 6 | Eyes Y (`eyeY`) | 1x DS929HV | same linkage, other axis | eyeY 50-100, "start with small range degree movements, especially for the up and down" | https://inmoov.fr/eye-mechanism/ |
| 7 | Cameras | Hercules Twist HD or MS LifeCam HD-3000 (OAK-D-Lite listed in newer BOM) | webcam PCB pulled out of its case, lens pressed into the eyeball | "only one camera is required for vision tracking" | https://inmoov.fr/eye-mechanism/, https://inmoov.fr/head-3/ |
| 8 | Torso side-bend (`topStom`) | 2x HS-805BB, one with pot extracted, both on one signal | `TStoPistonRight/Left` pistons + `StomGear`/`StoGearAttach`, sits on a printed ball race of "approximately 50 to 60 balls of 6mm diameter... Steel or plastic for BB Gun" | side-to-side bend of the upper torso | https://inmoov.fr/top-stomach/ |
| 9 | Torso rotation (`midStom`) | 2x HS-805BB (or HK15338), one hacked, reversed polarity so they turn opposite ways | two printed worm gears `MidWormRightV1` driving `StomGear`; 65-70 x 6 mm BBs as a turntable bearing; "put a good load of grease on the wormgears" | yaw of the whole upper body; Vigor VSD-11AYMB rejected because "they won't detach properly through software" | https://inmoov.fr/mid-stomach/ |
| 10 | Torso forward bend (`lowStom`) | not motorised in Gael's release; community linear actuators exist (mayaway M8x100 piston, 76 mm travel) | — | — | https://www.thingiverse.com/thing:3743426 (snippet) |
| 11 | Omoplate (`omoplate`, arm abduction) | 1x HS-805BB, **pot extracted** | printed `PivWorm` on the servo horn driving printed `PivGear`; pot sits in `PivPotholder` at the joint centre; race of "27 balls" (+ "31 balls" second race) of 6 mm BBs | MRL default `omoplate.map(10,70,10,70)`; rest 10 | https://inmoov.fr/shoulder-and-torso/, https://myrobotlab.org/content/help-minimal-arm-script-and-mrl-please |
| 12 | Shoulder flexion (`shoulder`) | 1x HS-805BB | `PistonClavi` + `Pistonbase` crank-slider inside `ClaviBack/ClaviFront` | **"The servo actuating PistonClavi should stay between 0 and 80 position, if you go further it will certainly break"**; MRL `shoulder.map(0,180,30,100)`; rest 33 | https://inmoov.fr/shoulder-and-torso/ |
| 13 | Upper-arm rotation (`rotate`) | 1x HS-805BB, pot extracted (pot measured "4.74 kohms") | `RotWormV5` on servo horn driving `RotGearV6`, `RotMit` lets it multi-turn; `RotCenter` carries the pot | MRL `rotate.map(46,180,50,150)`; rest 90; test "in 10-degree increments" | https://inmoov.fr/bicep/ |
| 14 | Elbow (`bicep`) | 1x HS-805BB, pot extracted onto the elbow shaft (`gearpotentio`) | servo gear into `ElbowShaftGear`, `GearHolder` "is simply clipped" | "up to 90 degrees... all depends on the gap you have set"; MRL `bicep.map(5,60,30,80)` / `setMinMax(5,95)` | https://inmoov.fr/bicep/, https://inmoov.fr/build-yourself/bicep-assembly-3d-views/ |
| 15 | Wrist rotation (`wrist`) | 1x MG996R (180° servo required; "The HK15298 only rotates of 90 degrees") | small printed gear on a cut servo horn driving the large `RotaWrist` gear, greased, 8 mm x 6 cm bolt as axle | "Due to the gear ratio used, the RotaWrist achieves only a total of 90 degrees of rotation" when centred; a remix gives full 180 | https://inmoov.fr/build-yours/hand-and-forarm-v2/, https://www.thingiverse.com/thing:534333 (snippet) |
| 16-20 | Five fingers (`thumb, index, majeure, ringFinger, pinky`) | 5x HK15298B per hand (20 kg·cm "Strong torque"); preference order today: JX PDI-6221MG > HK15298B > MG996R > MG946R > MG995 | forearm servo bed; each servo horn carries a `ServoPulley`/`RobRing`; **two tendons per finger** (one over the top, one under) of 200 lb braided line on the same pulley — agonist/antagonist on one servo, no spring in the base design | one servo per finger, ~90° servo travel closes the finger; thumb has only 2 tendon paths like the others | https://inmoov.fr/default-hardware-map/, https://inmoov.fr/finger-starter/, https://inmoov.fr/build-yours/hand-and-forarm-v2/ |

Servo spec sheet for the two workhorses:
- HS-805BB: 19.8 kg·cm @4.8 V, **24.7 kg·cm @6 V**, 0.14 s/60°, 152 g, 66x30x58 mm, nylon gears, ~USD 45-50, **CAD 50 at Canada Robotix (sold out)** (https://servodatabase.com/servo/hitec/hs-805bb, https://www.canadarobotix.com/products/415).
- HK15298B: 18 kg·cm @6 V, 20 kg·cm @7.4 V, 66 g, coreless, **discontinued** (https://servodatabase.com/servo/hobbyking/hk15298b).

Counting: 2 arms x (omoplate + shoulder + rotate + bicep) = 8 HS-805BB, + 2 head + 2 topStom + 2 midStom = 12-14 HS-805BB; 10 finger servos + 2 wrist + 1 jaw + 2 eyes + (2 rollNeck) = 15-17 small servos. That matches the BOM's "8 Hitec HS805BB = 240 euros" for arms and "10x servos HK15298B = 180 euros" for hands (https://inmoov.fr/default-hardware-map/).

---

## 2. The shoulder: omoplate and shoulder joints

**How it is driven.** Each shoulder cylinder "contains a gear with a worm drive related to the servo" and Gael "extracted the potentiometer of the servo and fix it in the center of the cylinder" (https://inmoov.fr/inmoov-robot-shoulder/). The right-shoulder parts list is: ClaviBack, ClaviFront, PistonClavi, Pistonbase, 2x PivConnector, PivGear, PivMit, PivCenter, 2x PivPotentio, PivPotholder, PivTit, PivWorm, servoHolster, servoholder, shoulderconnect (https://inmoov.fr/shoulder-and-torso/). So:
- **Omoplate (abduction)** = HS-805BB → `PivWorm` (worm, printed) → `PivGear` (worm wheel, printed) with a 6 mm BB race (27 balls, 31 in the second race) and an 8 mm x 90 mm through-bolt joining shoulder to Clavi parts.
- **Shoulder (flexion)** = HS-805BB in the clavicle driving `PistonClavi`, a crank-slider, hard-limited to servo 0-80.

**Why the pot comes out.** "Telling the servo to rotate 90 degrees does not yield a 90-degree rotation in the arm. Extracting the potentiometer and mounting it on the gearbox allows angle measurement at the gearbox rather than the servo shaft" (https://myrobotlab.org/content/inmoov-myrobotlab-and-notes-hs-805bb-potentiometer-extraction). The servo's stop tab is Dremeled off so it can multi-turn; the pot goes into a printed holder on the joint axis with 25-35 cm of extension wire; polarity is reversed for the left side (https://swanrobotics.com/servo-hack/, https://inmoov.fr/shoulder-and-torso/). Bicep page rule: "Do not de-solder the potentiometer wires from the PCB of the servo, just cut them and solder the extra length" (https://inmoov.fr/bicep/).

**Ratio.** Gael does not publish tooth counts anywhere I could find; the STL is the spec. The worm is single-start (it is printed vertically with support, and is the part every builder has to file), so the ratio equals the wheel tooth count — visually ~30-40:1 on `PivGear` **[est.]**. With HS-805BB at 24.7 kg·cm and even a 30:1 worm at ~30% printed-worm efficiency, that is ~200+ kg·cm at the joint, which is why "these servos are amazing for the strength they provide" (https://inmoov.fr/inmoov-robot-shoulder/).

**Why it holds without power.** The gearboxes "have two functions: one is to increase the torque rate and second is to lock the arm in position, thus releasing the servo from working and using power source" (https://www.thingiverse.com/thing:48678, ForrestHiggs alternative worm gear — from search snippet). A single-start worm cannot be back-driven, so the arm stays up when servos are detached, and the servo does not stall-heat holding a pose.

**Known problems (from builders).**
- Friction: "3D printed wormgears have way too much friction, especially with much force"; "the shoulder gear can touch the outer ring under force, and the wormgear never stays perfectly centered on the servo" (https://inmoov.fr/inmoov-robot-shoulder/ comments, via search).
- Worm end collision: gear teeth hit "the top of the spiral of the worm" and again at the bottom going the other way; fix is filing the worm end (https://swanrobotics.com/schoulder-inmoov/, https://inmoov.fr/sketch-3d-shoulder/ comments).
- Pot destruction: "The potentiometers can be damaged very easily... broken a lot of potentiometers" — over-rotation kills them; builders swap in 10 kΩ linear 270° pots and add mechanical stops (https://myrobotlab.org/content/inmoov-myrobotlab-and-notes-hs-805bb-potentiometer-extraction, https://inmoov.fr/bicep/).
- Fried servos: builders "had to replace HS-805BB servos in their shoulder and bicep after they were fried"; digital giant-scale replacements whine when stationary (https://synthiam.com/Community/Questions/Terrible-Whine-From-Hs-5805mg-Giant-Scale-Metal-Gear-Digital-3961, https://myrobotlab.org/content/and-so-it-begins-my-ongoing-inmoov-build-log).
- Gael's own warning: a 20 kg servo on the omoplate "will get tired and hot and will die sooner"; on his 4th build he uses 12x PDI-HV2060MG (48-62 kg·cm) for "biceps, shoulder, and torque-intensive joints" (https://groups.google.com/g/inmoov/c/iheGxJuvPcY).
- Bearing alignment: cstidham "corrected the 3D model's bearing journal alignments and added a little extra clearance... used stainless ball bearings and packed the cavities with synthetic grease" (https://www.thingiverse.com/thing:3371371, snippet). Others replaced the BB race with a real ball bearing (https://www.thingiverse.com/thing:1876443) or reinforced the frame (https://www.thingiverse.com/thing:1347747).
- Grease caution: "Some grease tint the printed parts or even dissolve the BBGun balls" (https://inmoov.fr/shoulder-and-torso/).

**Payload.** Gael: "1,5kg at extended arm (more or less depending on the material used to print)" (https://groups.google.com/g/inmoov/c/dmzvy2MHceA). A student paper claims 5 kg max but that is structural, not a lift test (https://www.ijraset.com/research-paper/inmoov-robotic-arm-for-performing-various-operations). With undersized servos, "don't expect the arm to lift anything more than its own arm" (https://groups.google.com/g/inmoov/c/iheGxJuvPcY). Gael: "The arms are heavy on the small gears of the servos. I would not recommend replacing with standard servos the omoplate servo, shoulder servo and bicep servo" (https://groups.google.com/g/inmoov/c/T22_oZCZsTk).

---

## 3. Bicep rotation, elbow, forearm, wrist

**Rotate (upper-arm twist).** Same worm pattern as the omoplate: `RotWormV5` on the HS-805BB horn drives `RotGearV6`; `RotMit` lets it multi-turn; extracted pot sits in `RotCenterV3`. Alternatives that "work similarly": Tower Pro TS-80, JX PDI-2060MG (https://inmoov.fr/bicep/). The thesis: the shoulder "is similar to the upper part of the bicep. It contains the same worm gear mechanism" (https://repositori.udl.cat/server/api/core/bitstreams/c52b5719-e48a-4132-87ed-0745f9f1bc79/content).

**Elbow (bicep).** HS-805BB with pot moved to the elbow shaft (`gearpotentio`), spur from the servo horn gear into `ElbowShaftGear`; `GearHolder` "is simply clipped, if for some reason it doesn't hold very well, you can add a screw or some hot glue"; align "the rectangle of ElbowShaftGear with the rectangle of RobCap" (https://inmoov.fr/build-yourself/bicep-assembly-3d-views/). Range ~90° and pot needs the servo to turn more than 180 ("The Bicep servo has to rotate more than 180 degrees that is why the pot has to be removed", https://synthiam.com/Community/Questions/Inmoov-bicep-servo-question-17834). Cheaper 25 kg BETU servos on Amazon "proved effective for lifting the forearm" (https://groups.google.com/g/inmoov/c/T22_oZCZsTk). Bicep printed part list per side (Cochran's tracker): 24 parts including GearHolder, 2x HighArmSide, Pistonanticlock, Pistonbaseanti, RotGear, RotMit, RotPotentio, RotTit, RotWorm, Rotcenter, 3x armtopcover, elbowshaftgear, gearpotentio, 2x lowarmside, 2x reinforcer, servobase, servoholder, spacer (https://synthiam.com/uploads/user/9B549C4DF0F8E1BE4AE204F29F78C354/PrintStatusInmoov-636311251823088871.pdf).

**Forearm and hand.** 5 servos on a printed `RobServoBed` with rubber silent-blocs, HK15298B (90°) or MG946R (180°); "Cut 10 pieces of 75cm long of braided fish line 200LB. Don't use standard nylon because it stretches"; two lines per finger routed "upper rods run through the upper parts of the fingers, run the lower rods through the lower parts"; knots at the fingertip with a drop of cyanoacrylate; finger hinges pinned with 3 mm filament ("cheap, easy, and strong enough"), outer holes drilled 3 mm, inner 3.2-3.5 mm; segments glued with acetone (ABS) or epoxy (PLA) (https://inmoov.fr/build-yours/hand-and-forarm-v2/, https://inmoov.fr/finger-starter/, https://inmoov.fr/lining-and-tighting-the-tendons/). Torque loss: "A lot of torque is lost in the length path of the tendons" (https://inmoov.fr/default-hardware-map/).
- Springs: the base hand has none — the extensor line on the same pulley opens the finger. The BOM does list "10x extension springs (0.51mm diameter, 1cm length)" and Gael showed a tensioner where "the tubes are simply glued to the springs with SuperGlue... it works like that since about 8 months" (https://groups.google.com/g/inmoov/c/m1GSNi3hzU, https://inmoov.fr/default-hardware-map/). The newer **Hand i2** goes fully to 6x JX-6225MG (300°) in the forearm, tendons in PTFE tubes, springs for passive return, and a Hall sensor (AH3503 + 2.5x1 mm magnet) in each silicone fingertip (https://inmoov.fr/hand-i2/).

**Wrist.** MG996R/MG995 with a small gear on a cut horn driving the big `RotaWrist` gear; three perimeter screws; ~90° net at the hand with the stock ratio, 180° with the remix (https://inmoov.fr/rotational-wrist/, https://inmoov.fr/build-yours/hand-and-forarm-v2/).

---

## 4. Torso, stand, arm attachment, power

**Structure.** The torso is a printed shell: 2x KinectSideHolder, 2x KinectSideBack, KinectMidFront, KinectMidBack, 2x InterKinectSide, 2x InterKinectMid, 2x HomLowFront, 2x HomLowBack, 2x ChestLow, plus sternum/throat/back plates (https://inmoov.fr/shoulder-and-torso/). Cochran's tracker lists Torso 22 parts, Top Stomach 31, Mid Stomach 12, Lower Stomach 4, Back 27, Chest 11 (https://synthiam.com/uploads/user/9B549C4DF0F8E1BE4AE204F29F78C354/PrintStatusInmoov-636311251823088871.pdf). Print settings on every page: "30% infill, 2.5mm wall thickness, no raft, no support (unless specified), use brim for large parts", 0.3 mm layers, "threaded bolts for 3D parts" and wood screws for servos; a printed calibrator first, slicer horizontal expansion "-0.15 is a great place to start" (https://inmoov.fr/shoulder-and-torso/, https://inmoov.fr/head-3/, https://inmoov.fr/top-stomach/).

**Arm attachment.** The shoulder cylinder bolts to the Clavi parts "with a 8mm, 90mm length screw"; two 14-conductor 28 AWG ribbon cables per arm are folded at ~30 cm and routed through the `PivGear` channel (https://inmoov.fr/shoulder-and-torso/). Ribbon lengths from the Nervo board: neck 10 cm, head 55 cm, arm 75 cm, hand 90 cm, finger sensors 120 cm, stomach 30 cm (https://inmoov.fr/default-hardware-map/).

**topStom / midStom.** See rows 8-9 above: topStom = side bend on a 50-60 BB race; midStom = yaw via two printed worms on `StomGear` on a 65-70 BB race, two HS-805BB paired on one channel with one pot (https://inmoov.fr/top-stomach/, https://inmoov.fr/mid-stomach/). The stand is the `TStoFrontStand`/`TStoBackStand` parts under the top stomach (parts list, Cochran PDF). Legs as published "are designed for standing only and are not motorized" (https://inmoov.fr/inmoov-legs-for-printing/ via search).

**Weight.** Gael does not publish a number. The thesis's full upper-body BOM prints from ~5 kg of ABS (1.5 kg arms + 1.5 kg hands/forearms + 2 kg head/torso at 30% infill) (https://repositori.udl.cat/server/api/core/bitstreams/c52b5719-e48a-4132-87ed-0745f9f1bc79/content); add ~14 x 152 g big servos (2.1 kg), ~15 x 66 g (1 kg), bolts, cables, boards: **~9-11 kg upper body [est.]**.

**Power.** "A 60Amps 6V power supply is suitable to power the whole robot, though Gael recommends not going lower than 40Amps"; a 20 A 6 V unit "sometimes shuts down due to peak consumption"; Gael's own: 6 V 50 A, or cheap 6 V 60 A from eBay, plus per-servo capacitors on weaker supplies (https://groups.google.com/g/inmoov/c/3jwBqoN-H6g, https://inmoov.fr/power-supply-robot-head-printed/). BOM alternatives: "1x Battery 6V12AH + battery charger 6V1.5A: 35 euros" or an adjustable 5 V 50 A supply turned up to 6 V (https://inmoov.fr/default-hardware-map/). Topology: two Arduino Megas, each with a Nervo shield; "A 6V20A power supply supplies only the Nervo boards" in the tutorial rig; grounds tied between Arduino and Nervo (https://inmoov.fr/nervo-board-tutorial/). The EZ-Robot kit ships a "7.5V 20A supply" instead (https://www.ez-robot.com/store/p93/ez-inmoov-humanoid-robot-hardware-kit.html).

---

## 5. Head

- **Skull**: two printed groups, "Skull and ears" and "Face and Jaw", mechanisms installed before closing; Cochran's list: EyeMask, EyeSupport, Internal_MainBase, Internal_RaiserBlock, Internal_ServoBase, Internal_TopMount, JawArmLeft/Right, JawBeam, JawWashers, JawWormGear, Neck_Gear, NeckGear_RetainingCollar, Servo_NeckGear, Skull_Bottom, Skull_Jaw, Skull_Top, 2x Ears (https://inmoov.fr/head-3/, Cochran PDF).
- **Jaw**: HK15298B, 0-20° only (https://inmoov.fr/neck-and-jaw/).
- **Eyes**: 2 servos (DS929HV; SG92R budget), X/Y linkage with offset pivots, camera PCB inside the eyeball, "the camera black ribbon needing to pass through the bottom hole of the eye socket"; Eyes i2 adds eyelids and syncs to the original eyeX/eyeY in MRL (https://inmoov.fr/eye-mechanism/, https://inmoov.fr/eyes-i2/ via search).
- **Neck yaw (rothead)**: HS-805BB → `ServoGear` → `MainGear`, greased spur, servo at 90 when the horn is fitted (https://inmoov.fr/neck-and-jaw/).
- **Neck pitch (neck)**: HS-805BB in the torso driving `ThroatPiston` to `NeckHinge` with an 8 mm bolt (https://inmoov.fr/neck-and-jaw/). Original 2013 neck used "the same servos as for the shoulder and biceps"; Gael said 11 kg·cm "should do the trick" (https://inmoov.fr/neck-for-inmoov/).
- **Extras**: 2x 8 Ω 10 W mini speakers, 6 V mini amp, PIR sensor, NeoPixel ring (https://inmoov.fr/default-hardware-map/).

---

## 6. Printing: material, settings, part counts, hours

- Material: Gael prints ABS (first shoulders in green ABS because white was out of stock) and glues with acetone; PLA builders use epoxy and "a hot air gun to get parts warmed up to get them to fit easier" (https://inmoov.fr/inmoov-robot-shoulder/, https://inmoov.fr/shoulder-and-torso/).
- Settings: 30% infill, 2.5 mm walls (thesis: 3 shells), 0.3 mm layers, no raft, brim on big parts; **pistons at 75-100% infill**, **worms need support**; worm builders go to 0.05-0.15 mm layers for the worm (https://repositori.udl.cat/server/api/core/bitstreams/c52b5719-e48a-4132-87ed-0745f9f1bc79/content, https://inmoov.fr/shoulder-and-torso/, https://inmoov.fr/inmoov-robot-shoulder/ comments via search).
- Every part fits 12x12x12 cm and "all of my parts are totally designed to be set on a 3D printer mainly without support" (https://inmoov.fr/printing-parts/).
- **Counts and hours (measured, not marketing):**
  - Thesis (2015, upper body with hands, head, torso, shoulders, arms): table of **158 STL files**, per-part minutes summing to **16,605 min ≈ 277 h** at 0.3 mm/30% (the text says "16.605 hours" but the column is minutes) (https://repositori.udl.cat/server/api/core/bitstreams/c52b5719-e48a-4132-87ed-0745f9f1bc79/content).
  - David Cochran's tracker (2017, two Flashforge Creator Pros, 0.2 mm, ABS, with raft+support): **231 total parts** for skull, eyes, face/jaw, mod-neck, torso, both shoulders, both biceps, both forearms/hands, top/mid/low stomach, back, chest, new hands; 204 printed at 88% after **25 print days**, **4.1 kg ABS used**, ~$370 total print cost, est. 56.7 days total (https://synthiam.com/uploads/user/9B549C4DF0F8E1BE4AE204F29F78C354/PrintStatusInmoov-636311251823088871.pdf).
  - Gael: "approximately two weeks for experienced builders using a single home printer; several months for beginners" (https://groups.google.com/g/inmoov/c/dmzvy2MHceA).
  - Per-part times from the thesis table: big torso/shell parts 100-240 min each (Robpart2 240, ClaviBack 180, PivMit 180, RotGear 130), gears/worms 60-130, finger segments 20 min.
- **Load-bearing parts**: PivGear/PivWorm and RotGear/RotWorm (worm sets), PistonClavi/Pistonbase and TStoPistons (100% infill), ClaviBack/Front, HighArmSide/LowArmSide + reinforcers, ElbowShaftGear, StomGear + MidWorms, the BB races. Everything else is shell.

---

## 7. Known weaknesses, best fixes, InMoov2, and the cost in CAD

**Weaknesses reported** (sources in section 2 plus):
1. Servo obsolescence: HS-805BB and HK15298B are discontinued; "We had trouble finding the specified servos, as they are no longer sold" (https://inmoov.fr/community-v2/).
2. Pot-hack fragility and left/right polarity errors ("The two outside wires on potentiometer should be switched", https://swanrobotics.com/schoulder-inmoov/).
3. Printed worm friction, worm-end collision, BB-race misalignment, grease dissolving BBs.
4. Stall heat: servos hold poses under gravity on non-worm joints (shoulder piston, elbow spur) and cook; MG996R has a power-on jerk (https://groups.google.com/g/inmoov/c/iheGxJuvPcY).
5. Tendon stretch and re-tensioning; torque loss along the tendon path.
6. Wiring mass: 14-wire ribbons per limb, two Megas, two Nervo sets (~$73-110 each), a 6 V 40-60 A supply (https://groups.google.com/g/inmoov/c/klYOj7n_18o).

**Best community fixes**: PDI-HV2060MG (48-62 kg·cm) on omoplate/shoulder/bicep and PDI-6221MG on fingers — Gael's current choice; CYS-S8218 (38-42 kg·cm) on the waist "without the power-up jerk problems of MG996R" (https://groups.google.com/g/inmoov/c/iheGxJuvPcY); real ball bearings in the shoulder (thing:1876443, thing:4484020); re-aligned bearing journals (thing:3371371); alansrobotlab stronger shoulder/bicep frames (thing:1347747, thing:1347113); 180° wrist remix (thing:534333); planetary-gear elbow printed at "100% infill and high detail" in ABS or nylon for EZ-Robot servos (https://synthiam.com/Community/Questions/Inmoov-bicep-servo-question-17834); spring tensioners on tendons; Hand i2 with Hall fingertips (https://inmoov.fr/hand-i2/); Nervo boards replaced by Mega + PCA9685 for budget builds (https://groups.google.com/g/inmoov/c/klYOj7n_18o).

**InMoov2 / i2**: mostly software (MRL "InMoov2" splits the service into head/hand/shoulder services, https://myrobotlab.org/content/inmoov-20) plus i2 hardware refreshes: Hand i2, Head i2, Eyes i2 with eyelids, a beta new shoulder (https://inmoov.fr/community-v2/, https://inmoov.fr/headi2/). Control alternatives: MyRobotLab (free, Java, Python scripting) or EZ-Robot ARC with EZ-B v4 and their USD 2,799.99 hardware kit (https://www.ez-robot.com/store/p93/ez-inmoov-humanoid-robot-hardware-kit.html).

**Cost of a classic InMoov upper body, converted to CAD** (1 EUR ≈ 1.50 CAD, 1 USD ≈ 1.37 CAD **[est.]**):
- Thesis total of purchasable parts: **1,201 €** (hands/forearms 262 €, arms/shoulders 259 €, head/torso 466 € incl. Kinect and 3 batteries, stomach 95 €, misc 119 €) ≈ **CAD 1,800** (https://repositori.udl.cat/server/api/core/bitstreams/c52b5719-e48a-4132-87ed-0745f9f1bc79/content).
- Gael: "under 1500 euros for the whole robot" ≈ CAD 2,250; a Spanish builder: >2,000 € ≈ CAD 3,000 with import taxes (https://groups.google.com/d/topic/inmoov/ZcarOFYsVbU).
- Line items today: HS-805BB CAD 50 each x 12-14 = CAD 600-700; PDI-HV2060MG ~CAD 60-70 each **[est.]**; PDI-6221MG ~CAD 25 **[est.]**; MG996R ~CAD 12 **[est.]**; 2 Arduino Mega ~CAD 80-100; 2 Nervo sets ~CAD 250-300; 6 V 50-60 A PSU ~CAD 80-120; filament 5 kg (free for us); bolts/BBs/line/grease ~CAD 100. **Classic BOM in CAD: ~1,500-1,900 with Gael's current servos.**

---

## 8. Our design: same topology, fewer parts, modern bus servos where they earn it

### The principle
InMoov's whole pot-extraction hack exists because a hobby servo (a) stops at 180° and (b) measures its own shaft, not the joint. A Feetech STS/HLS bus servo is a 360° multi-turn absolute encoder servo (12-bit, 0.088°, feeds back position/speed/load/voltage/temperature over one 3-wire daisy chain) (https://www.feetechrc.com/2020-05-13_56655.html, https://www.waveshare.com/wiki/ST3215_Servo). So **we keep Gael's printed worm where self-locking matters, but drive it with a multi-turn bus servo and command it in servo-turns** — the extracted pot, pot holder, pot bracket, extension wires, servo surgery and the left/right polarity trap all disappear, and the joint angle is still known exactly because the servo counts turns. Where InMoov uses a spur pair or a piston with the pot still in the servo (wrist, rothead, neck, jaw, eyes, fingers), a bus servo simply drops in.

Servo family, CAD prices (Canadian retail where found):
- **STS3215 12 V, 30 kg·cm, 0.222 s/60°: CAD 37.65** at RobotShop CA; 7.4 V 19.5 kg·cm variant CAD 40.71 (https://ca.robotshop.com/products/feetech-12v-30kgcm-magnetic-encoding-servo-sts3215, https://ca.robotshop.com/products/magnetic-encoding-servo-sts3215-74v-19kgcm). Same 45x25x35 mm body as a standard servo, so it fits InMoov's finger bed and wrist with a bracket tweak.
- **STS3250 12 V, 50 kg·cm, 0.133 s/60°, 74.5 g, aluminium case, coreless, 6-12 V**: USD 48-55 ≈ **CAD 70-80 [est.]** (https://servodatabase.com/servo/feetech/sts3250, https://www.aliexpress.com/s/wiki-ssr/article/feetech-sts3250-price_1005006523697779). Same footprint as STS3215.
- HLS3625M 7.4 V 25 kg·cm "constant force" (for grippers) exists (https://lxrcmodel.com/product/feetech-hls3625m-7-4v-25kg-double-shaft-constant-force-serial-bus-servo-for-lectric-hand-gripper-robot/); not needed if we stay 12 V.
- Bus driver: Waveshare Bus Servo Adapter (A) / FE-URT-1, controls up to 253 servos on one chain, USD ~27 ≈ CAD 40 **[est.]** (https://www.waveshare.com/wiki/Bus_Servo_Adapter_(A)). Two chains (left, right) into a Raspberry Pi or laptop replace 2 Megas + 2 Nervo sets + ribbons.
- Proven at scale: SO-ARM100/101 (LeRobot) uses 6x STS3215 as a whole arm (https://wiki.seeedstudio.com/lerobot_so100m/).

Rule for choosing: **worm stays where gravity loads the joint and we want it to hold with power off (omoplate, shoulder, elbow, torso yaw). Direct or spur drive where the load is light or the joint is short-stroke (rotate, wrist, head, jaw, eyes, fingers).** Printed worm ratio ~30:1 on a 50 kg·cm servo gives >400 kg·cm theoretical, so we can afford a smaller, cheaper wheel than Gael's if we keep ~20:1.

### Per-joint table

| Joint | InMoov way | Our way | Why | Printed-part count change (per joint) | Rough CAD cost (servo + hw) |
|---|---|---|---|---|---|
| Omoplate (abduction) | HS-805BB, pot extracted into PivPotholder, PivWorm→PivGear, 27+31 BB race, 8x90 bolt | **Keep worm.** STS3250 in multi-turn mode on the same PivWorm/PivGear geometry (re-modelled around the 45x25 mm body), one 6806-size thin bearing instead of loose BBs | Self-locking holds the arm up unpowered; encoder counts turns so no pot; 50 kg·cm in vs 24.7 | 14 → ~9 (drop PivPotentio x2, PivPotholder, PivTit, servoholder; bearing replaces BB race) | CAD 75 servo + 8 bearing + bolts ≈ 90 |
| Shoulder (flexion) | HS-805BB + PistonClavi crank, hard-limited 0-80, breaks past that | **Second copy of the same worm module** turned 90°, STS3250 | Gael's weakest joint (limited stroke, servo holds gravity, breaks); reusing one module means one design to debug | ~6 (Clavi shells + piston + base + servoholder) → ~9 as a module, but it is the *same* module as omoplate: zero new designs | ≈ 90 |
| Rotate (upper-arm twist) | HS-805BB pot-extracted, RotWorm→RotGear, RotMit, RotCenter | **STS3215 direct on a printed 3:1 spur** (or the worm module if the elbow will carry loads while bent) | Load on this axis is small; no need to hold unpowered; removes a whole worm set and pot | ~8 → ~4 | CAD 38 + bolts ≈ 45 |
| Elbow (bicep) | HS-805BB pot on elbow shaft, spur into ElbowShaftGear, ~90° | **Keep a worm** (third copy of the module) with STS3250 | Forearm+hand ≈ 1 kg at ~25 cm ≈ 25 kg·cm — Gael's servo is at its limit; worm gives headroom and holds a pose cold | ~12 (gears, gearpotentio, holders, HighArmSide x2...) → ~9 | ≈ 90 |
| Wrist rotation | MG996R, small gear on cut horn → RotaWrist gear, ~90° net | STS3215 on the existing RotaWrist gear pair, 1:1 or the 180° remix ratio | Drop-in; 360° encoder means full rotation is possible | 4 → 4 | ≈ 45 |
| Fingers x5 | 5x HK15298B on a servo bed, 2 tendons per finger on one pulley, 200 lb braid | **5x STS3215 7.4 V or 12 V** on a simplified bed, keep Gael's finger STLs and tendon routing exactly; add the BOM's 0.51 mm extension springs in the tensioner | Fingers are InMoov's most proven sub-assembly — do not redesign. Bus servos give load feedback = grip sensing for free (replaces the Hall-sensor i2 fingers). One 3-wire chain replaces the 14-wire ribbon | forearm ~10 parts + fingers ~15: unchanged (maybe -2 cable holders) | 5 x 38 = 190 + line/springs 15 ≈ 205 per hand |
| Head yaw (rothead) | HS-805BB → ServoGear → MainGear spur | STS3215 on the same spur | Light load; drop-in | 3 → 3 | ≈ 45 |
| Head pitch (neck) | HS-805BB + ThroatPiston | STS3215 + ThroatPiston (keep) | Short stroke, works | 3 → 3 | ≈ 45 |
| Head roll (rollNeck) | 2x HK15298B master/slave (optional) | **Omit for v1** | 16-week budget; add later | -6 | 0 |
| Jaw | HK15298B, 0-20° | STS3215 (or a CAD 20 STS3032) with software limit 0-20 | Drop-in | unchanged | 20-38 |
| Eyes X/Y | 2x DS929HV, offset-pivot linkage, webcam in eyeball | **Keep as-is** with 2x MG90S-class PWM on a CAD 8 PCA9685, or 2x STS3032 to stay all-bus | Gael's eye linkage is good and cheap; camera-in-eye is the InMoov look the owner wants | unchanged (~12) | 10-40 + camera 40 |
| Torso yaw (midStom) | 2x HS-805BB paired, 2 printed worms on StomGear, 65-70 BB turntable | **One STS3250 + one printed worm on StomGear, lazy-susan bearing** | One servo instead of a hacked pair; worm keeps the upper body from swinging; a CAD 15 steel lazy-susan replaces the BB race | 12 → ~7 | 75 + 15 ≈ 90 |
| Torso side-bend (topStom) | 2x HS-805BB paired + pistons on a 50-60 BB race | **Fixed (no servo) for v1**: print TStom parts as a solid stand | Saves 2 big servos and ~10 parts; nobody notices in a demo | 31 → ~20 | 0 |
| Torso fwd bend (lowStom) | not motorised | not motorised | same as Gael | — | 0 |
| Electronics | 2x Arduino Mega + 2x Nervo sets + 14-wire ribbons + 6 V 40-60 A | 2x bus adapters (left/right chains) + Pi/laptop, 12 V 30 A supply, 3-wire daisy chain through the PivGear channel | Removes two boards, two shields, ~10 ribbon cables; every servo reports load/temperature so we can detect stalls in software instead of frying servos | — | 80 + PSU 45 |

**Totals for our v1 (head + torso yaw + two full arms with hands):**
- Servos: 6x STS3250 (2 omoplate, 2 shoulder, 2 elbow) + 1 STS3250 (midStom) = 7 x CAD 75 = 525; STS3215: 2 rotate + 2 wrist + 10 fingers + rothead + neck + jaw = 17 x CAD 38 = 646; eyes ≈ 20. **≈ CAD 1,190 servos.**
- Adapters 80, PSU 45, camera 40, bearings/lazy-susan 40, bolts/BBs/line/springs/grease 100. **≈ CAD 1,500 all-in, printing free.** That is level with a classic InMoov in CAD (1,500-1,900) but with 24 servos instead of ~30, no servo surgery, no Nervo boards, and joint feedback everywhere.
- Printed parts: classic upper body ≈ 231 (Cochran) → ours ≈ 170-185 **[est.]** by deleting the pot parts (x4 per arm), pair-servo parts in the stomach, topStom mechanism and rollNeck, while adding nothing new except one reusable worm module.

**One design to own: the worm module.** Servo cradle for the 45x25x35 mm STS body, single-start printed worm (0.1 mm layers, 100% infill, PETG or ABS), a ~20-30 tooth wheel, a 6806 or 6808 thin-section bearing (CAD 5-8), two shell halves. Printed four times per arm side (omoplate, shoulder, elbow) plus once in the torso = 7 copies. The "no museum kernels" rule applies here too: the module must be test-fitted on the omoplate by week 4 or the whole plan slips.

**Honest risks for two students in 16 weeks.**
- Print time: ~277 h at 0.3 mm for the classic upper body (thesis); ours is fewer parts but PETG at 0.2 mm is slower — plan **300-350 h of printer time [est.]**, i.e. two printers running from week 1 to week 7.
- The printed worm is still the failure point (friction, end-collision, filing). Mitigation: 0.1 mm layers, print the worm vertical, file the ends, grease with PTFE grease that does not attack the plastic, run-in 30 min unloaded as SwanRobotics does (https://swanrobotics.com/schoulder-inmoov/). A machined brass worm on an 8 mm shaft is the plan B.
- STS3250 at 12 V draws several amps at stall; one 12 V 30 A supply and software torque limits (the servo reports load) replace Gael's 6 V 60 A brick.
- Fishing-line hands take a full weekend per hand to tension; Gael's tutorial pages are the manual, do not "improve" them.
- The 1.5 kg extended-arm payload Gael quotes is with 24.7 kg·cm servos; with 50 kg·cm through the same worm we can expect similar or better, but the printed ClaviBack/Front shells and the 8 mm through-bolt, not the servo, become the limit — keep Gael's 8 mm bolt scheme.

**Build order (topology copied from Gael's own tutorials):** finger starter (1 day, proves tendon workflow) → one full hand+forearm → worm module prototype on a bench with an STS3250 → right omoplate+shoulder+bicep → left arm (copies) → torso shell + midStom → head with eyes/jaw → integration on the bus. This mirrors Gael's "You don't have to do a complete inmoov at once... Start with just the head (requires 3-4 servos)" advice, but starts with the hand because that is the part the owner will show first (https://groups.google.com/g/inmoov/c/klYOj7n_18o).
