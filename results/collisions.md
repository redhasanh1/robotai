# Does the arm hit things? (hand/collide.py, tools/collisions.py)

The house sim plays poses back kinematically, and every geom had collisions switched off, so nothing ever checked
whether an arm went through a counter. The check switches on robot-vs-house contacts only (robot links against
counters, containers, the person, the wall and objects) and replays each task at 50 Hz. Not counted: the object the
step is handling, what is in a hand, and fingertips resting on a surface (up to 2 mm).

47 tasks the rules plan (the 50-prompt suite minus the 3 judgement calls):

| | tasks with a contact | worst |
|---|---|---|
| before | 45 / 47 | hand 11 cm through the counter front; wheeled base 9 cm inside every counter |
| after, > 2 mm | 9 / 47 | |
| after, > 5 mm | 4 / 47 | 8 mm (a hand brushing the cup during "do the dishes"); juggling throws |

What was wrong and what fixed it, in the order found:

1. **Hanging arms.** At rest the fingertips hung 1 cm from the counter's front, so every reach swept through it.
   Now the arms go to a CARRY pose (hand in front of the chest, above counter height) between tasks and while driving.
2. **A solid-block counter.** The 28 cm wheel disc sat 9 cm inside it. Counters now have a 4 cm top, the cabinet set
   back 2 cm, and a kick space under it (13 cm high, 11 cm deep - a little deeper than the usual 7.5 cm).
3. **Ends clear, path not.** Joint-space moves between two clear poses dipped through the counter. Every move now
   checks 7 points along its path; if blocked, it tries routes by one or two waypoints (straight above the target,
   straight up from the hand, or a ready pose above the counter edge) and takes the first clear one.
4. **Lift until clear.** A target that puts the hand inside something is raised 1 cm at a time (up to 10 cm).
   When grasping, another object in the way is not lifted over - the hand would miss - it is reported by name
   ("the cup is in the way of the plate") so the plan can move it first.
5. **Crowded containers.** The plate went into the rack right next to the cup and the hand swept through the cup. The
   robot now tries the free spots and uses the first one its hand can drop into without brushing what is there.
6. **Letting go.** Open fingers are longer than curled ones: releasing right above the washer put them 3.5 cm into
   it. Before opening, the open hand is checked; if it would hit, the hand lifts until it clears, then lets go.

7. **Something in the way of a grasp is moved aside**, then the robot takes what it came for ("moving the cup out
   of the way"). The check covers the whole approach - above, the way down, and the hand closing (curling fingers
   sweep sideways).
8. **Juggling at chest height** (25 cm over the counter, near the body) instead of 7 cm over the things on it.

After all of it, default layout: planner problems 0/47, replay contact > 5 mm in 2/47.

## Random clutter (tools/clutter.py, results/clutter.md)

10 random layouts - every object at a random spot on its own counter - times the 47 tasks = 470 runs:

| robot moves obstacles aside | done cleanly | stopped by the body check | replay: arm > 5 mm into something |
|---|---|---|---|
| no | 390 (83%) | 80 | 108 |
| yes | **453 (96%)** | 17 | 108 |

Moving obstacles aside turns 63 blocked tasks into done ones. The last column is the honest gap: in 23% of cluttered
runs the dense replay still finds a hand brushing something by more than 5 mm that the planner's checks (endpoints, 7
points per path, open/closed hand at the grip) did not see - e.g. closing on the ball after being lifted off the
counter brushes a soda can beside it by 8 mm. Next: check every emitted frame the way the replay does.

Every one of these is geometry, not learning: exact, needs no data, and works in a room it has never seen.

Still open: the object in the hand is not checked
against the house (only the arm is).
