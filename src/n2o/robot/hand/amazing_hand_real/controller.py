import math
import time

from ...controller import Controller
from ...simulation.amazing_hand import HAND_ACTION_POSE

_MOTOR_IDS = [
    1,
    2,
    3,
    4,
    5,
    6,
    7,
    8,
]  # finger1(index)..finger4(thumb), motor1/motor2 each

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
"""Backstop clamp -- the vendor SDK has no built-in safe-range limiting at all (per
AmazingHand-main's own README: "a kind of smart software needs to be built" for safe
grasping, not yet done upstream either). +-pi/2 (+-90 degrees) is every
`finger{1-4}_motor{1,2}` joint's own `jnt_range` in the bundled MJCF
(`n2o/robot/simulation/assets/amazing_hand_right/mjcf/demo_scene.xml`, verified by
inspecting `mujoco.MjModel(...).jnt_range` directly) -- the model was generated from
the real hand's CAD (see that asset dir's `NOTICE.md`), so this is the most authoritative
mechanical range-of-motion data available, not a guess. `HAND_ACTION_POSE`'s own values
plus the largest `_MOTOR_OFFSETS_RAD` entry never exceed ~1.52 rad, safely inside this."""


class AmazingHandRealController(Controller):
    """Drives the real AmazingHand (right) over its vendor `rustypot` serial SDK.

    Reuses `n2o.robot.simulation.amazing_hand.HAND_ACTION_POSE` (`"grip"`/`"release"`)
    unchanged -- confirmed equivalent to what real hardware expects by
    `AmazingHand-main/Demo/AHControl/src/main.rs` (the project's own production
    driver), whose calibration formula is exactly `real_goal_rad = mujoco_joint_rad +
    offset` (negated if `invert`). So the same action vocabulary the MuJoCo sim
    controller uses drives the real hand too, just shifted by each motor's own
    `offset`/`invert`.

    No high-level `grip()`/`release()` exists in `rustypot` either -- every example in
    `AmazingHand-main/PythonExample/` hand-composes one `write_goal_speed()` +
    `write_goal_position()` pair per motor, which this mirrors.
    """

    def __init__(
        self, serial_port="/dev/ttyACM0", baudrate=1_000_000, timeout=0.5, goal_speed=5
    ):
        from rustypot import Scs0009PyController

        self.goal_speed = goal_speed
        self._servo = Scs0009PyController(
            serial_port=serial_port, baudrate=baudrate, timeout=timeout
        )
        for motor_id in _MOTOR_IDS:
            self._servo.write_torque_enable(motor_id, 1)

    def apply(self, decoder_type, action):
        pose = HAND_ACTION_POSE[action]
        for i, motor_id in enumerate(_MOTOR_IDS):
            target = pose[i] + _MOTOR_OFFSETS_RAD[i]
            if _MOTOR_INVERT[i]:
                target = -target
            target = min(max(target, _SAFE_RANGE_RAD[0]), _SAFE_RANGE_RAD[1])
            self._servo.write_goal_speed(motor_id, self.goal_speed)
            self._servo.write_goal_position(motor_id, target)
            time.sleep(0.005)

    def disconnect(self):
        for motor_id in _MOTOR_IDS:
            self._servo.write_torque_enable(motor_id, 2)
