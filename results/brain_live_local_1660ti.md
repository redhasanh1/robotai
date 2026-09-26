# Real model in the loop: SmolVLM-500M on the GTX 1660 Ti

_2026-09-26 10:28, tools/brain_live.py, OpenAI-compatible local server (tools/local_vlm_server.py)_

| N | choose s | rank s | decision s |
|---|---|---|---|
| 1 | 6.316 | 7.151 | 13.467 |
| 4 | 6.339 | 7.476 | 13.815 |
| 8 | 6.288 | 6.067 | 12.355 |
| 16 | 6.991 | 7.005 | 13.996 |

Episodes (N=8, self-check, memory): 8/8 held, mean 1.50 tries, mean brain time 21.1 s per task.

JSON reply format followed in 4/48 calls; the rest were read from plain words (hand/brain.py _lenient).
