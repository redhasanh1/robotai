# Random things in the way (tools/clutter.py)

10 random layouts (seed 0): every object at a random spot on its own counter, >= 7 cm apart, off the containers. 47 rule-planned tasks on each.

| robot moves obstacles aside | runs | done cleanly | planner flagged a problem | arm > 5 mm inside something in the replay |
|---|---|---|---|---|
| no | 470 | 390 (83%) | 80 | 108 |
| yes | 470 | 453 (96%) | 17 | 108 |

'Flagged' means the body check caught it before doing it (a real robot would not try); the replay column is what would have hit something anyway.
