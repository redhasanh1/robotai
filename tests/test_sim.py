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


def test_slip_check_flags_drops_fast():
    drop = SimHand("ball").grasp_test([0, 0, 0, 0, 0, 0])
    assert not drop["held"] and drop["slip_t"] is not None and drop["slip_t"] < 0.3
    hold = SimHand("can").grasp_test([0.9, 0.9, 0.9, 0.9, 0.9, 0])
    assert hold["held"] and hold["slip_t"] is None


def test_full_inmoov_skeleton_builds_and_moves():
    import mujoco
    from hand.inmoov_sim import build_model
    m = build_model(meshes=False)                      # no downloaded meshes needed
    assert m.njnt == 56 and m.nu == 56                   # the free-spinning stand joint is welded
    d = mujoco.MjData(m)
    d.ctrl[m.actuator("right_elbow_x").id] = 1.0
    for _ in range(1500):
        mujoco.mj_step(m, d)
    assert abs(d.joint("right_elbow_x").qpos[0] - 1.0) < 0.1
