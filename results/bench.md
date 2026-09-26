# Benchmark (simulation)

_2026-09-26 10:04; seeds per cell: 12; latency profiles are assumptions until measured_

## 1. Best of N (self-check off)

| N | success | physics s/decision |
|---|---|---|
| 1 | 48% | 0.07 |
| 2 | 54% | 0.14 |
| 4 | 58% | 0.098 |
| 8 | 71% | 0.126 |
| 16 | 71% | 0.273 |

## 2. Self-check

| self-check | success | tries/task |
|---|---|---|
| off | 58% | 1.0 |
| on | 98% | 1.5 |

## 3. Physics veto (N=8, self-check off)

| veto | success |
|---|---|
| off | 71% |
| on | 94% |

## 4. Memory (first-try success, first half vs second half of the run)

- no_memory: 16/20 -> 18/20
- with_memory: 16/20 -> 19/20

## 5. Held-out contact model (softer contacts, pyramidal cone, condim 3 - nothing tuned on it)

| world | blind single try | full system (N=8, veto, self-check, memory) | tries |
|---|---|---|---|
| dev | 50% | 100% | 1.04 |
| holdout | 44% | 92% | 1.44 |

## 6. Brain speed (decision = choose + rank all N, budget 1.0 s)

| brain | N=1 | N=2 | N=4 | N=8 | N=16 | N=32 | max N in budget |
|---|---|---|---|---|---|---|---|
| local_1660ti (assumed) | 6.32s | 6.64s | 7.28s | 8.56s | 11.12s | 16.24s | 0 |
| rented_gpu (assumed) | 1.96s | 2.04s | 2.22s | 2.58s | 3.29s | 4.71s | 0 |
| cerebras (assumed) | 0.55s | 0.55s | 0.56s | 0.58s | 0.62s | 0.71s | 32 |
| local_1660ti MEASURED (local, 2026-09-26 10:28) | 13.47s | - | 13.81s | 12.36s | 14.00s | - | |
| local_1660ti_qwen3b MEASURED (qwen2.5-vl-3b-4bit, 2026-09-26 10:45) | 23.22s | - | 26.05s | 20.62s | 24.87s | - | |
