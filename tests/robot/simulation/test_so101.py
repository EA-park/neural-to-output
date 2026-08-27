import pytest

pytest.importorskip("mujoco")

import numpy as np

from n2o.robot.simulation import SO101ArmSim
from n2o.robot.simulation.so101 import ARM_ACTION_POSE, ARM_JOINTS


def test_move_drives_ctrl_to_action_pose():
    arm = SO101ArmSim()

    arm.move("dummy_type", "up")

    expected = np.array([ARM_ACTION_POSE["up"][joint] for joint in ARM_JOINTS])
    assert np.allclose(arm.data.ctrl, expected)


def test_move_updates_qpos():
    arm = SO101ArmSim()
    before = arm.data.qpos.copy()

    arm.move("dummy_type", "up")

    assert not np.allclose(before, arm.data.qpos)


def test_render_returns_rgb_frame():
    arm = SO101ArmSim()

    frame = arm.render()

    assert frame.shape == (360, 480, 3)
