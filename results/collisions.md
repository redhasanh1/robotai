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

Every one of these is geometry, not learning: exact, needs no data, and works in a room it has never seen.

Still open: juggling throws use their own motion code and are not checked yet; the object in the hand is not checked
against the house (only the arm is); moving an obstacle out of the way is reported, not yet done automatically.
