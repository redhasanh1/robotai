# Kimi round 2 (senior build manager) - humanoid-with-legs pivot - 2026-09-25

Inputs: owner's pick (humanoid with legs, C$500 arms / C$500 legs / C$500 rest, unlimited printing), round-1 price corrections, the Cerebras thesis, the reference photo (InMoov-style forearm + tendon hand), and the legs worker's finding (servo walker capped at ~0.62 m / 4.2 kg; photo arms at 0.75 kg each can't mount on it).

## Options Kimi weighed
- **A. Life-size torso + photo arms on a hoverboard-drive base, with passive casters (not self-balancing).** Recommended.
- **B. Stand-only torso (static, ALOHA-style station).** About C$850, but it can't fetch. Kept as the week-3 milestone on the way to A.
- **C. Hoverboard-motor legs.** 15-40 Nm through printed 6-9:1 planetaries on paper, but C$150-250 per joint, ODrive/VESC drivers at C$60-150 each, 3+ kg per leg and 1-3° backlash. No published sub-C$2k example. That's v2, not a 16-week plan.
- **D. Used/refurb actuators.** Used XM430s run C$150+ each; used hobby servos are a lottery. The only real used-market win is the hoverboard.

## Recommendation: "Torso-first, legs at a week-10 gate"
- **v1 (weeks 1-16):** life-size torso + both photo arms on the hoverboard base. It's the only sub-C$1,500 layout that does the mission (cooking prep, tidying, fetching) with the owner's arms, and all five Cerebras unlocks demo on manipulation.
- **Walking, in parallel:** RL in MJX/mjlab against the 0.62 m servo-biped design. The deliverable is a walking policy + a sim2real plan.
- **Week-10 gate:** if the torso is on schedule and ≥C$400 is left, build the 0.62 m biped as a separate small robot (two STS3215 6-packs + 3S LiPo + printed Open-Duck-derived legs, ~C$388), sharing the Pi, IMU and cameras. Those legs can never carry the life-size torso.

## Kimi's tables (CAD, pre-tax; many rows still estimates)
**Arms (C$523.42):**
- 4x 12V worm-gear motors, 100 kg·cm + encoder, for shoulder pitch/roll: C$50 each, estimate
- 2x 60 kg·cm worm-gear motors for the elbows: C$40 each, estimate
- STS3215 6-pack for wrist rotation, neck and spares: C$166.42, verified
- 7x AS5600 encoders: C$21
- 7x BTS7960 H-bridges: C$56, estimate
- Forearms, hands, MG996R pods, PCA9685 and ESP32: already owned

**Base (C$195, C$305 reserved for the legs gate):**
- Used hoverboard from Kijiji: ~C$120, estimate
- EFeru hoverboard-firmware-hack-FOC: free
- 36V to 12V 20A buck: C$25
- Casters: C$20
- E-stop, fuses, XT60: C$30

**Rest (C$290.85):**
- 2x Waveshare servo adapters: C$13.98
- EMEET C960: C$34.99
- 2x wrist cams: C$24
- BNO085 IMU: C$30
- Pi Zero 2 W: C$25
- Powered hub: C$65
- 5264 cables: C$13.44
- Screws and inserts: C$27
- Clamps: C$17.44
- Misc wiring: C$35
- Tethered PSUs: owned
- Phone teleop: free

**Totals:** v1 C$1,009.27, leaving C$491. With the legs gate, C$1,397.11.

## Kimi's least-sure list
1. Worm-gear "100 kg·cm" ratings are stall figures, with 1-2° backlash and no torque feedback. Shoulder margin at full extension is ~7 Nm needed vs ~9.8 claimed. Bench-test one first.
2. The hoverboard mainboard revision has to match what the EFeru firmware supports.
3. Tip-over risk: a tall torso on a ~40 cm track.
4. Worm-gear joints in LeRobot need a custom ESP32 driver.
5. The US$13.99 STS3215 listing is unverified.
6. The Zeroth repo is unmaintained; Open Duck Mini is the maintained path.
7. Two-robot schedule risk.
