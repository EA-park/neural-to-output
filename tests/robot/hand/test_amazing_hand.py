import pytest

from n2o.robot.controller import Controller
from n2o.robot.hand import AmazingHand


class _RecordingController(Controller):
    def __init__(self):
        self.applied_with = None

    def apply(self, decoder_type, command):
        self.applied_with = (decoder_type, command)
        return "applied"


def test_move_raises_without_controller():
    hand = AmazingHand()
    with pytest.raises(RuntimeError, match="controller is not set"):
        hand.move("decoder_type", "grip")


def test_move_delegates_to_controller_set_via_constructor():
    controller = _RecordingController()
    hand = AmazingHand(controller=controller)

    result = hand.move("decoder_type", "grip")

    assert result == "applied"
    assert controller.applied_with == ("decoder_type", "grip")


def test_move_delegates_to_controller_set_via_attribute():
    hand = AmazingHand()
    controller = _RecordingController()
    hand.controller = controller

    hand.move("decoder_type", "grip")

    assert controller.applied_with == ("decoder_type", "grip")
