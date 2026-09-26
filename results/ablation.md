# Ablation: does the family choice matter?

_2026-09-26 10:47, sim, stub brain, 48 tasks per row (4 objects x 12 seeds)_

| safety | search | family | success | tries | physics s/task |
|---|---|---|---|---|---|
| bare | rank | brain | 65% | 1.00 | 0.12 |
| bare | cem | brain | 71% | 1.00 | 1.71 |
| bare | cem | random | 81% | 1.00 | 1.66 |
| bare | rank | random | 58% | 1.00 | 0.13 |
| full | rank | brain | 98% | 1.19 | 0.18 |
| full | cem | brain | 100% | 1.06 | 2.29 |
| full | cem | random | 90% | 1.23 | 1.87 |
| full | rank | random | 85% | 1.52 | 0.20 |
