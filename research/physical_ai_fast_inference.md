# Physical-AI methods bottlenecked by inference speed — what fast compute unlocks for robotai

Research date: 2026-09-25. Every factual claim has a URL. Lines tagged **[analysis]** are my reasoning, not sourced facts.

Robot context: 2x SO-101 arms on a mobile cart, RGB cameras, LeRobot stack. Compute is split between an on-robot GPU and remote access to Cerebras (wafer-scale, fast batch-1 inference, big on-chip SRAM; also runs stencil, PDE and MD workloads).

---

## 0. TL;DR

- The best-documented case where compute is the bottleneck is **planning with a learned world model**. V-JEPA 2-AC takes **16 s per action** on an RTX 4090 (800 samples x 10 CEM iterations, horizon 1). Cosmos needs **4 min per action** ([V-JEPA 2 paper](https://arxiv.org/html/2506.09985v1)). DINO-WM takes **53 s** per plan on an A6000 (CEM 100x10) ([DINO-WM](https://arxiv.org/pdf/2411.04983)). Cosmos Policy best-of-N planning takes **~5 s per action chunk on 8x H100** ([Cosmos Policy](https://www.alphaxiv.org/abs/2601.16163)). Each of these is 10x to 1000x slower than a 1–10 Hz loop.
- **Test-time sampling plus a verifier** (RoboMonkey) is the second-clearest case. It samples 16 candidates and verifies them in **~650 ms (1.5 Hz)**, and it gains **+25 pts** out of distribution ([RoboMonkey](https://arxiv.org/html/2506.17811v1)). Action error follows a power law in the number of samples, so more samples buys more accuracy ([RoboMonkey](https://arxiv.org/html/2506.17811v1)).
- **Sampling MPC over a real physics engine** already runs in real time for rigid tasks on one GPU. It uses 1024 samples at 8–10 Hz on an RTX 5090 with MJX ([2606.20712](https://arxiv.org/html/2606.20712)). DIAL-MPC runs at 50 Hz ([DIAL-MPC](https://lecar-lab.github.io/dial-mpc/)). Fast compute helps less here, except with deformables or fluids and many parameter hypotheses.
- **Deformable, fluid and thermal models** are the most physical case, and there the bottleneck is **inverse problems**, not forward simulation. PhysTwin fits a spring-mass twin from video in **~12 min (CMA-ES) + ~5 min (gradient)** on a GPU ([PhysTwin](https://github.com/Jianghanxiao/PhysTwin)). RoboCraft's GNN-dynamics planner took **613.7 s per action** ([RoboCook](https://ar5iv.labs.arxiv.org/html/2306.14447)).
- **[analysis]** Cloud round-trip time limits where Cerebras can help. Anything that must run at ≥20 Hz (servoing, contact) stays on the robot GPU. Cerebras fits 0.5–10 Hz outer loops: planning, verification, re-identification and re-planning. RTC and async chunking already tolerate >300 ms of inference delay ([PI RTC](https://www.pi.website/research/real_time_chunking)), so this split is realistic.

---

## 1. World models for robot planning

| Model | What it is | Planning compute | Latency today (source) |
|---|---|---|---|
| **V-JEPA 2-AC** (Meta, 2025) | 300M action-conditioned predictor on a frozen V-JEPA 2 encoder, trained on 62 h of robot video. It plans toward an image goal by L1 distance in latent space. | CEM: 800 samples x 10 iters, horizon 1 | **16 s/action on 1x RTX 4090**. Success rates: reach 100%, grasp cup 60%, pick-place cup 80% ([arXiv](https://arxiv.org/html/2506.09985v1)) |
| **Cosmos (Predict) as a planner** | Pixel video diffusion world model | Renders full frames for each candidate | **~4 min/action**, so a full pick-and-place takes >1 h ([V-JEPA 2 comparison](https://arxiv.org/html/2506.09985v1)) |
| **Cosmos Policy** (NVIDIA, 2026) | Cosmos-Predict2 fine-tuned into a policy plus a value/world model; best-of-N planning | N=8, 1-step lookahead | **~5 s per action chunk on 8x H100**. Planning adds +12.5 pts, and the authors list latency as the main limitation ([alphaXiv](https://www.alphaxiv.org/abs/2601.16163), [cookbook](https://nvidia-cosmos.github.io/cosmos-cookbook/recipes/post_training/predict2/cosmos_policy/post_training.html)) |
| **DINO-WM** (2024) | Predicts DINOv2 patch tokens and plans zero-shot with MPC | CEM 100 samples x 10 iters | **53 s** per plan on an A6000 ([arXiv](https://arxiv.org/pdf/2411.04983)). Sparse Imagination roughly halves this (53.4 → 29.7 s/episode on LIBERO-10) ([arXiv](https://arxiv.org/abs/2506.01392)) |
| **Genie 3** (DeepMind, 2025) | Autoregressive interactive world model, 720p at 24 fps in real time | One rollout in real time, not thousands | Research preview only, not open ([DeepMind](https://deepmind.google/blog/genie-3-a-new-frontier-for-world-models/)) |
| **1X World Model** | Action-controllable video world model for policy **evaluation**, with a learned success/value head | Many rollouts per policy across "millions of scenarios" | Used offline for evaluation ([1X](https://www.1x.tech/discover/1x-world-model), [PDF](https://www.1x.tech/1x-world-model.pdf)) |
| **UniSim** (2023) | Video simulator driven by text or low-level actions; policies trained inside it transfer to the real world in some settings | Video diffusion per step | Offline ([arXiv](https://arxiv.org/abs/2310.06114)) |
| **IRASim** (ByteDance, ICCV'25) | Trajectory-to-video DiT with frame-level action conditioning | Test-time planning with the world model | Push-T IoU rises from 0.637 to 0.961 with model-based planning ([project](https://gen-irasim.github.io/)) |
| **DreamerV3 / DayDreamer** | RSSM latent world model; the policy is learned in imagination | Imagination during training; the policy is cheap at run time | Arm pick-and-place learned on hardware in 8–10 h ([DayDreamer](https://arxiv.org/abs/2206.14176)) |
| **TD-MPC2** | Latent model plus MPPI with a value bootstrap | e.g. 6 iters x 200–512 samples, horizon 3–5 | Small latent MLPs. One report gives 14.7 ms/step on a 4060 laptop in 2D navigation ([search result/paper](https://arxiv.org/pdf/2310.16828)) |

**[analysis] What speed unlocks.** V-JEPA 2-AC runs 8,000 predictor forward passes per action. A batch-1 fast engine would not help much by itself. The win comes from treating the 800 samples as one big batch and doing 10 sequential iterations with low latency. At about 100 ms per iteration you get ~1 s per action, 16x faster, which turns a "time-lapse demo" into a "live demo". The more important effect is that faster planning makes **horizon > 1** affordable. The paper names error accumulation over long horizons as the key limitation ([V-JEPA 2](https://arxiv.org/html/2506.09985v1)). The cost is samples x iterations x horizon, so horizon 5 at the same budget is 5x the compute.

**Risk.** V-JEPA 2-AC needs **careful manual camera positioning**, because it infers the action axes from monocular RGB ([V-JEPA 2](https://arxiv.org/html/2506.09985v1)). It was trained on Franka (DROID) data, so running it on SO-101 needs fine-tuning on your own teleop data. **[analysis]** Plan for 20–50 h of SO-101 play data.

---

## 2. PINNs, neural operators and learned simulators in robotics

- **Soft robots (a real-time PINN-MPC exists).** A domain-decoupled PINN surrogate of a Cosserat rod is **44,000x faster** than the full model. It enables nonlinear MPC at **70 Hz** on a GPU and was validated on a real pneumatic soft actuator with <3 mm error ([arXiv 2508.12681](https://arxiv.org/html/2508.12681v1)). Another PINN-MPC for multi-link manipulators appears in [IFAC 2022](https://www.sciencedirect.com/science/article/pii/S2405896322013118) with [code](https://github.com/Jonas-Nicodemus/PINNs-based-MPC).
- **Deformable manipulation (graph networks).** RoboCraft learns GNN particle dynamics for play-dough from about 10 min of interaction ([arXiv](https://arxiv.org/pdf/2205.02909)). Its sampling+gradient planner took **613.7 ± 202.7 s per action**. RoboCook swapped planning for a learned policy and cut that to **9.3 s** ([RoboCook](https://ar5iv.labs.arxiv.org/html/2306.14447)). **[analysis]** This is the textbook case of compute forcing people to abandon planning for amortized policies. Fast planning would let you keep the planner and its generalization.
- **Physics-constrained neural operators for soft objects.** PINDO learns a residual on a differentiable base simulator and plugs into MPC ([MDPI Actuators](https://www.mdpi.com/2076-0825/15/7/390)). FNO-style controllers are still rare in manipulation. Fourier Controller Networks target real-time embodied decisions ([arXiv 2405.19885](https://arxiv.org/pdf/2405.19885)).
- **Fluids and pouring.** A GNN particle simulator for liquids under rigid-body manipulation has been integrated into gradient-based MPC for pouring, and it transfers zero-shot to stirring and scooping ([arXiv 2509.03446](https://arxiv.org/html/2509.03446)). A 2-D GPU SPH simulation predicts the liquid free surface in real time for closed-loop pouring that avoids sloshing ([Appl. Sci.](https://doi.org/10.3390/app9235007)).
- **Thermal.** PINNs and neural operators predict temperature fields in near real time for additive manufacturing ([arXiv 2401.02403](https://arxiv.org/pdf/2401.02403)) and microwave heating/defrosting from IR matrix sensors ([ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1359431125033721)). For food, the classic approach is heat conduction plus a "doneness index", a time-integral of temperature over the cross-section ([patent](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12135533), [Physics Today](https://physicstoday.aip.org/features/the-virtual-cook-modeling-heat-transfer-in-the-kitchen)). I found **no robot cooking demo that closes the loop with a thermal PDE model**, which is an open niche. **[analysis]**
- **Tactile.** DiffTactile is an MPM-based differentiable tactile simulator that supports real-to-sim parameter refinement ([OpenReview](https://openreview.net/forum?id=eJHnSg783t)). Taccel's GPU IPC backend reaches real time or faster ([UniVTAC survey](https://arxiv.org/html/2602.10093v1)). SO-101 has no tactile sensors, so this is out of scope unless you add them. **[analysis]**
- **Inverse problems** (estimating mass, friction or stiffness) need many forward evaluations:
  - PhysTwin uses about 12 min of CMA-ES sampling plus about 5 min of Warp gradient descent per object ([GitHub](https://github.com/Jianghanxiao/PhysTwin)).
  - DiffTactile and RoboNinja use differentiable MPM to fit material properties and generate cutting trajectories ([RoboNinja](https://arxiv.org/abs/2302.11553)).
  - **[analysis]** These are embarrassingly parallel population searches over stencil-like particle and spring updates, which is the workload Cerebras has shown for scientific computing. On a WSE: MD at 270k timesteps/s for 800k atoms, **179x Frontier** ([Cerebras](https://www.cerebras.ai/press-release/cerebras-wafer-scale-engine-outperforms-worlds-1-supercomputer-achieving-long-timescale-molecular-dynamics-simulations-179x-faster)); 2D stencils up to **342x vs. an A100** ([CStencil](https://arxiv.org/abs/2605.07954)).

---

## 3. Sampling MPC and differentiable physics

- **MuJoCo MPC (MJPC)** offers iLQG, gradient descent and Predictive Sampling in real time on a CPU. Predictive Sampling was meant as a pedagogical baseline but turned out competitive ([arXiv](https://arxiv.org/abs/2212.00541), [code](https://github.com/google-deepmind/mujoco_mpc)).
- **DIAL-MPC** does full-order, torque-level sampling MPC by rolling out Brax physics with diffusion-style annealing. It runs at **50 Hz on hardware**, with 13.4x lower tracking error than vanilla MPPI ([project](https://lecar-lab.github.io/dial-mpc/), [code](https://github.com/LeCAR-Lab/dial-mpc)).
- **Massively parallel SMPC on a real Franka** (2026): MuJoCo MJX + JAX on an **RTX 5090**, **1024 samples at 8–10 Hz** on the real robot and 256 samples at 20 Hz in sim. Action selection runs at 50 Hz and low-level streaming at 1 kHz. Integration steps above 0.025 s go unstable ([arXiv 2606.20712](https://arxiv.org/html/2606.20712)).
- **Simulators.**
  - Newton (NVIDIA + DeepMind + Disney, Linux Foundation) is built on Warp. Its MuJoCo-Warp backend is **70x faster for humanoids and 100x for in-hand manipulation** ([Linux Foundation](https://www.linuxfoundation.org/press/linux-foundation-announces-contribution-of-newton-by-disney-research-google-deepmind-and-nvidia-to-accelerate-open-robot-learning), [NVIDIA](https://developer.nvidia.com/blog/announcing-newton-an-open-source-physics-engine-for-robotics-simulation/)).
  - Genesis claims **43M FPS for a Franka arm on one RTX 4090** and ships MPM, SPH, FEM and PBD solvers for liquids and deformables ([coverage](https://interestingengineering.com/innovation/genesis-system-robot-training), [DataCamp](https://www.datacamp.com/blog/genesis-physics-engine)). The rigid-body FPS headline is for simple scenes. **[analysis]**
- **[analysis]** For rigid pushing and placing, one consumer GPU is already enough. Compute becomes the bottleneck when (a) the model is deformable, fluid or MPM, where each rollout is far more expensive, or (b) you run MPPI **over an ensemble of physical-parameter hypotheses**, for example 32 friction/mass samples x 1024 action samples = 32k rollouts per step.

---

## 4. "Physical neural networks" and physics-grounded foundation models

- **Physical Neural Networks** (Wright et al., *Nature* 2022) train **physical systems** (optical, mechanical, electronic) to *be* the neural network, using physics-aware training, a hybrid of in-situ and in-silico backprop ([PubMed](https://pubmed.ncbi.nlm.nih.gov/35082422/)). **[analysis]** This is analog-computing hardware research, not a robotics method. It is not relevant to robotai beyond being a good framing reference. Don't spend time on it.
- **PhysBench** (ICLR'25) has 10,002 video-image-text items and tested 75 VLMs. VLMs are weak on physical properties and dynamics. PhysAgent (a VLM plus vision expert models) gives +18.4% on GPT-4o ([arXiv](https://arxiv.org/abs/2501.16411)). **[analysis]** This is useful as a benchmark for a verifier, not as a controller.
- **Cosmos-Reason1** (8B and 56B) is a VLM trained with physical-AI SFT and RL. The 56B model scores 60.2% on their physical common-sense benchmark ([arXiv](https://arxiv.org/abs/2503.15558), [code](https://github.com/nvidia-cosmos/cosmos-reason1)). **[analysis]** It is a candidate **verifier or critic** for test-time sampling (§5). Long chain-of-thought reasoning makes it latency-bound, which is exactly where fast token generation helps.
- **Newton, Genesis and Warp** are simulators (§3), not foundation models. They are relevant as the forward model inside MPC and system identification.

---

## 5. Test-time compute for robot policies

- **RoboMonkey** (CoRL'25) samples a few actions from a VLA, adds Gaussian perturbation and majority voting, and has a VLM-based verifier pick the best candidate. It runs **16 candidates in ~650 ms (1.5 Hz)** with SGLang. Results: +9 pts in-distribution (SIMPLER) and **+25 pts OOD real-world** (35 → 60%). Action error follows an exponentiated power law in the sample count ([arXiv](https://arxiv.org/html/2506.17811v1)).
- **V-GPS** re-ranks sampled actions from any generalist policy with an offline-RL value function and needs only black-box access. One value function improved 5 policies across 12 tasks ([arXiv](https://arxiv.org/abs/2410.13816), [project](https://nakamotoo.github.io/V-GPS/)).
- **FOREWARN** uses a latent world model to predict the outcome of each candidate plan, and a VLM aligned to those latents judges them in language ([arXiv](https://arxiv.org/abs/2502.01828)). DynaGuide steers diffusion denoising with an external dynamics model ([survey in arXiv 2511.14178](https://arxiv.org/html/2511.14178v2)).
- **Diffusion policy latency.** Diffusion Policy with DDIM at 10 steps takes 0.1 s on an RTX 3080 ([arXiv](https://arxiv.org/html/2303.04137v5)). π0.5 with 5 denoising steps takes **76 ms (97 ms with RTC)**. RTC stays robust with **>300 ms** of inference delay (match striking, Ethernet plugging) ([PI](https://www.pi.website/research/real_time_chunking), [LeRobot RTC](https://huggingface.co/docs/lerobot/rtc)).
- **SmolVLA async inference on SO-100** gives 30% faster response and 2x throughput. The sorting task did 19 vs. 9 cubes in 60 s ([HF blog](https://github.com/huggingface/blog/blob/main/smolvla.md), [LeRobot async](https://huggingface.co/docs/lerobot/async)).
- **[analysis]** These give the cleanest Cerebras story. The verifier is a VLM/LLM, and Cerebras is fastest at exactly that. The policy stays on the robot and the verifier goes remote. RTC and async already absorb 100–300 ms. Cerebras reports a TTFT of about 170–240 ms on large models ([Cerebras TTFT](https://www.cerebras.ai/glossary/what-is-time-to-first-token), [HPCwire 405B](https://www.hpcwire.com/bigdatawire/this-just-in/cerebras-delivers-record-breaking-performance-with-metas-llama-3-1-405b-model/)). **Caveat:** I found no public Cerebras VLM (image-input) benchmark. Check internally which multimodal models the API serves; image-token prefill may dominate latency.

---

## 6. Sim-to-real in the loop: real-time Real2Sim, digital twins, system ID

- **PhysTwin** (ICCV'25) builds a spring-mass model with Gaussian splats and generative shape completion from sparse video. The resulting twin simulates in real time and has been shown for ropes, cloth, plush toys and packages. The inverse fit is CMA-ES (~12 min) followed by Warp gradients (~5 min) ([arXiv](https://arxiv.org/abs/2503.17973), [GitHub](https://github.com/Jianghanxiao/PhysTwin)).
- **Real-is-Sim** (RAI Institute, ICRA'26) keeps a dynamic digital twin (Embodied Gaussians: Gaussian splats plus particle physics) **synchronized with the real world at 60 Hz**. The policy always acts in the sim and the real robot follows ([arXiv](https://arxiv.org/abs/2504.03597), [project](https://real-is-sim.github.io/)).
- **RoboGSim** combines 3DGS with Isaac Sim for real2sim2real data generation, with zero-shot real-robot transfer ([arXiv](https://arxiv.org/abs/2411.11839)).
- A related 2025 work does real-to-sim policy evaluation with Gaussian splatting plus soft-body simulation ([arXiv 2511.04665](https://arxiv.org/pdf/2511.04665)).
- **[analysis]** The compute-bound step is **re-identification**: refitting the physical parameters as the object changes (dough rested, cloth wet, food cooked). Taking PhysTwin's 17-minute fit to seconds would turn a one-off twin into an **online** twin that updates between actions. The population search (CMA-ES) maps onto massive parallelism, and spring-mass updates are nearest-neighbour stencils. This is plausible for CSL on a WSE, but it is research, not an off-the-shelf API call.

---

## 7. Cooking and household: what's actually useful

| Sub-task | Useful method | Compute-bound? | Verdict **[analysis]** |
|---|---|---|---|
| **Pouring to a target level** | GNN particle model + gradient MPC ([2509.03446](https://arxiv.org/html/2509.03446)), or GPU SPH surrogate ([Appl. Sci.](https://doi.org/10.3390/app9235007)) | Yes, if you plan over many tilt profiles with a particle model. Even then the outer loop is only 2–5 Hz. | Medium risk. Fallback: a learned "pour stop" classifier using vision and weight. |
| **Dough, deformables** | GNN particle dynamics + planning (RoboCraft, 613 s/action) ([arXiv](https://arxiv.org/pdf/2205.02909)); PhysTwin spring-mass | Very. This is the strongest "planning was abandoned because of compute" story. | Research-risky. SO-101 payload (~a few hundred g) limits dough force. Rope or cloth may be the better target. |
| **Cloth / towel folding** | PhysTwin twin + sampling MPC; video world model planning | Yes | Medium. Good visual demo. |
| **Doneness / thermal** | 1-D/2-D heat-conduction PDE + doneness index ([patent](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12135533)); PINN temperature fields ([arXiv 2401.02403](https://arxiv.org/pdf/2401.02403)) | **Not really.** Forward heat PDEs are cheap. Compute only matters if you do Bayesian inversion (unknown thickness, h-coefficient, pan temperature) with large ensembles and uncertainty. | Buildable, with a novel angle (no robot demo found). Needs a cheap thermal camera (e.g. MLX90640). Honest pitch: "physics + uncertainty", not raw speed. |
| **Cutting** | RoboNinja: differentiable MPM cutting sim + adaptive policy using force feedback ([arXiv](https://arxiv.org/abs/2302.11553)) | Offline yes (trajectory optimization); online no | Low priority. Knife safety plus SO-101 force limits. |
| **General pick, place, wipe** | VLA + test-time sampling/verifier; latent world model planning | Yes (§1, §5) | Best ROI |

---

## 8. Ranked: the six most promising "fast-compute unlocks" for robotai (4-month student timeline)

Split assumed: **on-robot GPU** handles cameras, the base policy (ACT/SmolVLA/π0-class), RTC/async chunking and ≥20 Hz servoing. **Cerebras cloud** handles 0.5–10 Hz outer loops: planning, verification and parameter search. **[analysis]** Network RTT sets the floor. Measure it in week 1.

### #1 — Test-time sampling + fast VLM verifier ("RoboMonkey on SO-101") — **BUILDABLE**
- **Where it runs.** SmolVLA or ACT on the robot GPU samples N action chunks (with Gaussian perturbation). A VLM verifier on Cerebras scores them, and the best chunk is executed via RTC.
- **Rate:** 1–3 Hz chunk selection; control stays at 30–50 Hz on the robot.
- **Rollouts:** N = 16 → 64–128 candidates per chunk.
- **GPU baseline:** 16 candidates in 650 ms (1.5 Hz) ([RoboMonkey](https://arxiv.org/html/2506.17811v1)). The power law says more samples give lower error.
- **Demo.** Put the same SO-101 policy on a cluttered, out-of-distribution kitchen counter. Show success vs. N (1, 16, 64, 256) with wall-clock time per decision, comparing a GPU verifier and a Cerebras verifier. Plot "success vs. seconds per decision".
- **Risk.** Low to medium. It depends on Cerebras serving a VLM with image input. If it doesn't, use an LLM verifier on a captioned or structured scene, or a V-GPS value function ([V-GPS](https://arxiv.org/abs/2410.13816)) as a fallback.

### #2 — Latent world-model planning at interactive speed (V-JEPA 2-AC / DINO-WM CEM) — **MEDIUM RISK**
- **Where it runs.** Encoder on the robot GPU (or remote). A CEM loop of 800 x 10 predictor calls, horizon 1→5, runs on Cerebras. The action goes back to the robot.
- **Rate target:** ≥1 Hz (1 s per action), vs. 16 s today.
- **Rollouts:** 8,000 predictor forwards per action at H=1; 40,000 at H=5.
- **GPU baseline:** 16 s/action on a 4090 ([V-JEPA 2](https://arxiv.org/html/2506.09985v1)); 53 s per plan on an A6000 for DINO-WM ([DINO-WM](https://arxiv.org/pdf/2411.04983)).
- **Demo.** Zero-reward, image-goal pick-and-place on SO-101. Show the same planner at 16 s/action on the GPU and about 1 s/action remote, then show a longer horizon enabling a two-step task.
- **Risk.**
  - Runs a *custom 300M ViT predictor* on Cerebras, not a stock LLM endpoint, so it needs internal model-compile access.
  - Needs SO-101 action-conditioned fine-tuning data (tens of hours).
  - Camera placement is sensitive.
  - Fallback: run on your own GPU with Sparse Imagination and fewer samples, then report the projected speedup.

### #3 — GPU sampling-MPC with MJX / MuJoCo-Warp for rigid subtasks (arms + cart base) — **BUILDABLE**
- **Where it runs.** Entirely on the robot GPU (or a LAN desktop GPU). An MJCF model of SO-101 plus the object comes from a phone scan or simple primitives.
- **Rate:** 8–20 Hz planning, 50 Hz action selection.
- **Rollouts:** 256–1024 samples, horizon ~0.4–0.7 s.
- **GPU baseline:** 1024 samples at 8–10 Hz on a real Franka, RTX 5090 ([2606.20712](https://arxiv.org/html/2606.20712)); DIAL-MPC at 50 Hz ([DIAL-MPC](https://lecar-lab.github.io/dial-mpc/)).
- **Demo.** Non-prehensile pushing of a pan or plate to a target pose with a disturbance, using no training data. Then the extension that *needs* big compute: MPPI over **32 physics-parameter hypotheses x 1024 samples**, a robust MPC that doesn't know the friction.
- **Risk.** Low for the base version. The ensemble version is the "Cerebras-sized" stretch goal.

### #4 — Online Real2Sim twin of a deformable (PhysTwin-style re-identification in seconds) — **RESEARCH-RISKY, highest Cerebras upside**
- **Where it runs.** Gaussian-splat and point tracking on the robot. The spring-mass parameter search (CMA-ES population x rollouts) runs on Cerebras as a CSL stencil kernel, or on a GPU as the baseline.
- **Rate:** re-fit every 5–30 s between actions, vs. ~17 min today.
- **Rollouts:** CMA-ES population ~64–256 x full-trajectory simulations per generation.
- **GPU baseline:** ~12 min CMA-ES + ~5 min gradient per object ([PhysTwin](https://github.com/Jianghanxiao/PhysTwin)). WSE priors: MD 179x Frontier ([Cerebras](https://www.cerebras.ai/press-release/cerebras-wafer-scale-engine-outperforms-worlds-1-supercomputer-achieving-long-timescale-molecular-dynamics-simulations-179x-faster)); stencils 342x vs. an A100 ([CStencil](https://arxiv.org/abs/2605.07954)).
- **Demo.** Two arms stretch and fold a towel or rope. The twin re-fits stiffness live after the towel gets wet, and the plan updates. Show "twin prediction error vs. wall-clock" for the GPU and the WSE.
- **Risk.** High. It needs a custom CSL spring-mass kernel plus the PhysTwin pipeline (which uses multiple cameras). **[analysis]** Hasan already writes CSL, so this is the most differentiated item but the least certain to finish in 4 months. Scope it as a standalone kernel benchmark first.

### #5 — Pour-to-level with a particle fluid model in the loop — **MEDIUM-HIGH RISK**
- **Where it runs.** Level estimation (vision, plus a load cell if added) on the robot. Candidate tilt trajectories are evaluated with an SPH or GNN liquid model remotely (or on the GPU).
- **Rate:** 2–5 Hz re-plan of the tilt profile; wrist control at 30+ Hz locally.
- **Rollouts:** 64–512 candidate tilt profiles x ~1–2 s horizon of particle simulation.
- **Baseline:** GNN pouring MPC exists with gradient-based optimization ([2509.03446](https://arxiv.org/html/2509.03446)); a real-time 2-D GPU SPH for closed-loop pouring exists ([Appl. Sci.](https://doi.org/10.3390/app9235007)). No end-to-end latency numbers were found, so measure your own.
- **Demo.** Pour water into cups of different shapes to a line, without spilling. Compare against a learned policy on unseen cups.
- **Risk.** Medium-high, because liquid sim-to-real is hard. Fallback: a 2-D SPH or a reduced model, which is enough for sloshing.

### #6 — Physics-based doneness estimation (heat equation + Bayesian inversion) — **BUILDABLE, low compute-need**
- **Where it runs.** A thermal camera (MLX90640-class) feeds surface temperatures. An ensemble of 1-D/2-D heat-conduction models with unknown thickness, heat-transfer coefficient and pan temperature is fitted online. This can run on the robot CPU/GPU. The Cerebras angle is a big-ensemble posterior (10^4–10^6 members) for calibrated uncertainty. **[analysis]**
- **Rate:** 1 Hz update, with a flip/remove decision when P(core ≥ target) > 0.95.
- **Rollouts:** 10^3–10^6 cheap PDE forward runs per update.
- **Baseline:** No robot demo found. Heat-conduction doneness models exist in patents and the literature ([patent](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12135533), [Physics Today](https://physicstoday.aip.org/features/the-virtual-cook-modeling-heat-transfer-in-the-kitchen)), and PINN temperature-field prediction runs in real time in manufacturing ([arXiv 2401.02403](https://arxiv.org/pdf/2401.02403)).
- **Demo.** The robot pan-sears a pancake or egg and flips or plates it based on the *inferred interior* temperature. Validate with a probe thermometer.
- **Risk.** Low for the physics. The dexterity (spatula flip with SO-101) is the hard part. **Be honest:** this one doesn't *need* Cerebras. Its value is "physical AI that isn't just a VLA".

### Suggested 4-month sequencing [analysis]
- **Month 1:** #3 base (MJX MPC pushing) and #1 plumbing (async policy, remote verifier, RTT measurement). Also measure the un-optimized GPU baselines first.
- **Month 2:** #1 full demo with success-vs-N curves.
- **Month 3:** #2 (world-model planner), falling back to "projected" numbers if Cerebras custom-model access stalls.
- **Month 4:** one physical showcase, either #6 (safe) or #4 (ambitious), plus the write-up.

---

## Sources (primary)
- V-JEPA 2: https://arxiv.org/html/2506.09985v1
- DINO-WM: https://arxiv.org/pdf/2411.04983
- Sparse Imagination: https://arxiv.org/abs/2506.01392
- Cosmos Policy: https://www.alphaxiv.org/abs/2601.16163
- Genie 3: https://deepmind.google/blog/genie-3-a-new-frontier-for-world-models/
- 1X WM: https://www.1x.tech/discover/1x-world-model
- UniSim: https://arxiv.org/abs/2310.06114
- IRASim: https://gen-irasim.github.io/
- DayDreamer: https://arxiv.org/abs/2206.14176
- TD-MPC2: https://arxiv.org/pdf/2310.16828
- DD-PINN soft robot MPC: https://arxiv.org/html/2508.12681v1
- RoboCraft: https://arxiv.org/pdf/2205.02909
- RoboCook: https://ar5iv.labs.arxiv.org/html/2306.14447
- GNN liquid pouring: https://arxiv.org/html/2509.03446
- SPH pouring: https://doi.org/10.3390/app9235007
- MJPC: https://arxiv.org/abs/2212.00541
- DIAL-MPC: https://lecar-lab.github.io/dial-mpc/
- Parallel SMPC Franka: https://arxiv.org/html/2606.20712
- Newton: https://www.linuxfoundation.org/press/linux-foundation-announces-contribution-of-newton-by-disney-research-google-deepmind-and-nvidia-to-accelerate-open-robot-learning
- Genesis: https://interestingengineering.com/innovation/genesis-system-robot-training
- Physical Neural Networks: https://pubmed.ncbi.nlm.nih.gov/35082422/
- PhysBench: https://arxiv.org/abs/2501.16411
- Cosmos-Reason1: https://arxiv.org/abs/2503.15558
- RoboMonkey: https://arxiv.org/html/2506.17811v1
- V-GPS: https://arxiv.org/abs/2410.13816
- FOREWARN: https://arxiv.org/abs/2502.01828
- Diffusion Policy: https://arxiv.org/html/2303.04137v5
- RTC: https://www.pi.website/research/real_time_chunking
- SmolVLA: https://github.com/huggingface/blog/blob/main/smolvla.md
- PhysTwin: https://github.com/Jianghanxiao/PhysTwin
- Real-is-Sim: https://arxiv.org/abs/2504.03597
- RoboGSim: https://arxiv.org/abs/2411.11839
- RoboNinja: https://arxiv.org/abs/2302.11553
- DiffTactile: https://openreview.net/forum?id=eJHnSg783t
- Cerebras MD: https://www.cerebras.ai/press-release/cerebras-wafer-scale-engine-outperforms-worlds-1-supercomputer-achieving-long-timescale-molecular-dynamics-simulations-179x-faster
- CStencil on WSE-3: https://arxiv.org/abs/2605.07954
- Cerebras TTFT: https://www.cerebras.ai/glossary/what-is-time-to-first-token
