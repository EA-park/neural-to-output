import pytest

from n2o.robot.arm import GESTURES, SO101Arm
from n2o.robot.arm.so101 import ARM_JOINTS


def test_ensure_connected_raises_a_clear_error_without_a_calibration_file(tmp_path):
    pytest.importorskip("lerobot")
    arm = SO101Arm(
        port="/dev/fake",
        id="test_calibration_never_exists",
        calibration_dir=tmp_path,
    )

    with pytest.raises(RuntimeError, match="lerobot-calibrate"):
        arm.move("up")


@pytest.fixture(autouse=True)
def _no_real_ramp_delay(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _seconds: None)


class _FakeRealArm:
    """Stands in for a connected `SO101Follower5Dof` -- records `send_action()` calls,
    no real serial I/O."""

    def __init__(self, start_deg):
        self._deg = dict(start_deg)
        self.sent = []

    def get_observation(self):
        return {f"{joint}.pos": deg for joint, deg in self._deg.items()}

    def send_action(self, action):
        self.sent.append(action)
        for key, value in action.items():
            self._deg[key.removesuffix(".pos")] = value


def test_goal_returns_a_known_gesture():
    arm = SO101Arm()
    assert arm.goal("up") == GESTURES["up"]


def test_goal_raises_for_an_unknown_gesture():
    arm = SO101Arm()
    with pytest.raises(ValueError, match="unknown SO101Arm gesture"):
        arm.goal("sideways")


def test_move_ramps_only_the_up_down_axis(monkeypatch):
    start_deg = dict.fromkeys(ARM_JOINTS, 10.0)
    fake_arm = _FakeRealArm(start_deg)
    arm = SO101Arm(port="/dev/fake")
    monkeypatch.setattr(
        arm, "_ensure_connected", lambda: setattr(arm, "_real_arm", fake_arm)
    )

    arm.move("up")

    end_deg = fake_arm._deg
    assert end_deg["shoulder_pan"] == pytest.approx(GESTURES["up"]["shoulder_pan"])
    for joint in ARM_JOINTS:
        if joint != "shoulder_pan":
            assert end_deg[joint] == pytest.approx(start_deg[joint])
    assert len(fake_arm.sent) > 0
