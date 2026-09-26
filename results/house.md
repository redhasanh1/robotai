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

The 3 judgement calls: "put everything that belongs in the kitchen back in the kitchen", "get the dirty clothes out of
the way", "I spilled something in the living room".

What it means: the house, the skills and the body check all work; everything a rule can express is done. The part
that fails is the thinking, and the brain that fits a 6 GB laptop GPU is both slow (20-85 s per thought) and not
smart enough for judgement calls - which is the gap a bigger, faster brain is for.
