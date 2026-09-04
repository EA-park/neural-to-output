import time

from ...part import Part

ARM_JOINTS = [
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
]  # no "gripper" -- the 5-DOF real arm has no gripper motor

GESTURES = {
    "up": {
        "shoulder_pan": 87.60,
        "shoulder_lift": -23.25,
        "elbow_flex": 128.79,
        "wrist_flex": -85.58,
        "wrist_roll": 38.11,
    },
    "down": {
        "shoulder_pan": -0.04,
        "shoulder_lift": -23.25,
        "elbow_flex": 128.79,
        "wrist_flex": -85.58,
        "wrist_roll": 38.11,
    },
    "up2": {
        "shoulder_pan": 87.60,
        "shoulder_lift": -23.25,
        "elbow_flex": 128.79,
        "wrist_flex": -85.58,
        "wrist_roll": 38.11,
    },
    "down2": {
        "shoulder_pan": -0.04,
        "shoulder_lift": -23.25,
        "elbow_flex": 128.79,
        "wrist_flex": -85.58,
        "wrist_roll": 38.11,
    },
    "up3": {
        "shoulder_pan": 87.60,
        "shoulder_lift": -23.25,
        "elbow_flex": 128.79,
        "wrist_flex": -85.58,
        "wrist_roll": 38.11,
    },
    "down3": {
        "shoulder_pan": -0.04,
        "shoulder_lift": -23.25,
        "elbow_flex": 128.79,
        "wrist_flex": -85.58,
        "wrist_roll": 38.11,
    },
}
"""Absolute per-joint degree targets, hand-captured on this specific physical unit
(torque disabled, arm moved by hand to each pose, then read back via
`get_observation()`). A different physical unit needs recapturing these."""

_UP_DOWN_AXIS = "shoulder_pan"
"""Only this one joint actually moves for a `"up"`/`"down"` gesture -- the other four
stay at whatever they currently are. Calibration on this unit is suspected bad (the
other per-joint values in `GESTURES` may not be trustworthy), so driving only one
known joint limits the blast radius until calibration itself gets fixed."""


class SO101Arm(Part):
    """Owns the real SO-101 5-DOF arm connection directly (see
    `lerobot_robot_so101_5dof/`) -- `goal()` is a pure lookup (no I/O), `move()`
    actually drives the hardware. Connection is lazy (first `move()` call).

    Cartesian-relative (`dx`/`dy`) IK control isn't wired in here yet -- the pure IK
    computation itself lives in `lerobot_robot_so101_5dof.solver.SO101IKSolver`
    (`solve(current_deg, dx, dy) -> (target_deg, ik_error)`), but no `Command` emits
    `(ActionType, {"dx", "dy"})` commands yet and `move()`/`goal()` don't call into
    it. See `ROADMAP.md`.
    """

    MAX_JOINT_SPEED_DEG_S = (
        20.0  # hard cap -- do not raise without re-verifying on real hardware
    )
    STEP_DT_S = 0.05

    def __init__(self, port: str = "", *, id: str = "n2o_so101_5dof", **connect_kwargs):
        self.port = port
        self.id = id
        self._connect_kwargs = connect_kwargs
        self._real_arm = None

    def goal(self, cmd):
        try:
            return dict(GESTURES[cmd])
        except KeyError:
            raise ValueError(f"unknown SO101Arm gesture: {cmd!r}") from None

    def move(self, cmd):
        target = self.goal(cmd)
        self._ensure_connected()
        start_deg = self._current_deg()
        target_deg = dict(start_deg)
        target_deg[_UP_DOWN_AXIS] = target[_UP_DOWN_AXIS]
        self._ramp_to_deg(start_deg, target_deg)

    def _current_deg(self):
        obs = self._real_arm.get_observation()
        return {joint: obs[f"{joint}.pos"] for joint in ARM_JOINTS}

    def _ramp_to_deg(self, start_deg, target_deg, note=""):
        """Linearly ramp every joint in `target_deg` from `start_deg`, purely in
        joint-degree space -- step count derived from the *largest single-joint*
        degree delta / `MAX_JOINT_SPEED_DEG_S`, so every joint's per-step delta stays
        safely under lerobot's own `max_relative_target` clamp regardless of how far
        any other joint moves."""
        import numpy as np

        max_delta_deg = max(abs(target_deg[j] - start_deg[j]) for j in ARM_JOINTS)
        n_steps = max(
            1,
            int(np.ceil(max_delta_deg / (self.MAX_JOINT_SPEED_DEG_S * self.STEP_DT_S))),
        )

        for step in range(n_steps):
            alpha = (step + 1) / n_steps
            action = {
                f"{joint}.pos": start_deg[joint]
                + alpha * (target_deg[joint] - start_deg[joint])
                for joint in ARM_JOINTS
            }
            self._real_arm.send_action(action)
            time.sleep(self.STEP_DT_S)

        avg_speed = max_delta_deg / (n_steps * self.STEP_DT_S)
        print(
            f"SO-101 arm (real) -> {target_deg} ({note}{n_steps} steps, "
            f"avg speed={avg_speed:.1f}deg/s)"
        )

    def _ensure_connected(self):
        if self._real_arm is None:
            from .lerobot_robot_so101_5dof import (
                SO101Follower5Dof,
                SO101Follower5DofConfig,
            )

            kwargs = {
                "max_relative_target": 2.0,
                "disable_torque_on_disconnect": True,
                **self._connect_kwargs,
            }
            config = SO101Follower5DofConfig(port=self.port, id=self.id, **kwargs)
            arm = SO101Follower5Dof(config)
            if not arm.calibration_fpath.is_file():
                raise RuntimeError(
                    f"no calibration file at {arm.calibration_fpath} -- "
                    "so101_follower_5dof isn't a registered lerobot robot type, so "
                    "the plain `lerobot-calibrate` CLI can't build it; instead, in a "
                    "real terminal run: `from n2o.robot.arm.so101.lerobot_robot_so101_5dof "
                    "import SO101Follower5Dof, SO101Follower5DofConfig; arm = "
                    "SO101Follower5Dof(SO101Follower5DofConfig(port="
                    f"{self.port!r}, id={self.id!r})); arm.connect(calibrate=False); "
                    "arm.calibrate(); arm.disconnect()`, then call move() again"
                )
            arm.connect(calibrate=False)
            self._real_arm = arm
