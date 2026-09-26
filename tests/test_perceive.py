"""Mess perception from pixels: counter cameras, clean house remembered once, stain = new hue at the same depth."""
import mujoco

from hand import home, home_tasks as H, perceive
from hand.inmoov_sim import build_model

M = build_model(meshes=False, extra=home.scene_xml(), mobile=True)


def test_sees_only_the_stained_counter():
    eyes = perceive.Eyes(M).learn()
    assert eyes.survey() == {}
    perceive.set_messes(M, {"living room"})
    seen = eyes.survey()
    perceive.set_messes(M, ())
    assert list(seen) == ["living room"] and "cm across" in seen["living room"]


def test_moving_objects_is_not_a_mess():
    eyes = perceive.Eyes(M).learn()
    for o in ("cup", "remote", "towel"):
        b = M.body_mocapid[mujoco.mj_name2id(M, mujoco.mjtObj.mjOBJ_BODY, home.mocap_name(o))]
        p = eyes.d.mocap_pos[b].copy()
        eyes.d.mocap_pos[b][0] += 0.1
        assert eyes.survey() == {}, o
        eyes.d.mocap_pos[b] = p


def test_spill_prompt_gets_its_mess_from_the_camera():
    seen = H.seen_messes(M, H.SCENES["I spilled something in the living room"])
    assert "living room" in seen
    assert "living room surface" in home.describe_world(home.HomeBody(M, seen))
    H.seen_messes(M, ())
