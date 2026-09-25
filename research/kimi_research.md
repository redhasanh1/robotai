# Kimi (K3, high effort) research pass - 2026-09-25

Source: kimi.ai chat "Robot Build & AI Policy", run by Claude in Hasan's logged-in browser, K3 model with web search
(5 search rounds, ~170 results). Kimi's inline citations are REF tags in its UI and did not survive text export,
so **treat every number below as a claim** until it's checked against `physical_ai_research.md`, which links a URL for every figure.

## Cross-check vs. our sourced research

| Topic | Kimi | Our brief | Status |
|---|---|---|---|
| Best platform | XLeRobot, "not close" | XLeRobot | **Agree** |
| XLeRobot cost | ~$660 self-sourced; WowRobo 0.4.0 kit $349 | $660 BOM; WowRobo $349 listing **sold out** 2026-09-25 | Agree on price. Kit availability is the risk |
| InMoov hand on SO-101 | "mostly a dealbreaker": ~400 g limit, no forearm room for MG996Rs, and MG996R (~10 kg-cm) is weaker than the arm's STS3215 (30 kg-cm) | Don't mount initially | **Agree**. Kimi adds the no-forearm-volume point |
| Dexterous hand | Amazing Hand only, as a month-4 stretch | Amazing Hand if any | Agree |
| Policies | ACT → SmolVLA → pi0.5-DROID; skip OpenVLA-OFT/GR00T | ACT → SmolVLA → pi0.5/GR00T | Agree |
| SmolVLA fine-tune | ~4 h on one L4, 22 GB VRAM | laptop inference ~2 GB | Complementary, **unverified** |
| Cerebras role | System-2 VLM every 1-2 s (Hi Robot style) + VLM success judge + voice + code-as-policy; motor loop stays local | Same split | **Agree** |
| Fast-reasoning evidence | Hi Robot: +34% instruction accuracy, +19% task progress vs flat; RTC robust to +200 ms latency; **no paper isolates System-2 speed as the variable** | Hi Robot ~1 Hz replanning | New: this gap is a paper opportunity |
| Backflips | "Unitree R1 ($5,900) backflip-capable" | R1 = cartwheels/handstands; **G1 (~$13.5k+) for backflip** | **Conflict**: our sourced brief is more specific. Either way, not feasible |
| Cooking | Prep only: fetch ingredients, hold bowl, slow stir; no knives/heat/liquids | sandwich/pour/stir/plate | Agree (Kimi is stricter on liquids) |
| New arm to know | Seeed reBot Arm B601-DM ~$1k, 1.5 kg payload, brushless | not covered | **Unverified**. Worth a look if SO-101 payload bites |
| Parts total | ~$900-950 USD (~$1,250 CAD) XLeRobot-kit based | ~$1,045 USD (arms + LeKiwi + cams + Jetson) | Same ballpark |

## Things Kimi added that we should act on
1. **Order in week 1.** China lead times are 2-4 weeks to Toronto, and the WowRobo price excludes Canadian import fees.
2. **STS3215 backlash will be the #1 accuracy limiter.** AhaRobot's dual-motor anti-backlash trick is worth copying.
3. **Scope autonomy claims to single-arm tasks**, using the second arm as a stabilizer. Autonomous bimanual work is a research problem.
4. **The fixed cart height means no floor pickup** without a lift mechanism, which is why AhaRobot has its rail.
5. **Paper angle:** "System-2 VLM at ~1 Hz on a $660 open robot via Cerebras". Kimi found no prior work isolating System-2 inference speed as the variable.

## Kimi's 16-week plan (summary)
- W1-2: order parts, print, LeRobot + MuJoCo sim
- W3-4: one SO-101 leader/follower pair, teleop
- W5-6: full XLeRobot build
- W7-8: 50-100 demos, ACT, first autonomy
- W9-10: SmolVLA fine-tune + async inference, 3 tidy/fetch tasks
- W11-12: Cerebras System-2 loop + voice
- W13-14: "bring me sandwich ingredients" + VLM-judge recovery
- W15: robustness
- W16: release + video; stretch goal: Amazing Hand swap

## Kimi's parts list (claims, USD, unverified)
| Item | Qty | ~Price |
|---|---|---|
| XLeRobot 0.4.0 kit (17x STS3215, boards, printed parts, cables), WowRobo | 1 | $349 |
| IKEA RÅSKOG cart | 1 | ~$40 |
| Anker SOLIX C300 power station | 1 | ~$180 |
| 4" omni wheels | 3 | ~$30 |
| USB cameras (head + 2 wrist) | 3 | ~$45 |
| Raspberry Pi 5 (optional) | 1 | ~$79 |
| Hub, cables, microSD, clamps, wire | - | ~$60 |
| SO-101 leader arm kit for teleop | 1 | ~$130-150 |
| **Total** | | **~$900-950 USD** |

Chat: https://www.kimi.ai/chat/1a0da468-6422-8953-8000-0982a48682df (private to Hasan's account)
