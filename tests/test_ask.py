"""Ask once, never again: finds the one missing fact, learns it from a spoken answer, never asks twice."""
from hand import ask as A


def test_asks_which_when_one_word_means_two_things():
    k = A.Knowledge()
    q = A.question("put the shirt in the washer", k)
    assert q["kind"] == "which" and set(q["options"]) == {"red shirt", "white shirt"}
    assert A.question("put the shirts in the washer", k) is None          # plural: both, nothing to ask
    assert k.learn(q, "the white one") == "white shirt"
    assert A.rewrite("put the shirt in the washer", k) == "put the white shirt in the washer"


def test_asks_where_things_live_and_remembers():
    k = A.Knowledge()
    answers = []
    prog, unknown, asked = A.plan("put the book away", k, ask=lambda q: answers.append(q) or "it lives in the kitchen")
    assert len(asked) == 1 and not unknown and prog == [{"do": "put_on", "obj": "book", "room": "kitchen"}]
    prog, unknown, asked = A.plan("put the book back", k, ask=lambda q: 1 / 0)          # must not ask again
    assert not asked and prog[0]["room"] == "kitchen"


def test_answer_it_does_not_understand_is_not_stored():
    k = A.Knowledge()
    q = A.question("put the sponge away", k)
    assert k.learn(q, "no idea") is None and "sponge" not in k.homes
