"""Sort the downloaded InMoov arm STLs into ready-to-print folders with a checklist.

python tools/make_print_folders.py [cad_folder]
Creates <cad_folder>/PRINT_right_arm, PRINT_left_arm, PRINT_torso_mounts with numbered sections, file names
prefixed with the quantity to print (e.g. "x2__HighArmSideV3.stl"), and PRINT_LIST.md (settings + checklist).
Classic InMoov hand (fits the owned MG996R finger servos). InMoov by Gael Langevin, CC BY-NC (non-commercial).
"""
import shutil
import sys
from pathlib import Path

CAD = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\conno\Tools\inmoov_arm_cad")

# section -> list of (source folder, file, qty, note)
RIGHT = {
    "1_hand": [("hand_right/classic", f, 1, "") for f in (
        "thumb5.stl", "Index3.stl", "Majeure3.stl", "ringfinger3.stl", "Auriculaire3.stl", "WristlargeV4.stl",
        "WristsmallV4.stl", "topsurface6.stl", "topsurfaceUP6.stl")] + [
        ("hand_right/classic", "coverfinger1.stl", 1, "print standing up, WITH support"),
        ("hand_right/classic", "Bolt_entretoise7.stl", 1, "printed bolts (replace M8x80/40/60)")],
    "2_forearm": [("forearm_right", f, 1, "brim" if f.startswith("robpart") else "") for f in (
        "robpart2V4.stl", "robpart3V4.stl", "robpart4V4.stl", "robpart5V4.stl", "robcap3V2.stl", "RobServoBedV6.stl",
        "RobCableFrontV3.stl", "RobCableBackV3.stl", "RobRingV3.stl", "servo-pulleyX5.stl", "TensionerRightV1.stl")],
    "3_wrist": [("wrist", f, 1, "gears at best quality" if "Gear" in f else "") for f in (
        "RotaWrist1V4.stl", "RotaWrist2V3.stl", "RotaWrist3V3.stl", "WristGearsV5.stl", "CableHolderWristV5.stl")],
    "4_elbow_bicep": [("bicep", f, q, n) for f, q, n in (
        ("elbowshaftgearV1.stl", 1, ""), ("GearHolderV1.stl", 1, ""), ("HighArmSideV3.stl", 2, "brim"),
        ("LowArmSideV3.stl", 2, "brim"), ("ReinforcerV2.stl", 2, ""), ("PistonanticlockV2.stl", 1, ""),
        ("PistonbaseantiV2.stl", 1, ""), ("gearpotentioV1.stl", 1, ""), ("servobaseV1.stl", 1, ""),
        ("servoholderV1.stl", 1, ""), ("spacerV1.stl", 1, ""), ("armtopcover1.stl", 1, ""), ("armtopcover2.stl", 1, ""),
        ("armtopcover3.stl", 1, ""), ("RibonPusherV1.stl", 1, ""),
        ("PivPotentioRoundV3.stl", 1, "pick Round OR Square to match your pot"))],
    "5_rotate": [("bicep", f, 1, "brim") for f in (
        "RotcenterV3.stl", "RotMitV3.stl", "RotTitV4.stl", "RotGearV6.stl", "RotWormV5.stl")],
    "6_shoulder": [("shoulder", f, q, n) for f, q, n in (
        ("PivcenterV3.stl", 1, "brim"), ("PivMitV2.stl", 1, "WITH support"), ("PivTitV3.stl", 1, "WITH support"),
        ("PivGearV6.stl", 1, ""), ("PivWormV5.stl", 1, "fine layers"), ("PivConnectorV1.stl", 2, ""),
        ("PivPotentioRoundV3.stl", 2, "pick Round OR Square to match your pot"), ("PivPotholderV3.stl", 1, ""),
        ("servoholderV1.stl", 1, ""))],
    "7_omoplate": [("omoplate", f, 1, "brim") for f in (
        "ClaviBackV2.stl", "ClaviFrontV2.stl", "PistonClaviV3.stl", "PistonbaseV6.stl")] + [
        ("shoulder", "servoHolsterV1.stl", 1, "WITH support")],
}


def left_of(right):
    """Left arm = right arm with Left* files swapped in where InMoov provides them."""
    swap = {
        "hand_right/classic": "hand_left/classic",
        "forearm_right": "forearm_left",
    }
    left = {}
    for sec, items in right.items():
        out = []
        for folder, f, q, n in items:
            lf = swap.get(folder, folder)
            cands = [f, "Left" + f, "left" + f, "Left" + f[0].upper() + f[1:], "LeftRob" + f[3:] if f.startswith("Rob") else None,
                     "Left" + f.replace("V4", "V4"), "Left" + f.replace("Right", "")]
            if f == "TensionerRightV1.stl":
                cands = ["LeftTensionerV1.stl"] + cands
            if f == "RotaWrist2V3.stl":
                cands = ["LeftRotaWrist2V3.stl"] + cands
            if f == "RotaWrist1V4.stl":
                cands = ["LeftRotawrist1V4.stl"] + cands
            hit = None
            for c in [c for c in cands if c]:
                for base in (CAD / lf, CAD / folder):
                    for real in base.glob("*.stl"):
                        if real.name.lower() == ("left" + f).lower() or real.name.lower() == c.lower():
                            if real.name.lower().startswith("left") or c == f:
                                hit = hit or real
            # prefer an explicit Left* file anywhere in the folder, else the shared file
            explicit = [r for base in (CAD / lf, CAD / folder) for r in base.glob("*.stl")
                        if r.name.lower().startswith("left") and r.name.lower().replace("left", "", 1) == f.lower()]
            src = explicit[0] if explicit else (hit or (CAD / lf / f if (CAD / lf / f).exists() else CAD / folder / f))
            out.append((src, q, n + (" (shared part, same as right)" if not src.name.lower().startswith("left") else "")))
        left[sec] = out
    return left


def resolve(right):
    return {sec: [(CAD / folder / f, q, n) for folder, f, q, n in items] for sec, items in right.items()}


def write(name, plan, lines):
    root = CAD / name
    if root.exists():
        shutil.rmtree(root)
    lines.append(f"\n## {name}\n")
    total = 0
    for sec, items in plan.items():
        d = root / sec
        d.mkdir(parents=True)
        lines.append(f"\n### {sec}\n")
        for src, q, note in items:
            if not src.exists():
                lines.append(f"- [ ] MISSING: {src.name}")
                continue
            shutil.copy2(src, d / f"x{q}__{src.name}")
            total += q
            lines.append(f"- [ ] {q} x `{src.name}`" + (f"  ({note.strip()})" if note.strip() else ""))
    lines.append(f"\n**{total} prints in {name}**")
    return total


lines = ["# InMoov arm print list (robotai)", "",
         "Print `_tools/Calibrator.stl` first. Settings (Gael Langevin): PLA or ABS, 0.3 mm layers (0.2 for gears/worms),",
         "30% infill, 2 mm walls on the hand/forearm (1.5 mm on classic fingers), 2.5 mm walls on elbow/shoulder/omoplate,",
         "brim on big parts, support only where marked. ~3 kg filament for both arms.",
         "File names start with the quantity to print (x2__ = print two).", ""]
tot = write("PRINT_right_arm", resolve(RIGHT), lines)
tot += write("PRINT_left_arm", left_of(RIGHT), lines)
torso = {"torso_mounts": [(p, 2 if p.name.startswith(("HomLow", "ChestLow")) else 1, "") for p in sorted((CAD / "torso_mounts").glob("*.stl"))
                          if p.name != "servoHolsterV1.stl"]}
tot += write("PRINT_torso_mounts", torso, lines)
lines.append(f"\n**Total: {tot} prints.**")
(CAD / "PRINT_LIST.md").write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
