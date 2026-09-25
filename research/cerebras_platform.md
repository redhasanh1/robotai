# robotai: where Cerebras inference changes what a robot can do that GPUs can't

Research date: 2026-09-25. Every factual claim has a URL next to it. Anything marked **[analysis]** is my own reasoning or estimate and is not sourced.

---

## 0. PRIORITY: the "fast wireless/network provider" partnership

**What I found:** I could not find any announcement of Cerebras partnering with a wireless, 5G, Wi-Fi or Starlink provider to deliver low-latency inference. I searched Verizon, T-Mobile, AT&T, Ericsson, Nokia, Cisco, Bell, Rogers, Telus, Akamai, Cloudflare, Lumen, Equinix, Zayo, Starlink, Qualcomm, SoftBank and Vodafone. In the Verizon, AT&T and T-Mobile AI-RAN work, the carriers partner with NVIDIA, Nokia and Ericsson, not Cerebras (https://www.fierce-network.com/wireless/att-t-mobile-and-verizon-plans-diverge-ai-ran, https://technologymagazine.com/news/nine-tech-firms-join-verizon-to-design-bottom-up-6g-for-ai). **Ask Hasan for the name or link.** It may be internal or not yet public.

**Candidates he may mean, most likely first:**

| Partner | What it is | Latency relevance | Canada |
|---|---|---|---|
| **Bell Canada (Bell AI Fabric)**, a telco and wireless carrier | Announced 2026-03-16. Cerebras is an anchor tenant of Bell's 300 MW Sherwood, Saskatchewan AI data centre, and Bell AI Fabric customers get access to Cerebras inference inside Canada (https://www.prnewswire.com/news-releases/bell-ai-fabric-expands-national-network-with-300-mw-data-centre-in-saskatchewan-892263812.html, https://www.datacenterdynamics.com/en/news/canadas-bell-announces-300mw-data-center-campus-in-saskatchewan-names-coreweave-cerebras-as-customers/). Cerebras takes 160 MW (https://thelogic.co/news/bell-saskatchewan-data-centre/). | No latency claims. First phase is due H1 2027 (https://www.prnewswire.com/news-releases/bell-ai-fabric-expands-national-network-with-300-mw-data-centre-in-saskatchewan-892263812.html). **[analysis]** A Bell wireless or fibre customer could get an on-net path to Cerebras. Regina is roughly 2,000+ km from Toronto, so expect about 35–50 ms RTT, which is worse than Montreal. | Yes |
| **Arista Networks** (networking partner, Supernova 2026) | Scale-up, scale-out and "scale-across" datacenter networking. Wafer-to-wafer IO latency is 2 µs and network latency through the wafer IO module is 3 µs (https://www.investing.com/news/transcripts/cerebras-at-supernova-2026-speed-becomes-the-new-ai-edge-93CH-4866314) | Inside the datacenter only, so it does not affect the robot's WAN hop | n/a |
| **AWS (Bedrock)**, Mar 2026 | Disaggregated inference: Trainium does prefill and CS-3 does decode, linked over EFA (https://www.aboutamazon.com/news/aws/aws-cerebras-ai-inference) | Reachable from AWS ca-central-1 (Montreal) edges **[analysis]** | Via AWS |
| **AMD Helios**, Jul 2026 | GPU prefill plus WSE decode. Names **robotics** explicitly: "robotics, scientific discovery and other applications where response time directly shapes the user experience". Available on Cerebras Cloud in H2 2026 (https://www.cerebras.ai/press-release/amd-and-cerebras-announce-industry-leading-ultra-low-latency-and-high-throughput-ai-inference) | Cuts prefill cost, which matters for image-heavy robot prompts **[analysis]** | Cerebras Cloud |
| **Callosum**, Aug 2026 | London software layer that orchestrates heterogeneous agentic workloads. No latency numbers and no network component (https://www.globenewswire.com/news-release/2026/08/20/3348334/0/en/cerebras-and-callosum-partner-to-deliver-ultra-low-latency-heterogeneous-agentic-inference.html) | Europe-focused | No |

**Effect on the robot latency budget (holds whatever the partner turns out to be) [analysis]:**
- VLA-Perf models the base latency of each network hop like this: Ethernet 0.05–0.1 ms, Wi-Fi 6/7 2.5–3.5 ms, 4G/5G 10–25 ms, cloud 10–100 ms (https://arxiv.org/html/2602.18397v1). **A 5G link is therefore slower than home Wi-Fi plus fibre.** A carrier partnership only helps if it gives a short, on-net path into a nearby Cerebras site (for example MEC or peering).
- Home Wi-Fi 6 (about 3 ms), plus residential fibre to Montreal (about 8 ms RTT, https://wondernetwork.com/pings/Toronto), plus about 70 ms p50 API TTFB (https://llmlatency.dev/provider/cerebras) comes to **about 80–90 ms before decode starts.** With decode on top, a **5–10 Hz action-chunk loop in the cloud is feasible** and 20 Hz is not, because of the per-request TTFB floor. With persistent connections, cached prompts and a dedicated endpoint, the 70 ms TTFB could plausibly drop to 20–40 ms. At that point **~15–20 Hz becomes plausible**. This needs internal confirmation (see Open Questions).

---

## A. Cerebras inference facts (2026)

**Hardware**
- **WSE-3 / CS-3:** 4T transistors, 900k cores, **44 GB on-chip SRAM, 21 PB/s memory bandwidth**, 125 PFLOPS peak AI, 5 nm (https://www.cerebras.ai/press-release/cerebras-announces-third-generation-wafer-scale-engine, https://introl.com/blog/cerebras-wafer-scale-engine-cs3-alternative-ai-architecture-guide-2025).
- **CS-4** (announced 2026-08-18): 3× "WSE-3 Turbo" wafers per rack, 750 PFLOPS sparse FP16, **129.6 PB/s**, models above 50T parameters. **More than 4,400 tok/s per user on GPT-OSS-120B**, which is up to 2× CS-3 and up to 30× GPUs. First systems come online in Q3 2026 (https://www.globenewswire.com/news-release/2026/08/19/3347356/0/en/cerebras-unveils-cs-4-up-to-30-times-faster-than-gpu-based-solutions.html, https://investors.cerebras.ai/news-releases/news-release-details/cerebras-unveils-cs-4-30-times-faster-gpu-based-solutions).

**Why decode is fast**
- At batch 1, decode reads every weight once per token, so it is memory-bandwidth-bound. An H100 (3.35 TB/s) needs about 21 ms per step for a 70B FP8 model. On WSE-3 the weights already sit in SRAM at 21 PB/s. Llama-3 70B runs single-stream at about 2,100 tok/s, against 30–50 tok/s on one H100 (https://www.cerebras.ai/blog/cerebras-inference-3x-faster, https://www.spheron.network/blog/cerebras-vs-nvidia-h100-inference-2026/).
- **[analysis]** The key property for robotics is that **per-user, per-token latency is low**, and batching many users together does not create that. A GPU can raise aggregate throughput by batching, but it cannot make *one* robot's 60-token sequence finish faster.

**Public models** (https://inference-docs.cerebras.ai/models/overview)
- `gpt-oss-120b`: about 3,000 tok/s, 65k context on free tier / 131k paid, production.
- `qwen-3.8-27b`: about 1,850 tok/s, 64k / 128k context, production, **accepts image input on the shared tier**.
- "Many additional model families" are available through Dedicated Endpoints.

**Vision / image input** (https://inference-docs.cerebras.ai/capabilities/image-inputs)
- The feature is in public preview. Images go in as base64 data URIs, PNG or JPEG. Max image size is 15k×15k px, max payload 10 MiB. Up to 10 images per request on Developer/Enterprise, 2 on free trial, more on dedicated endpoints.
- Image token costs: **qwen-3.8-27b** uses 32×32 px per token, up to 2,304 tokens per image. **gemma-4-31b** (dedicated endpoints) uses 48×48 px per token, **max 280 tokens per image**. **kimi-k2.7-code** is in customer trials.
- **Gemma 4 31B** runs at **1,851 tok/s** (Artificial Analysis). The quoted TTFT of **1.5 s includes reasoning**. The blog names "robotics" as a use case (https://www.cerebras.ai/blog/gemma-4-on-cerebras-the-fastest-inference-is-now-multimodal).
- **[analysis]** For a robot, Gemma 4's cap of 280 tokens per image makes prefill cheap. Two cameras come to about 560 tokens, which is attractive for high-rate loops.

**TTFT / latency**
- Llama 3.1 405B has 240 ms TTFT (https://www.cerebras.ai/blog/llama-405b-inference).
- Third-party edge probe (2026-09-25): **US-Central p50 TTFB 71 ms, p95 122 ms.** Europe, Tokyo and São Paulo are about 190–200 ms p50 (https://llmlatency.dev/provider/cerebras). No Canadian probe exists.

**Custom / fine-tuned models**
- Dedicated Endpoints support "custom weights" and let you deploy fine-tuned models. Dedicated customers get fine-tuning and weight management. You have to contact Cerebras to get one (https://inference-docs.cerebras.ai/dedicated/overview).

**Pricing**
- The official pricing page does not show per-token numbers (https://www.cerebras.ai/pricing).
- Third-party figures put GPT-OSS-120B at about $0.35/M input tokens and the overall range at roughly $0.10–$6/M (https://pricepertoken.com/endpoints/cerebras, https://costbench.com/software/llm-api-providers/cerebras-inference/). Treat these as approximate.
- **[analysis]** Cost is small for a robot loop. At 10 Hz × 800 tokens per call, a robot uses about 29M tokens per hour, which at an assumed ~$0.3–1/M comes to roughly $10–30 per hour. That is fine for demos, not for leaving it running 24/7.

**Access / partners:** also available via AWS Marketplace, OpenRouter, Hugging Face and Vercel (https://www.cerebras.ai/pricing).

**Regions**
- **Montreal (Enovum, Cerebras-owned, operational July 2025)** and Oklahoma City (300+ CS-3). Also Santa Clara, Stockton, Dallas and Minneapolis (https://www.cerebras.ai/press-release/cerebras-announces-six-new-ai-datacenters-across-north-america-and-europe-to-deliver-industry-s).
- The Supernova 2026 transcript summary also lists **Toronto** as a location (https://www.investing.com/news/transcripts/cerebras-at-supernova-2026-speed-becomes-the-new-ai-edge-93CH-4866314). I could not confirm this from a second source, so **ask internally.**
- Bell Saskatchewan is due H1 2027. Other 2026 capacity is in Finland (Mikkeli, 165 MW) and Europe.
- The OpenAI deal is 750 MW (https://openai.com/index/cerebras-partnership/).

**Speculative decoding:** I found no public Cerebras doc describing user-facing speculative decoding controls. **[analysis]** Ask internally whether it is used server-side and whether a custom draft model (for example an action-token draft) can be plugged in.

---

## B. Cerebras beyond LLMs (physics / scientific computing)

- **Molecular dynamics:** 1.1M MD steps/s, **748× faster than Frontier**, with Sandia, LLNL and LANL. Atoms are distributed across the 900k cores, which reaches millisecond timescales that are about 1,000× longer than before. This was part of the NNSA AMT program (https://www.cerebras.ai/press-release/cerebras-sets-new-world-record-in-molecular-dynamics-at-1.1-million-simulations-per-second-748x-faster-than-the-worlds-1-supercomputer-frontier, https://www.sandia.gov/labnews/2024/10/03/sandia-led-collaboration-achieves-one-of-worlds-fastest-molecular-dynamics-simulations/). The earlier result was 179× (https://www.cerebras.ai/press-release/cerebras-wafer-scale-engine-outperforms-worlds-1-supercomputer-achieving-long-timescale-molecular-dynamics-simulations-179x-faster).
  - **[analysis]** 1.1M steps/s is about 0.9 µs per timestep. This shows the wafer handles *strong scaling of small, latency-bound, iterative problems*, which is the same shape as a physics sim inside a robot's control loop.
- **CFD / stencils:**
  - The WSE Field-Equation API was up to 470× faster than NETL's Joule supercomputer and more than 100× faster than OpenFOAM (https://www.cerebras.ai/press-release/cerebras-systems-and-national-energy-technology-laboratory-set-new-milestones-for-high-performance-energy-efficient-field-equation-modeling-using-simple-python-interface, https://arxiv.org/html/2209.13768v2).
  - "Near real-time" natural convection CFD with NETL and PSC (https://www.cerebras.ai/press-release/national-energy-technology-laboratory-and-pittsburgh-supercomputing-center-pioneer-first-ever-computational-fluid-dynamics-simulation-on-cerebras-wafer-scale-engine).
  - A 7-point stencil BiCGStab solve reached 0.86 PFLOPS (https://arxiv.org/html/2010.03660).
  - There is a 2026 stencil paper by Belli and De Sensi (https://arxiv.org/pdf/2605.07954).
- **Seismic:** KAUST, 2023 Gordon Bell finalist. TLR-MVM sustained **92.58 PB/s** (https://www.cerebras.ai/press-release/kaust-and-cerebras-named-gordon-bell-award-finalist-for-solving-multi-dimensional-seismic-processing-at-record-breaking-speeds).
- **Monte Carlo particle transport:** ANL kernel, 130× faster than A100 (https://www.businesswire.com/news/home/20231113913017/en/Cerebras-Systems-Announces-130x-Performance-Improvement-on-Key-Nuclear-Energy-Simulation-over-Nvidia-A100-GPUs).
- **SDK:** CSL is used by TotalEnergies, KAUST, ANL, PSC and EPCC (https://www.cerebras.ai/blog/supercharge-your-hpc-research-with-the-cerebras-sdk).
- **Robotics / embodied / world models:**
  - I found no Cerebras robotics customer, world-model or embodied-AI product announcement.
  - Robotics shows up only as a named *use case*, in the AMD PR and the Gemma 4 blog (URLs above).
  - Cerebras investor Eclipse raised $1.3B for robotics and AI infrastructure. That is adjacent, not a Cerebras product (https://www.bloomberg.com/news/articles/2026-04-07/cerebras-backer-eclipse-raises-1-3-billion-for-robotics-ai-infrastructure).
  - **[analysis]** The space is open, and that is good for a portfolio or internal-demo story.

---

## C. Latency math: robot in Toronto → Cerebras

**Inputs**

| Hop | Estimate | Source |
|---|---|---|
| Wi-Fi 6/7 (robot to router) | 2.5–3.5 ms | https://arxiv.org/html/2602.18397v1 |
| Toronto → Montreal RTT | **7.9 ms** | https://wondernetwork.com/pings/Toronto |
| Toronto → Kansas City RTT (proxy for OKC) | 23.5 ms. Realistic OKC figure ~30–40 ms **[analysis]** | same |
| Toronto → Dallas | 34.4 ms | same |
| Toronto → Minneapolis | ~20–25 ms **[analysis]** (Des Moines is 22.8 ms) | same |
| Toronto → San Jose (Santa Clara) | 77 ms | same |
| Residential last mile | +5–15 ms **[analysis]** | — |
| API TTFB (US-Central probe) | 71 ms p50 / 122 ms p95 | https://llmlatency.dev/provider/cerebras |
| Decode | ~0.3–0.6 ms/token at 1,800–3,000 tok/s (from model speeds in §A) **[analysis]** | — |

**Per-call budget via Montreal [analysis]**
- Network ≈ 15–25 ms RTT, TTFB/prefill ≈ 50–100 ms, then decode.
- **Short output (~10 tokens: yes/no, point, score):** ~80–130 ms → **8–12 Hz.**
- **60-token action chunk:** + 20–35 ms → ~110–160 ms → **6–9 Hz chunk rate.** Each chunk covers about 1 s of motion, so this is well above the rate you need. Chunks are executed with asynchronous or real-time chunking, so the robot never stalls waiting for the network.
- **300–400 token ECoT reasoning trace:** + 120–220 ms → ~0.2–0.35 s → **3–5 Hz.**
- **p95 jitter is the real enemy.** US-Central p95 is 122 ms. Keep a local fallback policy, such as SmolVLA or ACT on the laptop GPU, that takes over whenever the cloud misses its deadline.

**Feasible control rates for cloud-in-the-loop [analysis]**
- 1 Hz planner or verifier: trivial.
- 5–10 Hz action chunks: feasible today.
- 15–20 Hz: only with a dedicated endpoint, a warm connection and TTFB under about 40 ms.
- Torque or servo loops (100 Hz or more) always stay local.

---

## D. Robot-loop designs that exploit batch-1 fast decode

Honest framing first. For **small diffusion or flow VLAs, GPUs are already fast**. π0 runs in 6.15 ms on H100, 31 ms on RTX 4090 and 52.6 ms on Jetson Thor (https://arxiv.org/html/2602.18397v1). The Cerebras advantage exists **only where the loop is decode-bound**: autoregressive tokens, reasoning traces, many sequential samples, or large (≥27B) models. The thesis should be "**big and autoregressive at the same latency a small diffusion policy gets on a GPU**", not "faster VLA".

### D1. Autoregressive VLA System-1 in the cloud
- **Facts:**
  - FAST produces about 30–60 tokens per 1 s chunk (about 30 per arm) (https://arxiv.org/html/2501.09747).
  - π0-FAST takes **about 750 ms per chunk**, against π0 diffusion under 100 ms on a 4090 (same paper).
  - VLA-Perf measured a classic autoregressive head at **327.6 ms, against 3.2 ms for diffusion** with chunk size 50 (https://arxiv.org/html/2602.18397v1).
  - OpenVLA runs at about 6 Hz on a 4090 (https://arxiv.org/pdf/2406.09246).
- **On Cerebras [analysis]:** a 2–4B autoregressive action model decoding 60 tokens (a bimanual XLeRobot is about 60+ tokens) at ≥2,000 tok/s takes about 30 ms, plus TTFB, for roughly **110–160 ms end to end, against about 750 ms locally.** That is a **5–7× improvement in chunk rate**, and it lets a *27–31B* VLM backbone emit actions at the same rate, which no GPU single-stream can do.
- **Why a GPU can't match it:** per-token latency on a GPU is bounded by HBM bandwidth, and batching does not help a single robot.

### D2. Best-of-N / test-time search (strongest story)
- **Facts:**
  - RoboMonkey samples 16 candidates, perturbs them, and uses a VLM verifier to pick one. That takes **650 ms (1.5 Hz) on an H100**, and gives +25% absolute on out-of-distribution tasks and +8% in-distribution. Action error follows an **inference-time scaling law** (a power law in the number of samples) (https://arxiv.org/html/2506.17811v1, https://robomonkey-vla.github.io/).
  - V-GPS re-ranks sampled actions with an offline-RL value function. It improved 5 different policies across 12 tasks and works with black-box policies, but the extra value model costs time (https://arxiv.org/pdf/2410.13816, https://nakamotoo.github.io/V-GPS/).
- **Design [analysis]:**
  - The local policy (SmolVLA or ACT) proposes N=8–32 chunks.
  - One Cerebras call to Gemma-4-31B or Qwen-3.8-27B then scores them. The call carries the image (280 tokens) plus the candidates drawn as overlays or written as text trajectories, and returns a short output (index plus score, about 5 tokens).
  - Budget ≈ network 20 + prefill/TTFB 60–100 + decode 5 = **~90–130 ms, which is 7–10 Hz of verified chunks**, against 1.5 Hz on an H100.
  - Pushing N higher costs prefill, not decode. That makes the Cerebras-plus-AMD/AWS disaggregated prefill relevant.
- **Why it's a thesis:** scaling laws say more samples and a better verifier give better actions. Cerebras converts that into a real-time budget.

### D3. Embodied chain-of-thought at high Hz
- **Facts:**
  - ECoT raises the token count per step from **7 (OpenVLA) to about 350**, which limits control to **about 1–1.2 Hz** (https://arxiv.org/abs/2506.07639, https://arxiv.org/pdf/2407.08693).
  - Workarounds trade reasoning for speed: ECoT-Lite is 3× faster and Fast-ECoT is 7.5× faster through reuse and caching (https://www.alphaxiv.org/overview/2505.08243v2, https://arxiv.org/abs/2506.07639).
  - Gemini Robotics-ER 1.5 exposes a **thinking budget** as a latency-versus-accuracy knob, and performance rises as the budget grows (https://developers.googleblog.com/building-the-next-generation-of-physical-agents-with-gemini-robotics-er-15/).
- **On Cerebras [analysis]:** 350 tokens at 1,850 tok/s is about 190 ms, plus about 90 ms network and TTFB, for **~0.28 s, or about 3.5 Hz *with full reasoning, every step*.** That is roughly 3× the published ECoT rate, with a 27–31B reasoner instead of 7B, and no caching hacks. A 1,000-token "think" becomes about 0.6 s, which is acceptable at every subtask boundary.

### D4. Code-as-policies / on-the-fly controllers
- **Fact:** Code as Policies has LLMs write Python "language model programs" that combine perception and control APIs with loops and conditionals (https://arxiv.org/pdf/2209.07753).
- **On Cerebras [analysis]:**
  - A 300–800 token controller comes back in about 0.2–0.5 s.
  - That allows **generate, run in sim or check, repair, regenerate** loops of 3–5 iterations inside about 2 s.
  - The robot can rewrite its grasp or visual-servo routine after every failure. On a GPU API at about 50–150 tok/s, one iteration takes 5–15 s.

### D5. Multi-agent swarm of small VLM queries
- Run several queries per second, each with about 5–20 output tokens:
  - success detection ("did the cup get grasped?")
  - affordance or point grounding
  - a safety monitor ("human hand in workspace?")
  - task-progress estimation for the planner
- **[analysis]:** at about 100 ms each over parallel connections, 4 monitors at 5 Hz is about 20 calls/s. Shared-tier rate limits are the constraint, so this needs a dedicated endpoint. On local GPU, one 27B VLM cannot run alongside the policy on a laptop at all.

---

## E. Custom models to serve on Cerebras (4-month student plus employee access)

Listed in order of realism **[analysis]**:

1. **Robot verifier/critic VLM (recommended flagship).**
   - LoRA fine-tune of Gemma-4-31B or Qwen-3.8-27B (both already served, both take images) to score (image, candidate-chunk overlay, instruction) and output success probability or rank.
   - Data: roll out your LeRobot policy and label successes and failures automatically with the robot's own success detector.
   - Deploy via Dedicated Endpoint custom weights (https://inference-docs.cerebras.ai/dedicated/overview).
   - This powers D2 and D5.
2. **System-2 planner / ER model.**
   - Same backbone, fine-tuned on your XLeRobot episodes to emit subtask plus 2D points plus a short ECoT (D3).
   - Low risk, because the output is text.
3. **Distilled autoregressive action model.**
   - A 2–4B VLM with a FAST tokenizer head, trained with LeRobot's π0-FAST recipe on your SO-101 data, served on Cerebras as the cloud System-1 (D1).
   - Riskier: it needs custom-architecture serving (vision tower plus action vocabulary) and a few hundred GPU-hours of training.
4. **Stretch goal: a wafer-native world model or physics check with CSL.** Hasan's CSL experience plus the MD and stencil results in §B point to a *tiny* on-wafer rigid-body or contact rollout for scoring candidate chunks. That fits the "no museum kernels" rule only if it plugs straight into the D2 verifier. It is probably out of scope for 4 months unless internal tooling exists.

---

## Top 5 unlocks (ranked)

| # | Unlock | Per-cycle budget (Montreal) [analysis] | GPU baseline (sourced) | Why GPU can't match it |
|---|---|---|---|---|
| 1 | **Real-time Best-of-N plus VLM verifier** (RoboMonkey or V-GPS style, 27–31B verifier) | 20 net + 60–100 prefill + 5 decode ≈ **90–130 ms (7–10 Hz)** | 16 samples verified in 650 ms / 1.5 Hz on H100 (https://arxiv.org/html/2506.17811v1) | Verifier size and the sequential sample-then-verify steps are latency-bound. Its scaling-law gains (+25% OOD) become usable at control rate. |
| 2 | **Full embodied CoT every step** (350 tokens) | ~90 + 190 ≈ **~280 ms (3.5 Hz)** | ECoT 1–1.2 Hz with 7B (https://arxiv.org/abs/2506.07639) | 350 sequential tokens at 30–100 tok/s cannot fit in 1 s |
| 3 | **Cloud autoregressive VLA System-1** (FAST tokens, 60/chunk) | ~90 + 30 ≈ **~120–160 ms (6–8 Hz chunks)** | π0-FAST about 750 ms per chunk (https://arxiv.org/html/2501.09747) | Autoregressive decode is batch-1 and bandwidth-bound |
| 4 | **Self-repairing code-as-policy** (3–5 generate, check, fix iterations) | ~0.3 s per 500-token iteration, **<2 s per repair loop** | GPU APIs at ~50–150 tok/s → 5–15 s per iteration (https://www.cerebras.ai/blog/gemma-4-on-cerebras-the-fastest-inference-is-now-multimodal says 35× a typical GPU endpoint) | Iteration count × tokens is purely decode time |
| 5 | **Parallel perception monitors** (success, safety, affordance) | ~100 ms each, **4 monitors × 5 Hz** | A laptop GPU cannot co-host a 27B VLM with the policy **[analysis]** | Short outputs mean TTFB dominates. Needs a dedicated endpoint for rate limits. |

**Pitch in one line [analysis]:** *"GPUs let a robot run a small policy fast. Cerebras lets a robot think, sample and check with a 30B model at the speed a small policy runs, and test-time-scaling results say that is where the success rate comes from."*

---

## Open questions to ask internally at Cerebras

1. Is there a Cerebras inference presence in **Toronto** (the Supernova transcript lists one)? What is measured RTT or TTFB from a Toronto residential ISP to Montreal?
2. What is the **wireless or network partnership** Hasan heard about? What is its name, latency SLA and on-net path, and is it available in Canada? Is Bell AI Fabric the one, and will Bell wireless or fibre customers get peered routes before Sherwood opens in H1 2027?
3. What is the **TTFB floor** on a warm, dedicated endpoint for a ~600-token prompt with 1–2 images? Can it get under 40 ms?
4. Is **prompt/KV prefix caching** available (the same system prompt plus instruction every call), and is there a **persistent-connection or streaming-input** mode (websocket, gRPC)?
5. Can a **custom VLM with LoRA** (Gemma-4-31B or Qwen-3.8-27B) be served on a dedicated endpoint for an internal or employee project? What is the turnaround and cost?
6. Are **custom architectures** supported, such as a VLM with an extended action-token vocabulary (FAST BPE tokens) or a small 2–4B model? What is the per-token latency for a model that small?
7. Is server-side **speculative decoding** used, and can we supply a draft model? Action tokens are highly predictable.
8. Are there **rate limits** for about 20–50 small requests/s from one client, and **p99 latency** guarantees?
9. Is image support for Gemma-4 or Qwen-3.8 moving to GA? Is **multi-frame video** input or a higher image count per request on the roadmap?
10. Does anyone internally own **robotics or physical-AI** go-to-market (the AMD PR names robotics)? Is there a demo or showcase slot?
11. For the CSL angle: is there internal tooling to run **non-LLM kernels** (a small physics rollout or world model) next to a served model on the same system for customers?
12. Will **CS-4** (4,400+ tok/s per user) capacity be in the Montreal region, and when?
