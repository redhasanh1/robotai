from hand.sim import SimHand


def test_open_hand_drops_everything():
    for obj in ("ball", "can"):
        assert not SimHand(obj).grasp_test([0, 0, 0, 0, 0, 0])["held"]


def test_power_grasp_holds_can():
    r = SimHand("can").grasp_test([0.9, 0.9, 0.9, 0.9, 0.9, 0])
    assert r["held"] and r["touching"]


def test_deterministic():
    a = SimHand("ball").grasp_test([0.9, 0.6, 0.7, 0.5, 0.9, 0])
    b = SimHand("ball").grasp_test([0.9, 0.6, 0.7, 0.5, 0.9, 0])
    assert a == b
