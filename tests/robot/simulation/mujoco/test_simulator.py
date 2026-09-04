import numpy as np
import pytest

pytest.importorskip("mujoco")

from n2o.robot.arm.so101 import GESTURES as ARM_GESTURES
from n2o.robot.hand.amazing_hand_right import GESTURES as HAND_GESTURES
from n2o.robot.simulation.mujoco.simulator import Simulator


def _actuator_ctrl(sim, part, name):
    import mujoco

    actuator_id = mujoco.mj_name2id(
        sim.model, mujoco.mjtObj.mjOBJ_ACTUATOR, sim.actuator_name(part, name)
    )
    return sim.data.ctrl[actuator_id]


def test_rejects_unknown_parts():
    with pytest.raises(ValueError, match="parts must be a non-empty subset"):
        Simulator(["tentacle"])


def test_drive_arm_moves_ctrl_toward_the_gesture():
    sim = Simulator(["arm"])

    sim.drive("arm", ARM_GESTURES["up"])

    assert _actuator_ctrl(sim, "arm", "shoulder_pan") == pytest.approx(
        np.radians(ARM_GESTURES["up"]["shoulder_pan"])
    )


def test_drive_hand_moves_ctrl_toward_the_gesture():
    sim = Simulator(["hand"])

    sim.drive("hand", HAND_GESTURES["grip"])

    assert _actuator_ctrl(sim, "hand", "finger1_motor1") == pytest.approx(
        HAND_GESTURES["grip"][0]
    )


def test_drive_both_parts_merged_prefixes_the_hand_actuators():
    # This is the exact path that broke after moving lerobot_robot_so101_5dof under
    # arm/so101/ -- Simulator._arm_ctrl() imports real_deg_to_mj_rad via a relative
    # import that has to be updated in lockstep with that move (see CLAUDE.md).
    sim = Simulator(["arm", "hand"])

    sim.drive("arm", ARM_GESTURES["down"])
    sim.drive("hand", HAND_GESTURES["release"])

    assert sim.actuator_name("hand", "finger1_motor1") == "hand_finger1_motor1"
    assert _actuator_ctrl(sim, "arm", "shoulder_pan") == pytest.approx(
        np.radians(ARM_GESTURES["down"]["shoulder_pan"])
    )
    assert _actuator_ctrl(sim, "hand", "finger1_motor1") == pytest.approx(0.0)


def test_render_returns_an_rgb_frame():
    sim = Simulator(["arm"])

    frame = sim.render()

    assert frame.shape == (360, 480, 3)


def test_drive_arm_actually_steps_physics_not_just_sets_ctrl():
    sim = Simulator(["arm"])
    before = sim.data.qpos.copy()

    sim.drive("arm", ARM_GESTURES["up"])

    assert not np.allclose(before, sim.data.qpos)


def test_drive_hand_actually_steps_physics_not_just_sets_ctrl():
    sim = Simulator(["hand"])
    before = sim.data.qpos.copy()

    sim.drive("hand", HAND_GESTURES["grip"])

    assert not np.allclose(before, sim.data.qpos)


@pytest.mark.parametrize("gesture", sorted(HAND_GESTURES))
def test_drive_hand_reaches_every_defined_gesture(gesture):
    sim = Simulator(["hand"])

    sim.drive("hand", HAND_GESTURES[gesture])

    actual = [
        _actuator_ctrl(sim, "hand", name)
        for name in (
            "finger1_motor1",
            "finger1_motor2",
            "finger2_motor1",
            "finger2_motor2",
            "finger3_motor1",
            "finger3_motor2",
            "finger4_motor1",
            "finger4_motor2",
        )
    ]
    assert actual == pytest.approx(HAND_GESTURES[gesture])
