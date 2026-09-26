# Printing at the Seneca Sandbox

Reference for every print we send to Seneca. Source: the Sandbox's own training module and 3D printing pages (September 2026).

## Who and what

- Current Seneca students, staff and faculty only, for academic or course-related projects. Our project is the final-year capstone.
- Free. You must complete the Sandbox's two-part online training module (with a short quiz) first:
  https://infoliteracy.senecapolytechnic.ca/3Dprinting/index.html
- They only accept **.3mf** files from PrusaSlicer.

## The printers

- **Original Prusa MK4S with the HF 0.4 mm (high-flow) nozzle**, at Newnham and SenecaYork. SenecaYork also has an MK3S.
- Bed 250 x 210 mm, max height 220 mm.

## Slicer setup

Option 1: Seneca MyApps (https://myapps.senecapolytechnic.ca), search PrusaSlicer, launch. It already has the Sandbox printer profiles. First time may need AppsAnywhere and Cloudpaging Player installed.

Option 2: your own PrusaSlicer (https://www.prusa3d.com, Software > PrusaSlicer). In the Configuration Wizard:
1. Skip the optional Prusa account login.
2. Configuration Sources: tick **Prusa FFF printers** only.
3. Prusa Research tab: select **Original Prusa MK4S, HF0.4 mm nozzle**.
4. Expert view mode is recommended.

What we use (matches the Sandbox's own example):
- Printer: `Original Prusa MK4S HF0.4 nozzle`
- Print: `0.20mm SPEED @MK4S HF0.4`, then 30% infill and 4 perimeters (InMoov: about 2 mm walls)
- Filament: `Generic PLA @MK4S HF0.4`
- Supports only where Gael marks them (the finger cover). Brim on big flat parts (palm large half, forearm shells).

## Booking rules

- Submit the .3mf through the 3D Print Request form (Seneca login): http://seneca.libwizard.com/id/8bbdd29dba13f10ecd520d63418fce4c
  Staff review the settings, tell you how long to book, and email you. One file per request.
- Max **5 hours of printing per day**. Anything over 4 h 45 needs a staff consult for an extended booking.
- Allow about 10 minutes for setup and cleanup, and stay until the first two layers are down.
- Hours: SenecaYork studios Tue to Fri 8:30 to 4:30 (closed Mondays). Newnham Mon to Thu 8:30 to 4:30. Check https://seneca.libcal.com/hours/ before going.
- Contact: sandbox@senecapolytechnic.ca

## Our plates (right hand, HF0.4 profile)

| Plate | Parts | Time | PLA |
|---|---|---|---|
| RH1 | index, middle, ring, pinky fingers | 2 h 29 | 47 g |
| RH2 | thumb, finger cover (supports), printed bolts | 2 h 48 | 52 g |
| RH3 | palm large half (brim) | 2 h 12 | 61 g |
| RH4 | palm small half, back cover | 2 h 04 | 59 g |
| RH5 | back cover top | 1 h 42 | 48 g |
| **Total** | 11 parts | **11 h 14** | **267 g** |

The .3mf files are built from the InMoov STLs (CC BY-NC, not in this repo) by a local script:
stlmerge.py lays each plate's parts out on the bed, then PrusaSlicer's CLI slices it with a flattened MK4S HF0.4 config
and the exact settings are embedded in the .3mf so the Sandbox sees them. RH1 was first submitted on 2026-09-26
(sliced for the standard 0.4 nozzle; the HF0.4 re-slice above is what to use from now on).

Heads-up for the forearm: robpart5 (the biggest shell) was 4 h 49 on the standard nozzle; re-check it on HF0.4,
and ask for an extended booking if it is still over 4 h 45.
