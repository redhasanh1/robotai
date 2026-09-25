# Kimi round 1 (senior build manager) - 2026-09-25

Brief: unlimited free school 3D printing, so print everything printable. Cheapest GOOD LeRobot-compatible build, shipped to Toronto, in CAD.
Kimi's own confidence labels are kept as it gave them. Claude's verification is in round1_verification.md.

## Decisions
- **Print:** all arm, leader and head structure, wrist-cam mounts, cable chains, cart adapters, and the omni wheels (TPU rollers + PETG hubs; VEX 4" at ~$42 as fallback). Hand: the Amazing Hand (8x SCS0009, ~$110) rather than InMoov, as a week-13+ stretch.
- **Don't print** arm-joint reducers. PLA/PETG cycloidals have 1-3° of backlash, worse than the STS3215's stock gears.
- **Power:** skip the Anker C300. Run tethered from the two Phase 1 SHNITPWR 10A PSUs set to 12V. For untethered use, the CUKTECH 15 PB200P (US$57.99) has dual 12V PD output (3A + 2.5A) on its spec sheet.
- **Skip** the RealSense D415 and the Pi 5 (~$154 CAD after 2026 price rises); use a laptop.
- **Head cam:** EMEET C960 (~$42) instead of a C920 (~$92).
- **Leaders:** phone teleop (LeRobot native, iOS HEBI / Android WebXR) plus a gamepad, for $0. Fallback 1: one STS3215 leader (~$104). Fallback 2: an AS5600 encoder leader (~$25, needs custom driver code). One phone drives only one arm, though, so bimanual demos need 2 phones, a leader + a phone, or 2 leaders.
- **Servos:** STS3215 12V from AliExpress at US$12.33. STS3250 50 kg-cm (US$15.98) on both shoulder-pitch joints, the best-value upgrade. Avoid Feetech RSBL, Damiao, MyActuator and printed cycloidal + BLDC. Mitigate backlash with TPU pads, slow acceleration, and later an AhaRobot-style dual-motor bias.

## Table (Kimi, CAD at an assumed 1 USD = 1.40)
| Part | B/P | Product | Vendor | URL | CAD | Qty | Line | Kimi confidence |
|---|---|---|---|---|---|---|---|---|
| Arm servos | Buy | STS3215 12V 30kg | AliExpress | https://www.aliexpress.com/item/1005012720505797.html | 17.26 | 12 | 207.12 | snippet |
| Shoulder | Buy | STS3250 12V 50kg | AliExpress | https://www.aliexpress.com/i/1005012735598453.html | 22.37 | 2 | 44.74 | snippet |
| Base wheels | Buy | STS3215 "360 cont." 4-pack | AliExpress | https://www.aliexpress.com/item/1005009400013739.html | 38.23 | 1 | 38.23 | snippet, verify variant |
| Head | Buy | STS3215 12V | AliExpress | (same as arm) | 17.26 | 2 | 34.52 | snippet |
| Driver boards | Buy | Waveshare Bus Servo Adapter (A) | Waveshare | https://www.waveshare.com/bus-servo-adapter-a.htm | 6.99 | 2 | 13.98 | verified |
| Servo cables | Buy | 5264 3P 10-pack | AliExpress | https://www.aliexpress.com/item/1005008074862037.html | 6.72 | 2 | 13.44 | snippet |
| Cart | Buy | IKEA RÅSKOG (large) | IKEA CA | https://www.ikea.com/ca/en/p/raskog-utility-cart-white-30586783/ | 39.99 | 1 | 39.99 | estimate |
| Structures, omni wheels | Print | PETG/PLA/TPU | school | - | 0 | - | 0 | - |
| Tethered power | Own | Phase 1 PSUs @12V + DC5521 pigtails | Amazon.ca | (search URL) | 10.00 | 1 | 10.00 | estimate |
| Battery (opt.) | Buy | CUKTECH 15 PB200P | AliExpress | https://www.aliexpress.com/item/1005006132215500.html | 81.19 | 1 | 81.19 | snippet |
| PD trigger cables (opt.) | Buy | USB-C PD to DC5521 12V | Amazon.ca | (search URL) | 12.59 | 2 | 25.18 | estimate |
| Head cam | Buy | EMEET C960 | Amazon | https://www.amazon.com/clp/B0CJHZ92P6 | 42.00 | 1 | 42.00 | snippet |
| Wrist cams | Buy | generic 1080p wide USB | AliExpress | (search URL) | 12.00 | 2 | 24.00 | estimate |
| USB hub | Buy | 7-port USB 3 | Amazon.ca | (search URL) | 22.39 | 1 | 22.39 | estimate |
| Table clamps | Buy | pair | Amazon.ca | (search URL) | 12.59 | 1 | 12.59 | estimate |
| Hardware | Buy | M3/M4 + heat-set inserts | Amazon.ca | (search URL) | 15.00 | 1 | 15.00 | estimate |
| Teleop | Free | LeRobot phone teleop | HF docs | https://huggingface.co/docs/lerobot/en/phone_teleop | 0 | - | 0 | verified |
| Leader (opt.) | Buy | 6x STS3215 | AliExpress | (same as arm) | 17.26 | 6 | 103.56 | snippet |
| Amazing Hand (stretch) | Buy+Print | 8x SCS0009 | AliExpress | https://github.com/pollen-robotics/AmazingHand | 12.60 | 8 | 100.80 | estimate |

Totals, pre-tax (Kimi): core ~$520; + battery + PD cables ~$626; everything ~$830. Official path ~$1,300+.

## Kimi's least-sure list
1. The US$6.83/pc STS3215 4-pack may be a different variant; wheels only, and bench-test first.
2. AliExpress STS3215 counterfeits: buy from listings with 100+ sold.
3. Large RÅSKOG stock in Canada ("last chance").
4. CUKTECH PB200P availability in Canada (the 15 SE's dual 12V output is unverified).
5. The FX rate and HST on AliExpress orders (+13%).
6. Wrist-cam quality (want UVC MJPEG 1080p30).
7. Phone teleop for bimanual work.
8. SCS0009 price and the Amazing Hand wrist adapter.
