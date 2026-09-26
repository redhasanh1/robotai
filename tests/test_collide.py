"""The arm must not go through the house: detector works, chores stay clear, a crowded rack is handled."""
from hand import collide, home, home_tasks as H
from hand.inmoov_sim import build_model

M = build_model(meshes=False, extra=home.scene_xml(), mobile=True)


def test_detector_sees_a_robot_inside_a_counter():
    c = home.to_world("kitchen", (0, -0.33))

    class Inside:
        frames = [(0.1, {"base_x": c[0], "base_y": c[1]}, None)]
        step_at = []

    assert any(h["hit"] == "counter_kitchen" for h in collide.sweep(M, Inside(), stride=1))


def test_chores_stay_clear():
    for p in ("put the red shirt in the washing machine", "put the towel in the basket", "wipe the kitchen counter"):
        b = home.HomeBody(M).run(H.plan(p)[0])
        assert not b.problems, (p, b.problems)
        deep = [h for h in collide.sweep(M, b, stride=2) if h["depth"] > 0.005]
        assert not deep, (p, deep[:2])


def test_second_dish_goes_where_the_hand_clears_the_first():
    b = home.HomeBody(M).run([{"do": "put_in", "obj": "cup", "into": "rack"},
                              {"do": "put_in", "obj": "plate", "into": "rack"}])
    assert not b.problems and b.where["plate"] == ("in", "rack")


def test_moves_an_object_that_is_in_the_way():
    import numpy as np
    b = home.HomeBody(M)
    pl = home.to_local(home.ROOMS["kitchen"], b.pos["plate"][:2])
    c = home.to_world("kitchen", (pl[0] + 0.06, pl[1]))              # the cup right beside the plate
    b.pos["cup"] = np.array([c[0], c[1], b.pos["cup"][2]])
    b.run([{"do": "pick", "obj": "plate"}], finish=False)
    assert "moving the cup out of the way" in b.said and not b.problems
    assert b.where["plate"][0] == "held"
