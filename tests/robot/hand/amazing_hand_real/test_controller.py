import pytest

pytest.importorskip("rustypot")

import numpy as np

from n2o.robot.hand.amazing_hand_real import AmazingHandRealController
from n2o.robot.hand.amazing_hand_real.controller import (
    _MOTOR_IDS,
    _MOTOR_OFFSETS_RAD,
)
from n2o.robot.simulation.amazing_hand import HAND_ACTION_POSE


class _FakeServo:
    def __init__(self, **kwargs):
        self.connect_kwargs = kwargs
        self.torque = {}
        self.speeds = []
        self.positions = []

    def write_torque_enable(self, motor_id, mode):
        self.torque[motor_id] = mode

    def write_goal_speed(self, motor_id, speed):
        self.speeds.append((motor_id, speed))

    def write_goal_position(self, motor_id, pos):
        self.positions.append((motor_id, pos))


@pytest.fixture
def fake_servo(monkeypatch):
    monkeypatch.setattr("rustypot.Scs0009PyController", _FakeServo)
    return _FakeServo


def test_construction_torque_enables_every_motor(fake_servo):
    controller = AmazingHandRealController(serial_port="/dev/fake")

    assert controller._servo.torque == dict.fromkeys(_MOTOR_IDS, 1)


def test_apply_sends_pose_plus_calibration_offset(fake_servo):
    controller = AmazingHandRealController(serial_port="/dev/fake")

    controller.apply("decoder_type", "grip")

    expected = [
        HAND_ACTION_POSE["grip"][i] + _MOTOR_OFFSETS_RAD[i]
        for i in range(len(_MOTOR_IDS))
    ]
    actual = [pos for _motor_id, pos in controller._servo.positions]
    np.testing.assert_allclose(actual, expected)
    assert [motor_id for motor_id, _pos in controller._servo.positions] == _MOTOR_IDS


def test_disconnect_torque_disables_every_motor(fake_servo):
    controller = AmazingHandRealController(serial_port="/dev/fake")

    controller.disconnect()

    assert controller._servo.torque == dict.fromkeys(_MOTOR_IDS, 2)
