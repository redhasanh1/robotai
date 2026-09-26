"""The simulated home: base-aware reach, chores end in the right place, the 50-prompt suite by rules."""
from hand import home, home_tasks as H
from hand.inmoov_sim import build_model

M = build_model(meshes=False, extra=home.scene_xml(), mobile=True)


def test_chores_drive_between_rooms_and_finish_clean():
    b = home.HomeBody(M).run([{"do": "put_in", "obj": "cup", "into": "rack"},
                              {"do": "put_in", "obj": "red shirt", "into": "washer"},
                              {"do": "give", "obj": "remote"}, {"do": "wipe", "room": "kitchen"}])
    assert not b.problems
    assert b.where["cup"] == ("in", "rack") and b.where["red shirt"] == ("in", "washer")
    assert b.where["remote"] == ("given",) and "kitchen" in b.wiped
    assert b.held == {"right": None, "left": None}


def test_rules_understand_47_of_50_and_leave_judgement_calls_to_the_ai():
    rows = H.score(M, say=lambda s: None)
    assert sum(r["passed"] for r in rows) >= 47
    left = [r["prompt"] for r in rows if r["how"] == "not understood"]
    assert "I spilled something in the living room" in left


def test_verb_carries_over_and():
    assert H.plan("put the cup in the sink and the plate in the rack")[0] == [
        {"do": "put_in", "obj": "cup", "into": "sink"}, {"do": "put_in", "obj": "plate", "into": "rack"}]
    assert H.plan("bring me the remote and the soda can")[0] == [{"do": "give", "obj": "remote"},
                                                                 {"do": "give", "obj": "soda can"}]


def test_mess_is_seen_and_wiped():
    b = home.HomeBody(M, {"living room": "a sticky puddle"})
    assert "living room surface: a sticky puddle" in home.describe_world(b)
    b.run([{"do": "wipe", "room": "living room"}])
    assert "living room" in b.wiped and not b.messes, b.problems
    assert "nothing dirty in view" in home.describe_world(b)


def test_errors_name_the_real_step():
    b = home.HomeBody(M).run([{"do": "go", "to": "kitchen"}, {"do": "pick", "obj": "unicorn"}])
    assert b.problems and b.problems[0].startswith("step 2:"), b.problems


def test_splice_repair_offers_only_steps_that_work():
    mess = {"living room": "a sticky puddle and some crumbs"}
    prog = [{"do": "go", "to": "living room"}, {"do": "pick", "obj": "crumbs"},
            {"do": "put_on", "obj": "crumbs", "room": "kitchen"}]
    opts = H.step_options(prog, 1, M, mess)
    assert {"do": "wipe", "room": "living room"} in opts and {"do": "remove"} in opts
    for o in opts:                      # every offered step runs clean where it stands
        assert not home.HomeBody(M, mess).run(prog[:1] + ([] if o["do"] == "remove" else [o])).problems

    class Picker:                       # stands in for the model: always takes the wipe when it's offered
        def program(self, *a, **k):
            return {"program": prog}

        def choose_step(self, command, p, k, error, options):
            return next((i for i, o in enumerate(options) if o["do"] == "wipe"), 0)

    fixed, _ = H.think("I spilled something in the living room", M, Picker(), say=lambda s: None, messes=mess)
    body = home.HomeBody(M, mess).run(fixed)
    assert not body.problems and "living room" in body.wiped and not body.messes
