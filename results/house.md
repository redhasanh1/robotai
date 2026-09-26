# The simulated home: 50 prompts (hand/home_tasks.py, tools/house.py --score)

The InMoov on its wheeled base in a kitchen / laundry / living room / you. Each prompt is planned, run on the body
model (reach, joint limits, grip, catches), and judged by where every object ends up.

| brain | passed | notes |
|---|---|---|
| rules only | **47/50** | direct jobs, wishes ("I'm hungry" -> apple), multi-step; judgement calls left open |
| rules + Qwen2.5-VL-3B 4-bit (laptop) | 47/50 | ~85 s per plan; the server died on the longer repair prompts |
| rules + Qwen2.5-3B text 4-bit (laptop), no examples | 47/50 | stable, 17-33 s per plan, no common sense: never wiped for "I spilled something" |
| same + its own solved tasks as in-context examples (fair) | 47/50 | plans reached for points 1-2 m away and couldn't repair them |
| same + 6 hand-written examples that paraphrase the tests (CEILING, not fair) | 48/50 | solved "get the dirty clothes out of the way" |
| **same, fair (own solved tasks as examples) + high-level skills only** | **49/50** | 27-68 s per plan; solved "belongs in the kitchen" and "dirty clothes"; "I spilled something" still never wipes |

The single change that mattered: the AI may only use skills (go, pick, put_in, put_on, give, wipe, ...), no raw hand
coordinates or joint angles, and it is told to think about where each object should end up first. With raw
coordinates available, the small model invented targets 1-2 m away and could not repair them.

Two more cheap levers (Kimi round 8), both prompt-only, no task-specific rules:

| change | passed | what happened |
|---|---|---|
| + one line per skill saying what it is for ("wipe: removes spills, crumbs, mess") | 48/50 | spill: picked up the remote and put it away, never wiped; "belongs in the kitchen" regressed (run-to-run noise on a 3B model) |
| + "what is wrong now / what should be true after" step before planning (`think(situate=True)`, off by default) | 48/50 | ~9 s extra per task. Spill: "wrong = the apple and ball on the living room counter" |

The situation step shows the real reason the spill fails: **the world description never contains a spill.** The robot
is told what objects are where, not that anything is dirty, so the model explains the request with what it can see
and tidies. A person would look at the floor. The fix is perception (camera / scene state reports messes), not a
smarter prompt. Rules only passes it because a rule maps "spill" to wipe. Scoring the AI on it is testing a guess.

The 3 judgement calls: "put everything that belongs in the kitchen back in the kitchen", "get the dirty clothes out of
the way", "I spilled something in the living room".

What it means: the house, the skills and the body check all work; everything a rule can express is done. The part
that fails is the thinking, and the brain that fits a 6 GB laptop GPU is both slow (20-85 s per thought) and not
smart enough for judgement calls - which is the gap a bigger, faster brain is for.
