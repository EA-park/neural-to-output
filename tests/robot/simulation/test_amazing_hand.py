import pytest

pytest.importorskip("mujoco")

import numpy as np

from n2o.robot.simulation import AmazingHandSim
from n2o.robot.simulation.amazing_hand import HAND_ACTION_POSE


def test_move_drives_ctrl_to_action_pose():
    hand = AmazingHandSim()

    hand.move("dummy_type", "grip")

    assert np.allclose(hand.data.ctrl, HAND_ACTION_POSE["grip"])


def test_move_updates_qpos():
    hand = AmazingHandSim()
    before = hand.data.qpos.copy()

    hand.move("dummy_type", "grip")

    assert not np.allclose(before, hand.data.qpos)


def test_render_returns_rgb_frame():
    hand = AmazingHandSim()

    frame = hand.render()

    assert frame.shape == (360, 480, 3)


@pytest.mark.parametrize("gesture", sorted(HAND_ACTION_POSE))
def test_move_drives_ctrl_to_every_defined_gesture(gesture):
    hand = AmazingHandSim()

    hand.move("dummy_type", gesture)

    assert np.allclose(hand.data.ctrl, HAND_ACTION_POSE[gesture])
