from hand import tendon_sim as T


def test_braid_closes_and_overtravel_stalls():
    r = T.sweep(T.Finger(), steps=120, settle=60)
    assert r["closes_to"] > 0.85
    assert r["stall_horn_rad"] is not None and r["stall_horn_rad"] > r["horn_for_90pct"]


def test_stretchy_line_does_not_close_and_object_stalls_early():
    assert T.sweep(T.Finger(stretch=0.02), steps=120, settle=60)["closes_to"] < 0.7
    obj = T.sweep(T.Finger(obstacle=0.45), steps=120, settle=60)
    assert obj["flex_at_stall"] is not None and obj["flex_at_stall"] < 0.8
