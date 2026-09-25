# InMoov arm CAD pack (robotai): both arms, right and left

Base design: **InMoov by Gael Langevin**, https://inmoov.fr. License: CC BY-NC 4.0. That is fine for a non-commercial student build. Keep the attribution ("InMoov by Gael Langevin, inmoov.fr") in any repo, poster or report that uses these files.

Collected 2026-09-25. Every file came straight from inmoov.fr's official STL parts library, `https://inmoov.fr/wp-content/uploads/stl/<Category>/<file>.stl`. No zips were involved: the library serves each STL on its own. I did not need Thingiverse or Google Drive, because the inmoov.fr gallery is the canonical, most up-to-date source (Thingiverse holds the older 2012–2014 versions).

## 1. Sources (every URL used)

Build and tutorial pages:
- Hand and Forarm (classic hand): https://inmoov.fr/hand-and-forarm/
- Hand i2: https://inmoov.fr/hand-i2/ and the overview at https://inmoov.fr/inmoov-hand/
- Bicep (elbow and rotate): https://inmoov.fr/bicep/
- Shoulder and Torso (shoulder, rotate ball joints, omoplate, clavicles): https://inmoov.fr/shoulder-and-torso/
- Rotational wrist: http://www.inmoov.fr/rotational-wrist/
- Hardware map and BOM: https://inmoov.fr/default-hardware-map/
- Left hand page, https://inmoov.fr/left-hand/: **returns 404**. The Hand and Forarm page says "The left hand is similar but parts are mirrored", and the gallery has a separate Left-Hand category.
- An omoplate page at https://inmoov.fr/omoplate/ does **not exist** (404). The omoplate is documented inside Shoulder and Torso.

Gallery categories the files came from (parts viewer):
- https://inmoov.fr/inmoov-stl-parts-viewer/?bodyparts=Right-Hand
- https://inmoov.fr/inmoov-stl-parts-viewer/?bodyparts=Left-Hand
- https://inmoov.fr/inmoov-stl-parts-viewer/?bodyparts=i2RightHand
- https://inmoov.fr/inmoov-stl-parts-viewer/?bodyparts=i2LeftHand
- https://inmoov.fr/inmoov-stl-parts-viewer/?bodyparts=Forearm-and-Servo-Bed
- https://inmoov.fr/inmoov-stl-parts-viewer/?bodyparts=Rotation-Wrist
- https://inmoov.fr/inmoov-stl-parts-viewer/?bodyparts=Bicep
- https://inmoov.fr/inmoov-stl-parts-viewer/?bodyparts=Shoulder
- https://inmoov.fr/inmoov-stl-parts-viewer/?bodyparts=Torso
- https://inmoov.fr/inmoov-stl-parts-viewer/?bodyparts=Back (only BackClaviHolderV2 was taken from here)
- Calibrator test piece: https://inmoov.fr/wp-content/uploads/2019/01/Calibrator.stl

Supporting documents, not downloaded:
- JX servo potentiometer extraction guide: https://inmoov.fr/wp-content/uploads/2019/12/HowTo-JX-Servo.pdf
- Servo potentiometer video tutorial: https://inmoov.fr/wp-content/uploads/2013/09/Video-Tuto-Pot-Servo.rar
- 3D assembly views: http://inmoov.fr/bicep-assembly-3d-views/ and http://inmoov.fr/shoulder-torso-and-chest-assembly-3d-view/
- Tendon tensioning: http://www.inmoov.fr/lining-and-tighting-the-tendons/

The exact URL of every single file is recorded in `C:\Users\conno\Tools\inmoov_arm_cad\_download_log.tsv` (HTTP code, folder, file, URL). All 140 downloads returned 200.

## 2. Local folder

Root: `C:\Users\conno\Tools\inmoov_arm_cad\`

| Folder | STLs | MB | Contents |
|---|---|---|---|
| hand_right/classic | 12 | 9.39 | Thumb, Index, Majeure, ringfinger, Auriculaire, Wristlarge/small, topsurface(+UP), coverfinger, Bolt_entretoise, ardiuinosupport |
| hand_left/classic | 11 | 9.34 | Left thumb/cover/topsurface/wrist parts plus the shared fingers |
| hand_right/i2 | 12 | 21.34 | i2 hand, all 3 mounting variants (arm-servo, PDI6225-in-palm, 1109MG adapter) |
| hand_left/i2 | 13 | 21.63 | i2 left-specific parts plus 4 shared parts **copied from right** (FingersX5, FingersTipX5, FingersMoldX5, PulleyX5) |
| forearm_right | 11 | 3.04 | robpart2-5, robcap3, RobServoBed, RobCableFront/Back, RobRing, servo-pulleyX5, TensionerRight |
| forearm_left | 9 | 1.31 | Left robpart2-5, LeftRobCap3, LeftRobServoBed, LeftRobCableFront/Back, LeftTensioner (RobRing and servo-pulleyX5 are shared, see forearm_right) |
| wrist | 8 | 1.44 | RotaWrist1/2/3, WristGears, CableHolderWrist, with Left variants of 1, 2 and CableHolder |
| bicep | 24 | 4.08 | Elbow (HighArmSide, LowArmSide, Piston*, GearHolder, gearpotentio, servobase/holder, spacer, reinforcer, covers, elbowshaftgear) and **the rotate unit** (RotCenter, RotMit, RotTit, RotGear, RotWorm, with Left variants) |
| shoulder | 19 | 2.24 | Piv* shoulder-lift unit (PivCenter, PivMit, PivTit, PivGear, PivWorm, PivConnector, PivPotholder, PivPotentio, with Left variants), servoholder, servoHolster, MyRobotLab logo plates |
| omoplate | 4 | 0.71 | ClaviBack, ClaviFront, PistonClavi, Pistonbase |
| torso_mounts | 11 | 0.19 | HomLowFront/Back, homplate front/back/backlow (+ and -), ChestLow, BackClaviHolder, servoHolster (copy) |
| torso_mounts/torso_frame | 9 | 0.16 | Kinect*/InterKinect* torso frame, Sternum, ThroatLower, arduinosupportmega (the frame the clavicles bolt into) |
| _tools | 1 | 0.01 | Calibrator.stl (print this first) |
| **Total** | **144** | **74.9 MB** | 140 unique downloads plus 4 i2 shared copies |

Every file was checked: all 144 are valid binary STLs, and in each one the triangle count matches the file size. None are HTML error pages.

## 3. Which hand: classic or i2

- **Classic hand** (Hand and Forarm page): the original, most documented design, which thousands of builders have made. It has 5 finger servos in the forearm servo bed, braided-line tendons, and a separate rotational wrist. The Hand and Forarm page now carries this notice: *"I have created a new hand model called i2Hand. I recommend this new model"*.
- **i2 hand**: Gael's current recommendation. The inmoov-hand page describes three ways to mount it:
  1. JX PDI-6225MG-300 servos in the arm. This still uses the classic forearm servo bed, RobCableFront and the RotaWrist parts, which the i2 tutorial references.
  2. PDI-6225MG-300 servos in the palm (`i2_HandPDI6225V2`, `i2_PalmPDI6225V3`). With this option there is *"no need for the forearm or wrist"*.
  3. Small JX-PDI1109MG or SG90 servos in the palm (`i2_Adapter1109MG`), using elastic thread instead of springs.
- I downloaded both. **Suggestion for robotai:** use i2 option 1. It is Gael's current design and it still uses the full forearm and wrist, so the bicep and elbow interface stays the documented one. Use classic if you want the build with the most tutorials and forum answers behind it.
- Version note: the i2 parts list names `i2_FingersX5V1`, but the gallery only serves `i2_FingersX5V2`, which is the one downloaded.

## 4. Per-part table (quantities are per arm; print both the right and left sets)

General print rule from Gael: **print the Calibrator first**. If the parts fit too tightly, set your slicer's horizontal expansion to about -0.15 mm. Material: Gael uses ABS for everything (BOM: about 1.5 kg for both hands and forearms, about 1.5 kg for both arms and shoulders). PLA works but glue differently: Gael names acetone for ABS, and Zap-A-Gap or 2-part epoxy for PLA. No part has a separate material spec.

| Part | Files (R / L) | Qty per arm | Print settings | Hardware needed (per arm) | Source |
|---|---|---|---|---|---|
| Fingers, classic | Index3, Majeure3, ringfinger3, Auriculaire3 (shared R/L); thumb5 / leftthumb5 | 1 each | 30% infill, 1.5 mm walls (thumb: 2 mm), no support, no raft, no brim | 16x M3x20 hinge bolts **or** 3 mm filament pegs (Gael recommends pegs). Silicone fingertips optional | hand-and-forarm |
| Hand/palm, classic | WristlargeV4, WristsmallV4, topsurface6 (+topsurfaceUP6), coverfinger1, Bolt_entretoise7 (all with Left* versions) | 1 each | Wristlarge/small: 30%, 2 mm, no support. coverfinger: 30%, 2 mm, **with support, printed standing up** | 1x M8x80 (Wristlarge to Wristsmall), 1x M8x40 (Wristlarge to thumb), 1x M8x60 (Wristlarge to robpart). The big bolts are **printable** (Bolt_entretoise) | hand-and-forarm |
| Hand, i2 | i2_WristLargeV2, i2_FingersX5V2, i2_FingersTipX5V2, i2_FingersMoldX5V3, i2_CoverFingerV3, i2_HandCoverV1, i2_PalmCoverV2, i2_PulleyX5V1, i2_WristGearV1 (Left: i2_Left*, plus i2_LeftCoverThumbV3) | 1 each | 0.25 mm layers max, 30% infill, 2 mm walls. **No support**: WristLarge, FingersMold, Fingers, WristGear, Pulley. **Support**: CoverFinger, FingersTip, HandCover, PalmCover | 6x JX PDI-6225MG-300 (5 fingers + wrist), 25x M3x16 countersunk, 5x M3x4 countersunk, 1x M3x12 countersunk, 5x M1.5x4 flat head, 5x extension springs 4.8x44.5 mm (3/16"x1-3/4"), 3 m braided line 0.8 mm 200 lb, 3 m PTFE tube ID1.5/OD2.5, 16-wire ribbon 3 m. Optional sensors: 5x AH3503 Hall sensors and 5x 2.5x1 mm magnets | hand-i2 |
| Forearm and servo bed | robpart2V4-5V4, robcap3V2, RobServoBedV6, RobCableFrontV3, RobCableBackV3, RobRingV3, servo-pulleyX5, TensionerRightV1 (Left*: robpart2-5, RobCap3, ServoBed, CableFront/Back, Tensioner; RobRing and pulleyX5 shared) | 1 each (servo-pulleyX5 is one plate of 5 pulleys) | robpart2-5: 30%, 2 mm, **brim**, no support, no raft | Classic: **5x HK15298B** finger servos. M3 nuts caged in robpart5. 5x extension springs about 0.5 cm OD x 1 to 2 cm (13/64"x13/16"; a commenter notes 13/16" is actually 2 cm) for the tensioner. Braided line 0.8 mm **200 lb**, 10 pieces x 75 cm per hand (not nylon, because it stretches). Small tubing for tendon routing. Rubber silentblocs for the servos | hand-and-forarm |
| Wrist rotation | RotaWrist1V4, RotaWrist2V3, RotaWrist3V3 (shared), WristGearsV5 (shared), CableHolderWristV5 (Left: LeftRotawrist1V4, LeftRotaWrist2V3, LeftCableHolderWristV5) | 1 each | 30%, 2 mm, no raft, no brim, no support. "Gears at best quality your printer can give" | **1x MG996R** (BOM; the wrist page says MG995, and i2 uses a PDI-6225MG). 1x M3x12 (main gear to RotaWrist3). Redrill with 2.5 mm and 8 mm bits | hand-and-forarm, rotational-wrist |
| Elbow and forearm link | elbowshaftgearV1, robcap3V2 / LeftRobCap3V2, Bolt_entretoise7 | 1 | 30%, 2.5 mm walls | Uses the printed bolt | bicep |
| Bicep (elbow lift) | GearHolderV1, HighArmSideV3 (x2), LowArmSideV3 (x2), ReinforcerV2 (x2), PistonanticlockV2, PistonbaseantiV2, gearpotentioV1, servobaseV1, servoholderV1, spacerV1, armtopcover1/2/3, RibonPusherV1, PivPotentioRound/SquareV3 (x2, pick the one that matches your pot) | as listed (x2 where noted) | 30% infill, **2.5 mm walls**, 0.3 mm layers, 2 mm top/bottom, no support, no raft, **brim** on big parts. Gears optionally 50% infill | **1x HS-805BB** (alternatives: PDI-HV2060MG, JX-PDI2060MG, TowerPro TS-80). The potentiometer is pulled out of the servo and extended 25 to 30 cm. Grease | bicep |
| Rotate (upper-arm twist) | RotcenterV3, RotMitV3, RotTitV4, RotGearV6, RotWormV5 (Left: LeftRotcenterV3, LeftRotTitV4) | 1 each | 30%, 2.5 mm, brim | **1x HS-805BB**. **27x 6 mm balls** (RotCenter) and **31x 6 mm balls** (RotMit). 4x wood screws 3.5x16. M3x30 x4 (RotCenter), M3x30 x2 (RotMit adjusters), M3x20 x2 (RotMit sides) | bicep and shoulder-and-torso |
| Shoulder (lift) | PivcenterV3, PivMitV2, PivTitV3, PivGearV6, PivWormV5, PivConnectorV1 (x2), PivPotentioRound/SquareV3/V4 (x2), PivPotholderV3 or SquareV1, servoholderV1 (Left: LeftPivcenter, LeftPivMit, LeftPivTit, LeftPivPotholder(Square)) | as listed | 30%, 2.5 mm, brim. **Add support** to PivMit and PivTit | **1x HS-805BB**. **27x 6 mm balls** (PivCenter) and **31x 6 mm balls** (PivMit). 4 M3 nuts in PivCenter, M3x35 hex (PivTit to PivCenter), 4x wood screws 3.5x16, 1x M3x30 (PivMit adjuster), 2x M3x20 side screws, 8 mm chrome shaft | shoulder-and-torso |
| Omoplate (shoulder blade) | ClaviBackV2, ClaviFrontV2, PistonClaviV3, PistonbaseV6, servoHolsterV1 (in shoulder/) | 1 each | 30%, 2.5 mm, brim. **Add support** to servoHolster. If PistonClavi binds in Pistonbase, scale X/Y down by 0.1 to 0.2 mm | **1x HS-805BB** (Arduino pin 11, rest position 10, keep it within 0 to 80). 4x wood screws 3.5x16, 4x M3x12 hex (PistonClavi to the servo horn), potentiometer on PivPotholder | shoulder-and-torso |
| Arm-to-torso mounting | Clavi parts (above) bolt to the torso: HomLowFront (x2), HomLowBack (x2), homplatefront+/-, homplateback+/-, homplatebacklow+/-, ChestLow (x2), BackClaviHolderV2, plus the torso_frame Kinect* parts | torso-level (2x where noted) | 30%, 2.5 mm, brim | **1x M8x90** screw per side (shoulder to Clavi). Gael (2019): "yes you still need to print those [homplate] parts" | shoulder-and-torso |

Left/right notes:
- Parts with no "Left" version are shared, so print them twice (once per arm). That covers the finger shells, RobRing, servo-pulleyX5, RotaWrist3, WristGears, all Piston* parts, the GearHolder, PivGear, PivWorm and PivConnector.
- The Clavi and Piston omoplate parts have **no Left variant** in the gallery. Check them in the 3D assembly view before printing the left side. They may need mirroring in the slicer.

## 5. Consolidated hardware for BOTH arms

**Servos**
| Servo | Classic hand build | i2 hand build (option 1) |
|---|---|---|
| Hitec HS-805BB (bicep, rotate, shoulder, omoplate: 4 per arm) | **8** | **8** |
| HobbyKing HK15298B (fingers, 5 per hand) | **10** | 0 |
| MG996R (wrist, 1 per arm) | **2** | 0 |
| JX PDI-6225MG-300 (5 fingers + wrist per hand) | 0 | **12** |

This matches Gael's BOM: "Hands and forearms: 10x HK15298B, 2x MG996R" and "Arms and shoulders: 8 Hitec HS805BB".

**Bearings.** InMoov uses **no ball-bearing races** (no 608ZZ or similar) in the arm. The shoulder and rotate joints are grease-packed ball joints filled with loose **6 mm balls**. Use steel balls; plastic BB-gun balls can be dissolved by some greases.
- Per arm: PivCenter 27 + PivMit 31 + RotCenter 27 + RotMit 31 = **116**
- **Both arms: 232 x 6 mm steel balls.** Buy about 250 to allow for spares.

**Bolts and screws** (both arms, from the page counts):
- M8: 2x M8x90 (shoulder to Clavi). Classic hand also needs 2x M8x80, 2x M8x40 and 2x M8x60, **or** print Bolt_entretoise.
- M3x20: 32 for the classic finger hinges, **or** use filament pegs. Plus about 8 side screws for the shoulder and rotate.
- M3x30: about 14. M3x35 hex: about 8 (PivTit). M3x12: about 10 (PistonClavi plus wrist).
- Wood screws 3.5x16: about 24 (servo mounts).
- M3 nuts: about 30.
- Gael's general stock list: about 50 M3x20 countersunk, 100 M3x12 flat head, 50 M4x20, 15 M8x100.
- i2 hands add: 50x M3x16 countersunk, 10x M3x4, 2x M3x12, 10x M1.5x4.

**Rods.** One 8 mm chrome shaft per shoulder (PivCenter).

**Springs**
- Classic: 10 extension springs, about 0.5 cm OD x 1 to 2 cm.
- i2: 10 springs, 4.8 x 44.5 mm.

**Braided line.** 0.8 mm braided fishing line rated **200 lb** (not nylon): about 15 m for 2 classic hands (20 x 75 cm), or 6 m for 2 i2 hands. i2 also needs 6 m of PTFE tube, ID 1.5 / OD 2.5.

**Other**
- Potentiometers are the ones pulled from each HS-805BB, 4 per arm. Round or square type, about 13 mm diameter. Choose the matching PivPotentioRound or PivPotentioSquare holder.
- Ribbon cable: 14-conductor 28 AWG.
- Grease that is safe for plastics.
- Acetone or epoxy for gluing.
- The Arm breakout board / Nervo Board, which is electronics and not part of this pack.

**Filament.** Per Gael's BOM, about 3 kg ABS for both hands, forearms, arms and shoulders.

## 6. Print hours

**No print-time estimate is given** on any of the inmoov.fr pages I checked: Hand and Forarm, Hand i2, Bicep, Shoulder and Torso, Rotational Wrist and the Hardware BOM. The only figures are filament weights (see section 5). Slice the folders in your own slicer to get a time for your printer.

## 7. Parts I could NOT get

- **ShoulderConnect**: listed as "1x shoulderconnect" in the shoulder parts list. It holds the Arm breakout board. It is **not in the free gallery**; a builder confirmed on the Shoulder page (Dec 2018) that "the piece is not available for free it is in the Inmoov shop". I did not buy it. It is a small board holder, so you can model a replacement bracket.
- **Left-hand tutorial page**: returns 404. That doesn't matter, because the Left-Hand gallery category has all the files.
- **Dedicated omoplate page**: does not exist. The omoplate is covered in Shoulder and Torso, and its parts are in `omoplate/`.
- **Separate STLs for printed finger pegs**: none exist. Gael says to cut 3 mm filament instead.
- **Thingiverse and Google Drive**: not used. inmoov.fr's own library links none of them for these parts, and it is the current source.
