> **INVALID RUN - do not use these numbers.** It ran while the grasping was being rewritten (branch real-grasps): every task with a flat object (remote, book, shirts, plate) failed on 'no clean way to get a hand round it', not on the model. What it does show: 'clear the kitchen counter' and 'hide the apple' reused with 0 model calls. Rerun when the grasp rework is merged.

# Skills the robot writes for itself (tools/skill_growth.py --ai)

Pass 1 programs come from the local model (Qwen2.5-3B 4-bit, :8766). Every task starts from the same clean house.

| pass | tasks | done | model calls | model seconds | done by its own skill |
|---|---|---|---|---|---|
| 1 first time | 7 | 1/7 | 15 | 544 | 0 |
| 2 again | 7 | 1/7 | 14 | 546 | 1 |
| 3 new wording/objects | 6 | 2/6 | 11 | 463 | 1 |

| pass | request | how | done | calls |
|---|---|---|---|---|
| 1 | hide the remote | AI | no | 1 |
| 1 | put the toy away | AI | no | 3 |
| 1 | set the table in the living room | AI | no | 4 |
| 1 | clear the living room table | AI | no | 2 |
| 1 | empty the laundry counter onto the living room table | AI | no | 3 |
| 1 | put the laundry away | AI | no | 1 |
| 1 | clear the kitchen counter | AI | yes | 1 |
| 2 | hide the remote | AI | no | 1 |
| 2 | put the toy away | AI | no | 3 |
| 2 | set the table in the living room | AI | no | 4 |
| 2 | clear the living room table | AI | no | 2 |
| 2 | empty the laundry counter onto the living room table | AI | no | 3 |
| 2 | put the laundry away | AI | no | 1 |
| 2 | clear the kitchen counter | own skill | yes | 0 |
| 3 | hide the book | AI | no | 1 |
| 3 | please hide the soda can | AI | yes | 1 |
| 3 | hide the apple | own skill | yes | 0 |
| 3 | put the book away | AI | no | 3 |
| 3 | set the table in the kitchen | AI | no | 3 |
| 3 | clear the laundry counter | AI | no | 3 |

Skills in the library afterwards:

- `clear kitchen counter` (from "clear the kitchen counter", 2/2 worked): [{'do': 'go', 'to': '{r0}'}, {'do': 'pick', 'obj': 'cup'}, {'do': 'put_in', 'obj': 'cup', 'into': 'rack'}, {'do': 'go', 'to': '{r0}'}, {'do': 'pick', 'obj': 'plate'}, {'do': 'put_in', 'obj': 'plate', 'into': 'rack'}, {'do': 'go', 'to': '{r0}'}, {'do': 'pick', 'obj': 'apple'}, {'do': 'put_on', 'obj': 'apple', 'room': 'living room'}, {'do': 'go', 'to': '{r0}'}, {'do': 'pick', 'obj': 'sponge'}, {'do': 'put_in', 'obj': 'sponge', 'into': 'sink'}]
- `hide {0}` (from "please hide the soda can", 2/2 worked): [{'do': 'go', 'to': 'living room'}, {'do': 'pick', 'obj': '{0}'}, {'do': 'put_in', 'obj': '{0}', 'into': 'sink'}]
