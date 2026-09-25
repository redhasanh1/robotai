# robotai v1: both InMoov arms, corrected BOM (stock STLs)

Date: 2026-09-25. Cap: **C$500 for both arms** (pre-tax, excluding what's already owned). Result: **C$452.30 pre-tax** (C$511 with 13% HST).

## Per-joint (per arm x2)

| Joint | InMoov stock servo | Our pick | Fits stock STL? | Qty (both arms) | Unit CAD | Line | URL | Confidence |
|---|---|---|---|---|---|---|---|---|
| Omoplate | HS-805BB, pot pulled out, PivWorm/PivGear | DS5160 60 kg 180deg, pot pulled out | Probably, with a printed spacer (body 48 vs 58 mm tall, same 65x30 footprint) | 2 | 32.84 | 65.68 | aliexpress.com/item/1005005676958064.html | price verified on page; fit inferred |
| Shoulder | HS-805BB on PistonClavi, 0-80 only | DS5160, pot left in | Same | 2 | 32.84 | 65.68 | same | same |
| Rotate | HS-805BB, pot pulled out, RotWorm/RotGear | DS5160, pot pulled out | Same | 2 | 32.84 | 65.68 | same | same |
| Bicep | HS-805BB, pot on the elbow shaft | DS5160, pot pulled out | Same | 2 | 32.84 | 65.68 | same | same |
| Wrist | MG996R (180deg) | MG996R, already owned | Yes (Gael's spec) | 2 | 0 | 0 | amazon.ca/dp/B07MFK266B | owned |
| Fingers x5 | HK15298B (discontinued) | MG996R, already owned | Yes (on Gael's approved list) | 10 | 0 | 0 | amazon.ca/dp/B07MFK266B | owned |

## Purchase list (both arms)

| Item | Product | ASIN / link | Unit | Qty | Line | Confidence |
|---|---|---|---|---|---|---|
| Big servos | DS5160 60 kg, 180deg (**AliExpress, flagged**: Amazon.ca is C$50-57 each) | aliexpress 1005005676958064 | 32.84 | 8 | 262.72 | verified on page, free shipping |
| Arm PSU, 1 per arm @7.4 V | SHNITPWR 12A adjustable | B0CKXW6ZCJ | 36.79 | 2 | 73.58 | from existing bom.json |
| Countersunk M3/M4 + nuts | DYWISHKEY 500 pcs 304 SS | B08QD6TT2N | 35.47 | 1 | 35.47 | verified on search page |
| Spare 10k pots | uxcell WH148 10K, 10 pcs | B07JM62B3Q | 13.99 | 1 | 13.99 | verified on search page |
| 6 mm BBs (232 needed) | Lancer Tactical 4000 bag | B00HC1U0LO | 13.00 | 1 | 13.00 | estimate |
| Servo extensions | 10pc 30 cm JR | B09VGDJ6Z8 | 8.27 | 2 | 16.54 | from phase1 |
| Servo wood screws | M3x12 / 3.5x16 assortment | hardware store | 10.00 | 1 | 10.00 | estimate |
| M8x90-100 bolts + nuts | about 6 | hardware store | 15.00 | 1 | 15.00 | estimate |
| PTFE grease | Super Lube class | Amazon.ca | 12.00 | 1 | 12.00 | estimate |
| **Total** | | | | | **452.30** | |

Optional: 18T round horns B0GR5RSMGL 2x ~C$16 (only if the included arm horn won't mate with the printed gear), bringing the total to C$484.30. Drop-in upgrade: PDI-HV2060MG (B07SW4JCWT, ~C$54 each, confirmed same size as HS-805BB) costs C$432 for 8, which breaks the cap.

## Delete from phase2
- NFP 5840 worm motors x8 (C$632)
- BTS7960 x8 (C$57.52)
- AS5600 x8 (C$27.12)
- Review the STS3215 6-pack: the wrists are now MG996R; the neck still needs servos.

## v1 total
Phase1 hands C$316.40 + phase2 after deletions C$624.85 + arms C$452.30 = **C$1,393.55 pre-tax**, leaving C$106 under C$1,500.

## Key facts
- Standard-size servos don't fit the HS-805BB pockets without adapters. Gael advises against them on omoplate/shoulder/bicep.
- HV2060MG fits the stock parts ("same size no need to modify the STL", inmoov.fr forum).
- The arm uses BB races, not bearings: 27+31 balls (Piv) and 27+31 (Rot) per arm.
- Pot mod applies to omoplate, rotate and bicep. Reuse the servo's own pot on an extension lead. Swap the outer pot wires on the left arm.
- The hand PCA9685s each have 10 free channels, so the big servos go there. No new driver needed.
- Amazon.ca hides prices on the Santa Clara address. Confirm the "estimate" lines in the cart.
