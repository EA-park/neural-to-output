import math
import time

from ..part import Part

GESTURES = {
    "grip": [1.4, 0.0] * 4,
    "release": [0.0] * 8,
    # Ported qualitatively from AmazingHand-main/PythonExample/AmazingHand_Demo.py's
    # gesture functions (Move_Index/Middle/Ring/Thumb(Angle_1, Angle_2, Speed) real
    # servo-degree calls) -- not an exact biomechanical conversion. Each finger here
    # is a single [curl, 0.0] pair on the same 0 (open, matches "release") .. 1.4 rad
    # (fully closed, matches "grip") scale grip/release already use; motor2 stays 0.0
    # for every gesture, same as grip/release. [index, middle, ring, thumb] order.
    "open_hand": [0.0] * 8,  # OpenHand() -- same pose as "release"
    "close_hand": [1.4, 0.0] * 4,  # CloseHand() -- same pose as "grip"
    "clench_hand": [0.3, 0.0, 0.0, 0.0, 1.0, 0.0, 1.2, 0.0],  # ClenchHand()
    "victory": [0.0, 0.0, 0.0, 0.0, 1.4, 0.0, 1.4, 0.0],  # index+middle extended
    "index_pointing": [0.0, 0.0, 1.4, 0.0, 1.4, 0.0, 1.4, 0.0],
    "nonono": [0.2, 0.0, 1.4, 0.0, 1.4, 0.0, 1.4, 0.0],  # mid-wag snapshot
    "perfect": [1.3, 0.0, 0.0, 0.0, 0.4, 0.0, 1.1, 0.0],
}

_MOTOR_IDS = [1, 2, 3, 4, 5, 6, 7, 8]  # finger1(index)..finger4(thumb), motor1/motor2 each

_MOTOR_OFFSETS_RAD = [
    0.12217304763960307,  # finger1 motor1
    0.08726646259971647,  # finger1 motor2
    0.0,  # finger2 motor1
    0.12217304763960307,  # finger2 motor2
    0.08726646259971647,  # finger3 motor1
    0.12217304763960307,  # finger3 motor2
    0.0,  # finger4 motor1
    0.12217304763960307,  # finger4 motor2
]
"""Per-motor zero-position offset (radians), copied from this validated right hand's
own calibration file (`AmazingHand-main/Demo/AHControl/config/r_hand.toml`). A
different physical unit needs recalibrating with that repo's own `get_zeros`/
`set_zeros` tools first -- these numbers are specific to the unit they came from."""

_MOTOR_INVERT = [False] * 8

_SAFE_RANGE_RAD = (-math.pi / 2, math.pi / 2)
"""Backstop clamp -- the vendor SDK has no built-in safe-range limiting at all. +-pi/2
matches every `finger{1-4}_motor{1,2}` joint's own `jnt_range` in the (currently
removed, see robot/simulation/) bundled MJCF, generated from the real hand's CAD --
the most authoritative mechanical range-of-motion data available. `GESTURES`' own
values plus the largest `_MOTOR_OFFSETS_RAD` entry never exceed ~1.52 rad, safely
inside this."""


class AmazingHand(Part):
    """Owns the real AmazingHand (right) servo connection directly -- `goal()` is a
    pure lookup (no I/O), `move()` actually drives the hardware. Connection to the
    vendor `rustypot` serial SDK is lazy (first `move()` call), so building/using an
    `AmazingHand` for `goal()` only never needs `rustypot` installed."""

    MOVE_SETTLE_S = 1.0
    """How long `move()` sleeps after issuing every motor's target, before returning
    -- an estimate, not measured against the real hand (the vendor SDK exposes no
    position read-back, unlike `SO101Arm`'s `get_observation()`, so there's no way to
    detect true completion). Without this, `move()` would return -- and
    `Part.done_event` would fire -- the instant commands are *sent*, not when the
    hand actually finishes moving; `Robot.router()`/`N2O.run()` rely on `done_event`
    meaning genuine physical completion to know it's safe to issue the next command.
    Tune this if it's clearly too short/long for your unit."""

    def __init__(self, port: str = "", baudrate: int = 1_000_000, timeout: float = 0.5,
                 goal_speed: int = 5):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.goal_speed = goal_speed
        self._servo = None

    def goal(self, cmd):
        try:
            return GESTURES[cmd]
        except KeyError:
            raise ValueError(f"unknown AmazingHand gesture: {cmd!r}") from None

    def move(self, cmd):
        pose = self.goal(cmd)
        self._ensure_servo()
        for i, motor_id in enumerate(_MOTOR_IDS):
            target = pose[i] + _MOTOR_OFFSETS_RAD[i]
            if _MOTOR_INVERT[i]:
                target = -target
            target = min(max(target, _SAFE_RANGE_RAD[0]), _SAFE_RANGE_RAD[1])
            self._servo.write_goal_speed(motor_id, self.goal_speed)
            self._servo.write_goal_position(motor_id, target)
            time.sleep(0.005)
        time.sleep(self.MOVE_SETTLE_S)

    def disconnect(self):
        if self._servo is not None:
            for motor_id in _MOTOR_IDS:
                self._servo.write_torque_enable(motor_id, 2)

    def _ensure_servo(self):
        if self._servo is None:
            from rustypot import Scs0009PyController

            self._servo = Scs0009PyController(
                serial_port=self.port, baudrate=self.baudrate, timeout=self.timeout
            )
            for motor_id in _MOTOR_IDS:
                self._servo.write_torque_enable(motor_id, 1)
