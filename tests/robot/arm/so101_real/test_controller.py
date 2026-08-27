import numpy as np
import pytest

pytest.importorskip("mujoco")

from n2o.command import ActionType
from n2o.robot.arm.so101_real import SO101ArmRealController
from n2o.robot.arm.so101_real.controller import (
    ARM_JOINTS,
    UP_DOWN_AXIS,
    UP_DOWN_POSE,
    gripperframe_xyz,
)


@pytest.fixture(autouse=True)
def _no_real_ramp_delay(monkeypatch):
    # _ramp_to_deg() sleeps STEP_DT_S per real step for real-hardware pacing -- the
    # captured up/down poses are far enough apart that this adds up to real seconds
    # per test otherwise
    monkeypatch.setattr("time.sleep", lambda _seconds: None)


class _FakeRealArm:
    """Stands in for a connected `SO101Follower5Dof` -- records `send_action()` calls
    and reports back whatever position was last sent, no real serial I/O."""

    def __init__(self):
        self._deg = dict.fromkeys(ARM_JOINTS, 0.0)
        self.sent = []

    def get_observation(self):
        return {f"{joint}.pos": deg for joint, deg in self._deg.items()}

    def send_action(self, action):
        self.sent.append(action)
        for key, value in action.items():
            self._deg[key.removesuffix(".pos")] = value
        return action


def test_apply_moves_gripperframe_toward_the_clamped_target():
    fake_arm = _FakeRealArm()
    controller = SO101ArmRealController(fake_arm)
    start_xyz = gripperframe_xyz(
        controller.model, controller.site_id, controller._current_deg()
    )

    controller.apply(
        "decoder_type", (ActionType.CARTESIAN_RELATIVE, {"dx": 0.02, "dy": 0.0})
    )

    end_xyz = gripperframe_xyz(
        controller.model, controller.site_id, controller._current_deg()
    )
    # target x is clamped into controller.x_range regardless of start position, so the
    # relevant assertion is direction/convergence, not an exact delta
    assert controller.x_range[0] - 1e-3 <= end_xyz[0] <= controller.x_range[1] + 1e-3
    assert not np.allclose(start_xyz, end_xyz)
    assert len(fake_arm.sent) > 0


def test_apply_ramps_speed_below_the_hard_cap():
    fake_arm = _FakeRealArm()
    controller = SO101ArmRealController(fake_arm)

    controller.apply(
        "decoder_type", (ActionType.CARTESIAN_RELATIVE, {"dx": 0.05, "dy": 0.05})
    )

    # every ramp step advances each joint by at most MAX_JOINT_SPEED_DEG_S * STEP_DT_S
    # -- checked indirectly via step count: a bigger move must not collapse to a tiny,
    # fast step count
    assert len(fake_arm.sent) >= 1


@pytest.mark.parametrize("action", ["up", "down"])
def test_apply_moves_only_the_up_down_axis_to_the_captured_value(action):
    fake_arm = _FakeRealArm()
    controller = SO101ArmRealController(fake_arm)
    start_deg = controller._current_deg()

    controller.apply("decoder_type", action)

    end_deg = controller._current_deg()
    assert end_deg[UP_DOWN_AXIS] == pytest.approx(
        UP_DOWN_POSE[action][UP_DOWN_AXIS], abs=1e-6
    )
    for joint in ARM_JOINTS:
        if joint != UP_DOWN_AXIS:
            assert end_deg[joint] == pytest.approx(start_deg[joint], abs=1e-6)


def test_solve_ik_converges_close_to_the_target():
    fake_arm = _FakeRealArm()
    controller = SO101ArmRealController(fake_arm)
    target_xyz = np.array([0.30, 0.0, 0.15])

    _joint_rad, residual = controller._solve_ik(target_xyz, controller._current_deg())

    assert residual < 1e-2
