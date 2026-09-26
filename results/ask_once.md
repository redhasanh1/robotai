# Ask once, never again (tools/ask_once.py)

12 requests each missing one fact (which of two things / where something lives). A simulated person answers truthfully. The robot may ask at most one question per request; answers are kept.

| robot | done | questions asked |
|---|---|---|
| today | 0/12 | 0 |
| guess (first idea) | 1/12 | 9 |
| guess (common sense) | 6/12 | 9 |
| ask one question | 12/12 | 9 |
| again (same knowledge) | 12/12 | 0 |

| request | today | common-sense guess | ask | question it asked |
|---|---|---|---|---|
| put the towel away | no | yes | yes | I don't know where the towel lives yet - where does it go? (sink, rack, washer, basket, kitchen, laundry, living room) |
| put the ball away | no | yes | yes | I don't know where the ball lives yet - where does it go? (sink, rack, washer, basket, kitchen, laundry, living room) |
| put the cup away | no | yes | yes | I don't know where the cup lives yet - where does it go? (sink, rack, washer, basket, kitchen, laundry, living room) |
| put the soda can back | no | yes | yes | I don't know where the soda can lives yet - where does it go? (sink, rack, washer, basket, kitchen, laundry, living room) |
| put the book away | no | no | yes | I don't know where the book lives yet - where does it go? (sink, rack, washer, basket, kitchen, laundry, living room) |
| put the sponge back | no | yes | yes | I don't know where the sponge lives yet - where does it go? (sink, rack, washer, basket, kitchen, laundry, living room) |
| put the shirt in the washer | no | no | yes | I see a red shirt and a white shirt - which one do you mean? |
| bring me the dish | no | no | yes | I see a cup and a plate - which one do you mean? |
| put the dish in the sink | no | no | yes | - |
| hand me the shirt | no | no | yes | - |
| put the plate away | no | yes | yes | I don't know where the plate lives yet - where does it go? (sink, rack, washer, basket, kitchen, laundry, living room) |
| put the shirt on the living room table | no | no | yes | - |

House knowledge afterwards: which = {'shirt': 'white shirt', 'dish': 'plate'}; lives in = {'towel': 'basket', 'ball': 'basket', 'cup': 'rack', 'soda can': 'kitchen', 'book': 'kitchen', 'sponge': 'sink', 'plate': 'rack'}
