# robotai: physical-AI research brief (arm/base, models, fast-inference use, feasibility)

Researched 2026-09-25. All prices are **USD** unless marked CAD. Prices come from vendor pages or press coverage on the date above and change often, so re-check before ordering. Anything marked **[est]** is my own engineering estimate and has no source behind it.

---

## 0. TL;DR

1. **Platform: build an XLeRobot-style rig.** That means two SO-101 arms on a wheeled cart with a head camera and wrist cameras. It is the cheapest open bimanual mobile manipulator with a large community: a **$660 BOM** ([GitHub](https://github.com/Vector-Wangel/XLeRobot)), and it runs natively in LeRobot. LeKiwi (a single SO-101 on an omni base) is the cheaper fallback.
2. **Don't hang the InMoov hands on SO-101 arms at first.** SO-101 payload is only a few hundred grams (sources disagree, see §1.3). An InMoov hand with its servos in the forearm will be at or over that limit, and dexterous 5-finger imitation learning is much harder than parallel-gripper learning. Train with the stock grippers. Show the InMoov hands as a separate "hand" demo. If you want a hand on the arm later, use a light one (Pollen Amazing Hand, 400 g).
3. **Low-level policy: ACT first, then SmolVLA, then pi0.5 or GR00T** if you have a 24-40 GB GPU. Plan on about 50 teleop demos per task ([ACT paper](https://arxiv.org/abs/2304.13705); the [GR00T N1.7 SO-101 guide](https://openelab.io/blogs/learn/nvidia-groot-1-7-so-101-lerobot-requirements) uses 50 episodes too).
4. **Where Cerebras helps is System-2**, meaning the planner, the voice interface, replanning, success detection and code generation. It does not help System-1, the 30-200 Hz motor loop, which runs on a local GPU next to the robot. Helix runs S2 at 7-9 Hz and S1 at 200 Hz ([Figure](https://www.figure.ai/news/helix)). Hi Robot re-queries its high level about once per second ([arXiv](https://arxiv.org/html/2502.19417v1)).
5. **Backflips are out.** They need a BLDC humanoid: Unitree R1 at about $5,900 (cartwheels/handstands), G1 at about $13.5k+ (backflip). **Cooking is partly realistic.** No SO-101 rig has publicly demonstrated real heat cooking. Mobile ALOHA ($32k) did cook shrimp, with 50 demos per task. Aim for "assemble a sandwich / pour / stir / plate", not "cook dinner".

---

## 1. What Kimi said

**Update 2026-09-25:** Kimi was re-run on kimi.ai while logged in. See [kimi_research.md](kimi_research.md) for its answer and a cross-check against this brief. (The first attempt on kimi.com hit a login wall; nothing below comes from Kimi.)

---

## 2. Hardware: arm + mobile platform (question a)

### 2.1 Candidates

| Platform | What it is | Price (USD) | Source | Verdict |
|---|---|---|---|---|
| **SO-101 (SO-ARM101)** | 6-DOF arm (5 joints + gripper), Feetech STS3215 bus servos, 3D-printed, leader/follower teleop | Pro motor kit **$249.90** (motors, adapter board and cables for leader+follower; no printed parts or camera); printed parts **$29.90** | [Seeed motor kit](https://www.seeedstudio.com/SO-101-Low-Cost-AI-Arm-Kit-Pro-p-6427.html), [CNX](https://www.cnx-software.com/2025/05/02/so-arm101-open-source-dual-robotic-arm-kit-works-with-hugging-faces-lerobot/) ($220 std / $240 pro at launch) | **Core building block.** Best-supported arm in LeRobot. |
| **XLeRobot** | 2x SO-101-derived arms on a wheeled IKEA-cart base with a head camera | **$660 BOM** (excludes printing, tools, shipping, tax); developer kit **$579** worldwide / ¥3,699 CN (no battery or cart); WowRobo v0.4.0 listing **$349**, all packages sold out when checked | [GitHub](https://github.com/Vector-Wangel/XLeRobot), [docs](https://xlerobot.readthedocs.io/), [WowRobo](https://shop.wowrobo.com/products/xlerobot-dual-arm-mobile-household-robot-kit) | **Recommended.** Bimanual + mobile, designed for household chores, open source. Its own docs say it is "not currently designed for in-hand dexterity, heavy lifting (over 1kg per arm), or highly dynamic movements". |
| **LeKiwi** | 3-wheel omni base + one SO-101 arm, optional Raspberry Pi | "from **$260**" (base) | [AIFITLAB](https://aifitlab.com/products/lerobot-lekiwi-low-cost-mobile-manipulator), [Seeed](https://www.seeedstudio.com/LeKiwi-Full-Kit-12V-Verision.html) (price did not render; arm add-on $240-249.90; needs 2+ USB cameras) | Cheaper, but single arm, and single-arm chores are very limited. |
| **Koch v1.1** | Dynamixel XL430/XL330 arm | follower ~$400; leader ~$180 (~$430 total per one source) | [ROBOTIS](https://www.robotis.us/koch-v1-1-low-cost-robot-arm-follower/), [Robotic Gizmos](https://www.roboticgizmos.com/koch-v1-1/) | Older. Better servos, but pricier than SO-101 and has less community momentum. Skip. |
| **AhaRobot** | SCARA-like bimanual mobile manipulator, 0.7 mm repeatability | ~**$1,000** hardware | [arXiv 2503.10070](https://arxiv.org/abs/2503.10070), [site](https://aha-robot.github.io/) | Technically strong, but it is a research build with a smaller community and more custom fabrication. A good plan B if SO-101 payload bites. |
| **HopeJR (HF + The Robot Studio)** | Full humanoid, 66 DOF, dexterous hands | "under **$3,000**" | [TechCrunch](https://techcrunch.com/2025/05/29/hugging-face-unveils-two-new-humanoid-robots/), [Humanoid Hub](https://x.com/TheHumanoidHub/status/1928140664505540960) | Over budget and a very large build for 4 months. Worth looking at for its hand/forearm design ideas. |
| **Pollen Amazing Hand** | 4 fingers, 8 DOF, 2 hobby servos per finger, 400 g | Seeed right-hand dev kit **$99** (page doesn't say if servos are included); HF blog says "< $200" to build | [Seeed](https://www.seeedstudio.com/Amazing-Hand-Right-Hand-The-Open-Source-Robotic-Hand-Developer-Kit.html), [HF blog](https://huggingface.co/blog/pollen-robotics/amazing-hand), [GitHub](https://github.com/pollen-robotics/AmazingHand) | The best "hand on an arm" candidate. All actuation is inside the hand, and it is light. |

### 2.2 Best capability per dollar

**XLeRobot (2x SO-101 + cart) wins.** It is the only option under about $1k that is bimanual, mobile, LeRobot-native, and has demonstrated household tasks. Most useful chores (open a container and take something out, hold a bowl and stir, fold) need two arms. A single-arm LeKiwi saves about $300 but loses most of those tasks. AhaRobot has better precision per dollar, but it needs more custom build work and has a smaller ecosystem.

### 2.3 InMoov hand on an SO-101: payload

- The SO-101 uses STS3215 servos: **30 kg·cm stall at 12V** (C018, 1/345 gear) or 16.5 kg·cm on the 7.4V version ([WowRobo servo](https://shop.wowrobo.com/products/feetech-sts3215-servo-12v-30kg-high-torque-servo-for-so-arm100), [ThinkRobotics](https://thinkrobotics.com/blogs/product-reviews-buying-guides/thinkrobotics-lerobot-so-101-6-axis-robotic-arm-review-ai-ready-open-source-and-built-for-learning)).
- **Stated payloads conflict:** "~200 g realistic" (ThinkRobotics review via search summary), "~500 g" ([Robotics Center spec page](https://www.roboticscenter.ai/hardware/so-101)), and "600-1000 g single arm" ([XLeRobot docs](https://xlerobot.readthedocs.io/), probably with 12V servos at short reach). The official [SO-ARM100 repo](https://github.com/TheRobotStudio/SO-ARM100) states no payload. Treat **200-500 g at full reach** as the working envelope.
- An InMoov hand + forearm with 5x MG996R (~55 g each) in the forearm probably weighs **400-700 g [est]**. That is at or past the limit, it is cantilevered at the end of the arm, and it replaces the gripper the policies are trained around.
- **Recommendation:** (1) Use the SO-101 stock gripper, or its compliant TPU variant from the SO-ARM100 repo, for all learned tasks. (2) Keep the InMoov hands as a standalone dexterity demo: the Phase 1 deliverable, teleoperated by glove/camera, with LLM-driven gestures. (3) If a hand on the arm is required, either move the InMoov servos off the arm (Bowden-cable tendons back to the cart), or use the 400 g Amazing Hand and upgrade the shoulder/elbow to 12V servos. Budget extra time for 5-finger imitation learning; data collection with a glove is a project in itself.

---

## 3. Open-weight robot policies (question b)

| Model | Size | GPU (inference / fine-tune) | Data needed | Control / chunking | Source |
|---|---|---|---|---|---|
| **ACT** | small (tens of M) | trains on one consumer GPU | **50-100 demos**/task (10-20 min of data); 80-90% on fine bimanual tasks in the paper | chunks of ~100 steps at **50 Hz** | [arXiv 2304.13705](https://arxiv.org/abs/2304.13705), [phospho explainer](https://blog.phospho.ai/dissecting-action-chunking-with-transformers-act-precision-imitation-learning-for-robotic-manipulation/) |
| **Diffusion Policy** | small-mid | one consumer GPU | tens to low hundreds of demos | action-sequence denoising; slower inference than ACT unless few-step sampling | [arXiv 2303.04137](https://arxiv.org/abs/2303.04137) |
| **SmolVLA** | **450M** | runs on CPU/laptop; fine-tunes on one consumer GPU; ~2 GB at inference | pretrained on <30k community episodes; ~78% on SO-100 real tasks, beats ACT | action chunks + **async inference** (30% faster, 2x throughput) | [HF blog](https://huggingface.co/blog/smolvla), [LeRobot async docs](https://huggingface.co/docs/lerobot/async) |
| **pi0 / pi0-FAST / pi0.5 (openpi)** | ~3B (PaliGemma base) | inference >8 GB (LeRobot says pi0 uses ~14 GB); LoRA fine-tune >22.5 GB (RTX 4090); full >70 GB (A100/H100) | tens to hundreds of demos per task; community SO-101 LoRA pipeline exists | flow-matching action chunks; **remote websocket policy server** built in | [openpi](https://github.com/Physical-Intelligence/openpi), [LeRobot pi0.5 docs](https://github.com/huggingface/lerobot/blob/main/docs/source/pi05.mdx), [pi05-so101-finetune](https://github.com/ljt228/pi05-so101-finetune) |
| **GR00T N1.6 / N1.7** | ~2-3B (VLM + diffusion head) | inference **16 GB+**; fine-tune **40 GB+** (a 4090 is not enough for the official fine-tune baseline) | reference SO-101 example uses **50 episodes** | dual-system (VLM + action head); measure latency yourself | [OpenELAB N1.7 guide](https://openelab.io/blogs/learn/nvidia-groot-1-7-so-101-lerobot-requirements), [Seeed N1.6 SO-101 wiki](https://wiki.seeedstudio.com/fine_tune_gr00t_n1.6_for_lerobot_so_arm_and_deploy_on_agx_orin/) |
| **OpenVLA-OFT** | 7B | needs a big GPU | fine-tuned per task; 97.1% on LIBERO | parallel decoding + chunking give **26x (LIBERO) / 43x (ALOHA)** throughput over OpenVLA | [project](https://openvla-oft.github.io/), [arXiv 2502.19645](https://arxiv.org/abs/2502.19645) |
| **RDT-1B** | 1.2B (170M variant exists) | large; ZeRO / 8-bit tricks documented | pretrained on 1M+ episodes, 6K ALOHA bimanual episodes | diffusion, bimanual-focused | [arXiv 2410.07864](https://arxiv.org/abs/2410.07864), [GitHub](https://github.com/thu-ml/RoboticsDiffusionTransformer) |
| **Gemini Robotics-ER 1.5 / ER 2** (API, not open weights) | n/a | cloud | zero-shot | **planner / embodied reasoner** (pointing, boxes, trajectories, task planning, success detection, hands off to a VLA); ER 1.5 preview **$0.30/M input, $2.50/M output** | [Google dev blog](https://developers.googleblog.com/building-the-next-generation-of-physical-agents-with-gemini-robotics-er-15/), [API docs](https://ai.google.dev/gemini-api/docs/robotics-overview), [ER 2](https://deepmind.google/models/gemini-robotics/embodied-reasoning/), [CloudPrice](https://cloudprice.net/models/google-gemini-robotics-er-1-5-preview) |

**Practical takeaway for a student:** use ACT for the first skill (fast to train, well understood), then SmolVLA for language-conditioned multi-skill. Move to pi0.5 or GR00T only if you get a 24-40 GB GPU (a rented A100/H100 for fine-tuning is fine). Budget **~50 good teleop episodes per skill**. Operator consistency matters more than raw count.

---

## 4. Where fast inference is a real unlock (question c)

### 4.1 The reference architectures

- **Figure Helix:** S2 is a 7B VLM at **7-9 Hz**. S1 is an 80M visuomotor policy at **200 Hz**. They talk through a single latent vector, and both run onboard on dual embedded GPUs. Trained on ~500 h of teleop ([Figure](https://www.figure.ai/news/helix)).
- **Hi Robot (Physical Intelligence):** the high-level VLM (PaliGemma-3B) emits language subgoals. It re-runs **every 1 s or on each user interaction**, and pi0 executes. It runs on 1-2 RTX 4090s. It did sandwich-making and table cleaning with live user corrections ([arXiv](https://arxiv.org/html/2502.19417v1), [PI blog](https://www.pi.website/research/hirobot)).
- **Code as Policies:** an LLM writes Python that calls perception and control primitives ([arXiv 2209.07753](https://arxiv.org/abs/2209.07753)).
- **Gemini Robotics-ER:** explicitly sold as the "high-level brain" that delegates motor control to a VLA ([DeepMind](https://deepmind.google/models/gemini-robotics/embodied-reasoning/)).

### 4.2 What Cerebras gives you

Cerebras now serves a multimodal model: **Gemma 4 31B at ~1,851 output tok/s**, with **~1.5 s time-to-first-answer-token including reasoning** ([Cerebras blog](https://www.cerebras.ai/blog/gemma-4-on-cerebras-the-fastest-inference-is-now-multimodal)). It also serves text models such as gpt-oss-120b at ~3,000 tok/s ([EdenAI summary](https://www.edenai.co/providers/cerebras)).

**Honest framing:** throughput is enormous, but **network RTT + time-to-first-token puts a floor of hundreds of ms to ~1.5 s** on each call [est for RTT]. That rules Cerebras out of the motor loop, and it doesn't need to be there. It fits the System-2 slot well, and there it is faster than anything a student could run locally.

| Layer | Rate needed | Where it runs | Cerebras role |
|---|---|---|---|
| Servo control / safety limits | 100 Hz-1 kHz | ESP32 / servo bus | none |
| **System-1 policy** (ACT/SmolVLA/pi0.5) | action chunks consumed at 30-50 Hz, re-inferred every ~0.3-1 s | **local GPU** (laptop / desktop 4090 / Jetson) via LeRobot async server ([docs](https://huggingface.co/docs/lerobot/async)) | none; keep local, WiFi jitter kills it |
| **System-2 task planner** ("clean table" → subgoals like "pick cup", "place in sink") | ~1 Hz or on-event (Hi Robot pattern) | **Cerebras** | **core unlock**: long reasoning chains finish in about a second, so you can re-plan after every subgoal instead of once per task |
| **Success detection / replanning** ("did the grasp work?") | after every skill, ~0.5-2 Hz | Cerebras VLM (Gemma 4) or Gemini-ER | **unlock**: verify every step, retry on failure |
| **Voice conversation** | human-perceived <1 s | STT local/cloud → Cerebras → TTS | **unlock**: the reasoning part of the reply is essentially instant; latency becomes an STT/TTS problem |
| **Code-as-policy** for scripted skills (open drawer with IK, sort by color) | on-demand | Cerebras | **unlock**: generate, run, check, regenerate loops in seconds |
| Spatial grounding (pixel points, boxes) | per step | Gemini Robotics-ER (specialized) or local detector | Gemma-4-on-Cerebras is untested here; Gemini-ER is trained for it |

**Architecture to build:** `voice → Cerebras LLM (planner, tool-calling) → skill library [ACT/SmolVLA policies + scripted IK primitives] → VLM success check (Cerebras Gemma 4, or Gemini-ER for pointing) → replan`. This is Hi Robot's structure, with Cerebras in the high-level slot and a much faster re-query budget. The honest pitch: *"fast inference lets the planner think more and check more often, so the robot recovers from failures in real time."* Don't claim the motors are driven by Cerebras.

---

## 5. Feasibility (question d)

### 5.1 Backflips: not feasible on this budget

Backflips need high-torque BLDC actuators and whole-body RL controllers. The cheapest acrobatic humanoid is the **Unitree R1 at ~$5,900** (cartwheels, handstands) ([Engadget](https://www.engadget.com/ai/this-humanoid-robot-can-do-cartwheels-handstands-and-roundhouse-kicks-at-less-than-6000-184500276.html), [Interesting Engineering](https://interestingengineering.com/innovation/unitree-launches-cheapest-humanoid-robot-r1)). The backflip-capable **G1 is ~$13,500+** official, $13.5k-19k street ([RoboZaps](https://blog.robozaps.com/b/unitree-g1-review)). Hobby-servo InMoov/SO-101 hardware is about 1-2 orders of magnitude short on torque and speed. Drop it, or pitch it as a stretch goal that means "buy an R1 later".

### 5.2 Cooking: what has actually been shown

- **SO-101 class:** I found **no public autonomous real-heat cooking demo** on SO-100/101 rigs. The closest is ChefMate: SO-101 + GR00T N1.5 sandwich assembly (cheese, bread, patty), mostly in Isaac Sim, with 20-50 episodes per subtask ([Hackaday](https://hackaday.io/project/204187-chefmate-kitchen-robot-using-vla-act-diffusion)). XLeRobot demos are household pick/place/tidy tasks; its docs don't list cooking ([docs](https://xlerobot.readthedocs.io/)).
- **Higher-end reference:** Mobile ALOHA (~$32k) cooked shrimp, wiped spills and stored a 3 lb pot with **50 demos per task** plus co-training ([MIT Tech Review](https://www.technologyreview.com/2024/01/15/1086592/watch-this-robot-cook-shrimp-and-clean-autonomously/)). Hi Robot made sandwiches ([PI](https://www.pi.website/research/hirobot)).
- **Realistic for 2x SO-101 [est]:** light, rigid objects under about 300 g. Tasks: sandwich/toast assembly, pouring cereal or dry ingredients from a light container, stirring a pot with a spoon (the pot is held or fixed), plating, wiping a counter, putting utensils in a rack, pressing appliance buttons. **Avoid:** lifting a full pot or pan, cracking eggs, knife work, and anything near open flame or hot oil (servo plastic, safety).

### 5.3 Recommended 4-month milestone plan

| Month | Goal | Deliverable / exit test |
|---|---|---|
| **M1 (wk 1-4)** | Finish Phase 1 InMoov hands (in progress). Order and build 2x SO-101 leader/follower. LeRobot calibration and teleop. | Both follower arms mirror their leaders. InMoov hands do scripted gestures via ESP32. |
| **M1.5 (wk 5-6)** | Baseline: record 50 episodes of one tabletop task (e.g. "cup to tray"). Train **ACT**. | ≥70% success on 20 trials, **measured and logged before any fancy stuff**. |
| **M2 (wk 7-9)** | Mobile base (XLeRobot cart or LeKiwi base), head + 2 wrist cameras. Bimanual teleop. Record 3-5 skills × 50 eps. Train **SmolVLA** multi-task with language prompts. | One policy runs several skills when given text commands. Async inference over LAN from a GPU box. |
| **M3 (wk 10-13)** | **Cerebras System-2 layer**: voice in → planner LLM → skill calls → VLM success check → replan. Add code-as-policy primitives (IK go-to, open/close). | "Tidy the table" works end to end, recovers from at least one injected failure, and the voice reply feels instant. |
| **M4 (wk 14-17)** | Kitchen demo: sandwich/toast assembly or "pour + stir + plate" as a 3-4 skill chain. Optional: pi0.5/GR00T fine-tune on a rented A100 to compare against SmolVLA. InMoov hand shown as a gesture/handoff demo. | Recorded 2-3 min uncut demo video + success-rate table + writeup. |

---

## 6. Recommended full-robot components (verified prices)

Currency is **USD** unless noted. "Verified" means seen on the linked page or in coverage of it on 2026-09-25.

| # | Component | Qty | Unit price | Line total | Link / note |
|---|---|---|---|---|---|
| 1 | SO-ARM101 Pro servo motor kit (leader + follower motors, driver board, cables) | 2 | $249.90 | $499.80 | [Seeed](https://www.seeedstudio.com/SO-101-Low-Cost-AI-Arm-Kit-Pro-p-6427.html). 3D-printed parts not included |
| 2 | SO-101 3D-printed parts (or print yourself, ~$0 on own printer) | 2 | $29.90 | $59.80 | [Seeed](https://www.seeedstudio.com/SO-101-Low-Cost-AI-Arm-Kit-Pro-p-6427.html) (related product) |
| 3 | Mobile base: XLeRobot cart build (full BOM incl. arms ≈ $660) **or** LeKiwi base from $260 | 1 | ~$260 | ~$260 | [XLeRobot BOM](https://github.com/Vector-Wangel/XLeRobot); [LeKiwi](https://aifitlab.com/products/lerobot-lekiwi-low-cost-mobile-manipulator). XLeRobot dev kit $579 (no battery/cart) |
| 4 | Cameras: USB cams (head + 2 wrist) | 3 | $12 | $36 | Seeed X10 USB camera, listed as a LeKiwi add-on ([Seeed](https://www.seeedstudio.com/LeKiwi-Full-Kit-12V-Verision.html)) |
| 5 | (Optional) depth camera, Orbbec Gemini 2 | 1 | $240 | $240 | same Seeed page |
| 6 | On-robot compute: Jetson Orin Nano Super (or use your laptop) | 1 | $249 | $249 | [JetsonHacks](https://jetsonhacks.com/2024/12/17/jetson-orin-nano-super-developer-kit/), [NVIDIA](https://blogs.nvidia.com/blog/jetson-generative-ai-supercomputer/) |
| 7 | (Optional) light dexterous hand, Pollen Amazing Hand | 1 | $99 (Seeed kit; servos may be extra) / <$200 BOM | $99-200 | [Seeed](https://www.seeedstudio.com/Amazing-Hand-Right-Hand-The-Open-Source-Robotic-Hand-Developer-Kit.html), [HF blog](https://huggingface.co/blog/pollen-robotics/amazing-hand) |
| 8 | Training GPU: rent cloud A100/H100 for pi0.5/GR00T fine-tunes, or use an existing 24 GB card for ACT/SmolVLA | n/a | varies | $0-100 [est] | GPU needs per [openpi](https://github.com/Physical-Intelligence/openpi) |
| 9 | High-level brain: Cerebras (Hasan has access) + optional Gemini Robotics-ER API | n/a | ER 1.5: $0.30/M in, $2.50/M out | ~$5-20 [est] | [CloudPrice](https://cloudprice.net/models/google-gemini-robotics-er-1-5-preview) |
| | **Core subtotal (items 1-4, 6)** | | | **≈ $1,105 USD** | ≈ **$1,530 CAD** at ~1.38 [est FX], before shipping/tax |

The Phase 1 InMoov hands (<$500 CAD) are priced by other workers and are not in this table.

**Cheaper path:** item 3 as a DIY IKEA-cart base per the XLeRobot docs, drop item 6 (use a laptop), print parts yourself. That comes to about $550-650 USD, consistent with XLeRobot's $660 BOM.

---

## Appendix A: prompt prepared for Kimi (not submitted; login wall)

> Search the web and give me a thorough, sourced (with URLs) technical research answer. Context: student in Toronto building a home-helper "robot maid"... (a) best open-source student-buildable arm + mobile platform in 2026 with prices: SO-100/SO-101, LeKiwi, XLeRobot, Koch, AhaRobot, HopeJR, Amazing Hand; InMoov hand on SO-101 vs gripper. (b) open-weight policies: ACT, Diffusion Policy, SmolVLA, pi0/pi0.5, GR00T N1.x, OpenVLA-OFT, RDT, Gemini Robotics-ER: GPU, demos, Hz. (c) where very fast LLM/VLM inference helps: System-2 over System-1 (Helix, GR00T, Hi Robot), decomposition, replanning, voice, code-as-policy. (d) feasibility: backflips, cooking on SO-101-class rigs, 4-month plan.

## Appendix B: open verification gaps

- SO-101 payload: the sources conflict (200 g / 500 g / 600-1000 g). Measure it on your own arm with a luggage scale before committing to any hand-on-arm design.
- Whether the Amazing Hand $99 Seeed kit includes its 8 servos: the page doesn't say.
- XLeRobot WowRobo kits were sold out on 2026-09-25, so plan to self-source.
- Gemma-4-on-Cerebras image latency for small images hasn't been benchmarked for robotics. Measure end-to-end RTT from Toronto before designing loop timing.
