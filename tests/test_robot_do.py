"""Full-body command skills: sentence -> steps, and every step is reachable by the arm (IK)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import robot_do as R  # noqa: E402
from hand.inmoov_sim import build_model  # noqa: E402


def test_planner_understands_the_task_list_and_pronouns():
    for c in R.TASKS:
        steps, unknown = R.plan(c)
        assert steps and not unknown, c
    assert R.plan("grab the orange and put it on the right")[0] == [("pick", "ball"), ("place", "ball", "right")]
    assert R.plan("push the ball forward")[0] == [("push", "ball", "away")]
    assert R.plan("stack the block on the can")[0] == [("stack", "block", "can")]
    assert R.plan("walk the dog") == ([], ["walk the dog"])


def test_every_task_is_reachable_and_ends_with_nothing_held():
    m = build_model(meshes=False, extra=R.scene())
    for c in R.TASKS:
        rb = R.Robot(m)
        rb.run(R.plan(c)[0])
        assert not [s for s in rb.say if "reach" in s], (c, rb.say)
        assert rb.held is None and rb.frames


def test_stack_moves_the_object_on_top():
    m = build_model(meshes=False, extra=R.scene())
    rb = R.Robot(m)
    rb.run([("stack", "block", "can")])
    assert abs(rb.pos["block"][0] - rb.pos["can"][0]) < 1e-6
    assert rb.pos["block"][2] > rb.pos["can"][2] + 0.05
