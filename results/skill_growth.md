# Skills the robot writes for itself (tools/skill_growth.py)

Pass 1 programs come from a SCRIPTED TEACHER in pass 1 (measures the library, not the model's composing). Every task starts from the same clean house.

| pass | tasks | done | model calls | model seconds | done by its own skill |
|---|---|---|---|---|---|
| 1 first time | 7 | 7/7 | 7 | 0 | 0 |
| 2 again | 7 | 7/7 | 0 | 0 | 7 |
| 3 new wording/objects | 6 | 4/6 | 6 | 0 | 4 |

| pass | request | how | done | calls |
|---|---|---|---|---|
| 1 | hide the remote | AI | yes | 1 |
| 1 | put the toy away | AI | yes | 1 |
| 1 | set the table in the living room | AI | yes | 1 |
| 1 | clear the living room table | AI | yes | 1 |
| 1 | empty the laundry counter onto the living room table | AI | yes | 1 |
| 1 | put the laundry away | AI | yes | 1 |
| 1 | clear the kitchen counter | AI | yes | 1 |
| 2 | hide the remote | own skill | yes | 0 |
| 2 | put the toy away | own skill | yes | 0 |
| 2 | set the table in the living room | own skill | yes | 0 |
| 2 | clear the living room table | own skill | yes | 0 |
| 2 | empty the laundry counter onto the living room table | own skill | yes | 0 |
| 2 | put the laundry away | own skill | yes | 0 |
| 2 | clear the kitchen counter | own skill | yes | 0 |
| 3 | hide the book | own skill | yes | 0 |
| 3 | please hide the soda can | own skill | yes | 0 |
| 3 | hide the apple | own skill | yes | 0 |
| 3 | put the book away | own skill | yes | 0 |
| 3 | set the table in the kitchen | AI | no | 3 |
| 3 | clear the laundry counter | AI | no | 3 |

Skills in the library afterwards:

- `hide {0}` (from "hide the remote", 5/5 worked): [{'do': 'put_in', 'obj': '{0}', 'into': 'basket'}]
- `put {0} away` (from "put the toy away", 3/3 worked): [{'do': 'put_in', 'obj': '{0}', 'into': 'basket'}]
- `set table in living room` (from "set the table in the living room", 2/2 worked): [{'do': 'put_on', 'obj': 'cup', 'room': 'living room'}, {'do': 'put_on', 'obj': 'plate', 'room': 'living room'}]
- `clear living room table` (from "clear the living room table", 2/2 worked): [{'do': 'put_in', 'obj': 'ball', 'into': 'basket'}, {'do': 'put_on', 'obj': 'book', 'room': 'kitchen'}, {'do': 'put_on', 'obj': 'remote', 'room': 'kitchen'}, {'do': 'put_on', 'obj': 'soda can', 'room': 'kitchen'}]
- `empty laundry counter onto living room table` (from "empty the laundry counter onto the living room table", 2/2 worked): [{'do': 'put_on', 'obj': 'red shirt', 'room': 'living room'}, {'do': 'put_on', 'obj': 'white shirt', 'room': 'living room'}, {'do': 'put_on', 'obj': 'towel', 'room': 'living room'}]
- `put laundry away` (from "put the laundry away", 2/2 worked): [{'do': 'put_in', 'obj': 'towel', 'into': 'basket'}]
- `clear kitchen counter` (from "clear the kitchen counter", 2/2 worked): [{'do': 'put_in', 'obj': 'cup', 'into': 'rack'}, {'do': 'put_in', 'obj': 'plate', 'into': 'rack'}, {'do': 'put_on', 'obj': 'apple', 'room': 'living room'}]
