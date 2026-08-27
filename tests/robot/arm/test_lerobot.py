import pytest

from n2o.robot.arm import LeRobotSO101
from n2o.robot.controller import Controller


class _RecordingController(Controller):
    def __init__(self):
        self.applied_with = None

    def apply(self, decoder_type, command):
        self.applied_with = (decoder_type, command)
        return "applied"


def test_move_raises_without_controller():
    arm = LeRobotSO101()
    with pytest.raises(RuntimeError, match="controller is not set"):
        arm.move("decoder_type", "grip")


def test_move_delegates_to_controller_set_via_constructor():
    controller = _RecordingController()
    arm = LeRobotSO101(controller=controller)

    result = arm.move("decoder_type", "grip")

    assert result == "applied"
    assert controller.applied_with == ("decoder_type", "grip")


def test_move_delegates_to_controller_set_via_attribute():
    arm = LeRobotSO101()
    controller = _RecordingController()
    arm.controller = controller

    arm.move("decoder_type", "grip")

    assert controller.applied_with == ("decoder_type", "grip")
