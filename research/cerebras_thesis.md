# The Cerebras thesis: what fast inference unlocks for this robot

*2026-09-25. Summary of two sourced reports: [cerebras_platform.md](cerebras_platform.md) (Cerebras facts, latency, loop designs) and [physical_ai_fast_inference.md](physical_ai_fast_inference.md) (world models, PINNs, MPC, test-time compute). A Kimi cross-check is running separately. Every number below is sourced in those two files.*

## The one-line pitch

**Run a 30B multimodal model that samples, checks and reasons at the rate a small robot policy acts.**
"A faster policy" is not the pitch. Small diffusion policies already run fast on GPUs (π0 takes about 6 ms on an H100 and 31 ms on a 4090). The edge is making the *big thinking model* fast enough to sit inside the control loop.

## Where it runs

| Loop | Rate | Where | Why |
|---|---|---|---|
| Servo control, safety stop | 100 Hz+ | robot | can't tolerate the network |
| Motor policy (ACT / SmolVLA) | 20-50 Hz | robot laptop GPU | also the fallback if the network jitters |
| **Verify, choose, re-plan** | **1-10 Hz** | **Cerebras** | a 30B VLM here is only possible at Cerebras speed |
| Task planning, voice | ~1 Hz | Cerebras | responses feel instant |

Latency: Cerebras has a live Montreal datacenter about 7.9 ms from Toronto. A third-party probe measured API first-byte at 71 ms p50 / 122 ms p95 (from US-Central; there's no Toronto probe yet). With a dedicated endpoint, 5-10 Hz cloud action chunks look feasible. 15-20 Hz needs time-to-first-token under about 40 ms.

## Ranked unlocks for our 16 weeks

1. **Best-of-N + VLM verifier (buildable, strongest).** Sample about 16 candidate action chunks locally, then have a 27-31B VLM on Cerebras pick the best one. RoboMonkey gets **+25% on out-of-distribution tasks**, but runs at only 1.5 Hz on an H100 (650 ms for 16 samples). On Cerebras the estimate is **about 90-130 ms, or 7-10 Hz**. Error drops as a power law in samples, so speed turns directly into success rate.
2. **World-model planning in about 1 s instead of 16 s (medium risk).** V-JEPA 2-AC takes 16 s per action on a 4090, DINO-WM 53 s per plan, Cosmos 4 min. Search over imagined futures only becomes real-time with far more compute. This needs a custom model served on Cerebras, so it needs internal access.
3. **Embodied chain-of-thought every step (buildable).** A full ~350-token reason-then-act step at about 3.5 Hz, against 1-1.2 Hz in the ECoT paper. The robot says what it's doing and why, live.
4. **Self-repairing code-as-policies (buildable).** Generate a controller, run it, have a VLM look at the result, fix it: under 2 s per repair loop. Plus parallel monitors (success, safety, grasp points) at about 4 × 5 Hz.
5. **Physics twin re-fit in seconds (research-risky, biggest upside).** PhysTwin fits a spring-mass model of a deformable (cloth, dough, rope) from video in about 17 min on a GPU. Spring-mass and particle updates are stencil-like, the workload where Cerebras has published **molecular dynamics at 748× Frontier** and stencils at up to 342× an A100. A CSL kernel for this is exactly Hasan's skill set, but it's probably past 16 weeks.

**Bonus (niche, no Cerebras needed):** thermal doneness. A heat-equation model of the pan and food, with uncertainty. No robot demo has closed the cooking loop with a heat model, so it's an open niche.

**Skip:** Physical Neural Networks (Wright, Nature 2022) is analog-hardware research. Genie 3 is a closed preview. PINN-based real-time control has no convincing robot demos yet.

## The custom model

Fine-tune **Gemma-4-31B or Qwen-3.8-27B** (both image-capable on Cerebras) with LoRA as a **robot critic**: given camera frames and candidate actions, score them. Train it on our own labelled teleop and rollout data. It becomes the planner later. Dedicated endpoints accept custom weights. Stretch goal: a distilled 2-4B autoregressive action model served on Cerebras.

## The paper

Nobody has isolated *System-2 speed* as the experimental variable. Run the same robot and tasks with the verifier/planner at 0.5 / 2 / 10 Hz, and plot success rate against inference speed. That's a clean, publishable result that only someone with Cerebras access can produce.

## What to measure first (week 1-2)

1. Round-trip time and TTFT from Toronto to the Cerebras API, with an image, p50/p95.
2. The GPU baseline for the same verifier call (to compute the speedup).
3. Local ACT/SmolVLA inference time on the laptop.

## Ask internally

Toronto latency and the TTFT floor; dedicated-endpoint access for a student project; custom weights and architectures (a small world model?); prefix caching for repeated camera frames; speculative decoding; rate limits; when CS-4 reaches Montreal; whether a CSL physics kernel could be exposed as an endpoint.

**Open:** Hasan mentioned a Cerebras partnership with a fast wireless/network provider. The research found no public announcement. The closest match is Bell Canada's AI Fabric (Cerebras in Bell's Saskatchewan data centre, opening H1 2027). **Need the name or link from Hasan.**
