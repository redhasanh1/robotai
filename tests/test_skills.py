"""Skills the robot writes for itself: templates with object slots, Beta gate, body-checked reuse with no model call."""
from hand import home, home_tasks as H, skills
from hand.inmoov_sim import build_model

M = build_model(meshes=False, extra=home.scene_xml(), mobile=True)
HIDE = [{"do": "put_in", "obj": "remote", "into": "basket"}]


def test_template_turns_named_objects_into_slots():
    assert skills.template("Please hide the remote") == ("hide {0}", ["remote"], [])
    assert skills.template("move the soda can and the towel to the kitchen") == \
        ("move {0} and {1} to {r0}", ["soda can", "towel"], ["kitchen"])


def test_one_success_is_trusted_one_failure_is_not():
    lib = skills.Library()
    assert lib.recall("hide the book") is None
    lib.learn("hide the remote", HIDE, True)
    hit = lib.recall("hide the book")
    assert hit["program"] == [{"do": "put_in", "obj": "book", "into": "basket"}]
    lib.learn("hide the book", hit["program"], False)
    assert lib.recall("hide the ball") is None           # last use failed: ask the model again
    lib.learn("hide the ball", [{"do": "put_in", "obj": "ball", "into": "washer"}], True)
    assert lib.recall("hide the cup")["program"][0]["into"] == "washer"      # the new program replaced the old one


def test_do_task_uses_own_skill_without_the_model():
    class NoModel:
        calls = []

        def program(self, *a, **k):
            raise AssertionError("the model was asked")

    lib = skills.Library()
    lib.learn("hide the remote", HIDE, True)
    prog, how, part, key = H.do_task("hide the book", M, NoModel(), lib, say=lambda s: None)
    assert how == "own skill" and home.HomeBody(M).run(prog).where["book"] == ("in", "basket")


def test_reuse_is_body_checked():
    lib = skills.Library()
    lib.learn("hide the remote", HIDE, True)
    lib.skills["hide {0}"]["program"] = [{"do": "put_in", "obj": "{0}", "into": "oven"}]     # no oven in this house
    prog, how, _, _ = H.do_task("hide the book", M, None, lib, say=lambda s: None)
    assert how == "not understood"


def test_rooms_are_slots_unless_the_room_chose_the_objects():
    lib = skills.Library()
    lib.learn("set the table in the living room", [{"do": "put_on", "obj": "cup", "room": "living room"},
                                                   {"do": "put_on", "obj": "plate", "room": "living room"}], True)
    assert [a["room"] for a in lib.recall("set the table in the kitchen")["program"]] == ["kitchen", "kitchen"]
    lib.learn("clear the living room table", [{"do": "put_on", "obj": o, "room": "kitchen"}
                                              for o in ("book", "remote", "soda can")] +
              [{"do": "put_in", "obj": "ball", "into": "basket"}], True)
    assert lib.recall("clear the living room table") is not None
    assert lib.recall("clear the laundry counter") is None      # those objects were picked because of the room
