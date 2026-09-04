import pytest

from n2o.robot.hand import GESTURES, AmazingHand
from n2o.robot.hand.amazing_hand_right import _MOTOR_IDS, _MOTOR_OFFSETS_RAD


@pytest.fixture(autouse=True)
def _no_real_settle_delay(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _seconds: None)


class _FakeServo:
    """Stands in for `rustypot.Scs0009PyController` -- records calls, no real serial
    I/O."""

    def __init__(self):
        self.torque = {}
        self.positions = []

    def write_torque_enable(self, motor_id, mode):
        self.torque[motor_id] = mode

    def write_goal_speed(self, motor_id, speed):
        pass

    def write_goal_position(self, motor_id, pos):
        self.positions.append((motor_id, pos))


def _hand_with_fake_servo(monkeypatch):
    hand = AmazingHand(port="/dev/fake")
    fake_servo = _FakeServo()
    monkeypatch.setattr(
        hand, "_ensure_servo", lambda: setattr(hand, "_servo", fake_servo)
    )
    return hand, fake_servo


def test_goal_returns_a_known_gesture():
    hand = AmazingHand()
    assert hand.goal("grip") == GESTURES["grip"]


def test_goal_raises_for_an_unknown_gesture():
    hand = AmazingHand()
    with pytest.raises(ValueError, match="unknown AmazingHand gesture"):
        hand.goal("wave")


def test_move_sends_pose_plus_calibration_offset_to_every_motor(monkeypatch):
    hand, fake_servo = _hand_with_fake_servo(monkeypatch)

    hand.move("grip")

    expected = [
        GESTURES["grip"][i] + _MOTOR_OFFSETS_RAD[i] for i in range(len(_MOTOR_IDS))
    ]
    actual = [pos for _motor_id, pos in fake_servo.positions]
    assert actual == pytest.approx(expected)
    assert [motor_id for motor_id, _pos in fake_servo.positions] == _MOTOR_IDS


def test_disconnect_torque_disables_every_motor(monkeypatch):
    hand, fake_servo = _hand_with_fake_servo(monkeypatch)
    hand.move("release")

    hand.disconnect()

    assert fake_servo.torque[_MOTOR_IDS[0]] == 2


def test_ensure_servo_torque_enables_every_motor_via_the_real_sdk_path(monkeypatch):
    # Unlike the tests above (which bypass _ensure_servo() entirely via a
    # monkeypatch), this one fakes only the vendor SDK class itself, so it's the
    # real _ensure_servo() body -- and its torque-enable-on-first-move() behavior --
    # that runs.
    pytest.importorskip("rustypot")
    fake_servo = _FakeServo()
    monkeypatch.setattr("rustypot.Scs0009PyController", lambda **kwargs: fake_servo)
    hand = AmazingHand(port="/dev/fake")

    hand.move("release")

    assert fake_servo.torque == dict.fromkeys(_MOTOR_IDS, 1)
