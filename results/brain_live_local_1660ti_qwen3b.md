# Real model in the loop: Qwen2.5-VL-3B (4-bit) on the GTX 1660 Ti

_2026-09-26 10:45, tools/brain_live.py, LOCAL_4BIT=1 tools/local_vlm_server.py (Kimi round 5: fair local baseline = biggest model that fits)_

| N | choose s | rank s | decision s |
|---|---|---|---|
| 1 | 11.828 | 11.391 | 23.219 |
| 4 | 10.261 | 15.787 | 26.048 |
| 8 | 8.274 | 12.342 | 20.617 |
| 16 | 8.321 | 16.545 | 24.866 |

Episodes (N=8, self-check, memory): 8/8 held, mean 1.25 tries, mean brain time 29.3 s per task.

JSON format followed in 48/48 calls (SmolVLM-500M: 4/48).
