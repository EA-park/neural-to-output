import time
from pathlib import Path

import mujoco
import numpy as np

from ...controller import Controller

_ASSET_DIR = (
    Path(__file__).resolve().parents[2] / "simulation" / "assets" / "so101" / "mjcf"
)

ARM_JOINTS = [
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
]  # no "gripper" -- the 5-DOF real arm has no gripper motor (see so101_5dof.py)
IK_JOINTS = ["shoulder_pan", "shoulder_lift", "elbow_flex"]

UP_DOWN_POSE = {
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
}
"""Absolute per-joint degree targets for the bare `"up"`/`"down"` gesture actions --
hand-captured on this specific physical unit via `sandbox/capture_arm_poses.py`
(torque disabled, arm moved by hand to each pose, then read back via
`get_observation()`). A different physical unit needs recapturing these -- there's no
way to derive them from the CAD model the way `SIGN`/`ik_ranges` are."""

UP_DOWN_AXIS = "shoulder_pan"
"""Only this one joint actually moves for a bare `"up"`/`"down"` action -- the other
four stay at whatever they currently are. Calibration on this unit is suspected bad
(per-joint values in `UP_DOWN_POSE` may not be trustworthy), so driving only one known
joint limits the blast radius until calibration itself gets fixed -- go back to
driving the full `UP_DOWN_POSE` once it has."""

SIGN = dict.fromkeys(ARM_JOINTS, 1.0)
"""Per-joint sign correcting real-hardware degrees into the MJCF's own rotation
direction. Verify against your physical unit before trusting this: move one joint a
known small amount via `real_arm.send_action(...)`, check whether `gripperframe_xyz()`
moves the expected direction, and flip the sign for that joint here if not (see
`examples/09_real_so101_arm_control.ipynb`, section 2)."""


def real_deg_to_mj_rad(deg_by_joint):
    """Convert real-hardware degrees to the MJCF model's own radians."""
    return {joint: SIGN[joint] * np.radians(deg) for joint, deg in deg_by_joint.items()}


def mj_rad_to_real_deg(rad_by_joint):
    """Inverse of `real_deg_to_mj_rad()`."""
    return {joint: np.degrees(rad) / SIGN[joint] for joint, rad in rad_by_joint.items()}


def gripperframe_xyz(model, site_id, deg_by_joint):
    """Solve forward kinematics for the `gripperframe` site's xyz (meters) from the 5
    real joint angles (degrees) -- no physics stepping."""
    data = mujoco.MjData(model)
    for joint, rad in real_deg_to_mj_rad(deg_by_joint).items():
        joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint)
        data.qpos[model.jnt_qposadr[joint_id]] = rad
    mujoco.mj_forward(model, data)
    return data.site_xpos[site_id].copy()


class SO101ArmRealController(Controller):
    """Drives the real SO-101 5-DOF arm (see `so101_real/lerobot_robot_so101_5dof/`)
    from either a bare `"up"`/`"down"` gesture name (ramps just `UP_DOWN_AXIS` to the
    matching hand-captured value in `UP_DOWN_POSE` -- every other joint stays put, see
    `UP_DOWN_AXIS`) or an `(ActionType, {"dx": ..., "dy": ...})`
    Cartesian-relative command (solves a damped-least-squares IK step against the
    bundled SO-101 MJCF model, the same one `n2o.robot.simulation.so101` uses, to turn
    the offset into a joint-space target). Either way, the actual ramp toward the
    target is done entirely in joint-degree space (`_ramp_to_deg()`), not Cartesian --
    see `MAX_JOINT_SPEED_DEG_S`.

    Ported from `examples/09_real_so101_arm_control.ipynb`. The vendor SDK (`lerobot`)
    has no Cartesian-target call, so this composes low-level joint targets via IK
    instead, the same way `n2o.robot.simulation.so101.SO101ArmController` does for the
    sim -- but on top of *real* joint feedback (`real_arm.get_observation()`) and real
    motor writes (`real_arm.send_action()`).

    `MAX_JOINT_SPEED_DEG_S` is the actual safety mechanism, not
    `SO101Follower5DofConfig.max_relative_target` -- that config only clips relative to
    the *currently measured* position on each individual `send_action()` call, so a
    fixed step count can still move arbitrarily fast if the arm can't keep up with
    consecutive calls. Step count used to be derived from *Cartesian* distance
    (end-effector xyz), which meant a pose whose joints swing a lot but whose
    end-effector barely translates (e.g. `UP_DOWN_POSE`'s wrist/elbow-heavy poses) got
    too few steps -- each step's per-joint delta then exceeded `max_relative_target`
    and got silently clipped by lerobot itself, so the arm settled short of the
    intended pose instead of reaching it. Deriving steps from the largest per-joint
    degree delta instead keeps every joint's per-step delta safely under that clamp
    regardless of how Cartesian-far the move is.
    """

    MAX_JOINT_SPEED_DEG_S = (
        20.0  # hard cap -- do not raise without re-verifying on real hardware
    )
    STEP_DT_S = 0.05

    def __init__(
        self,
        real_arm=None,
        *,
        serial_port=None,
        x_range=(0.26, 0.34),
        y_range=(-0.10, 0.10),
        z=0.15,
        **connect_kwargs,
    ):
        if (real_arm is None) == (serial_port is None):
            raise ValueError(
                "SO101ArmRealController needs exactly one of real_arm or serial_port"
            )
        if serial_port is not None:
            from .connect import connect_so101

            real_arm = connect_so101(serial_port, **connect_kwargs)
        self.real_arm = real_arm
        self.x_range = x_range
        self.y_range = y_range
        self.z = z
        self.model = mujoco.MjModel.from_xml_path(str(_ASSET_DIR / "scene.xml"))
        self.site_id = mujoco.mj_name2id(
            self.model, mujoco.mjtObj.mjOBJ_SITE, "gripperframe"
        )
        self.ik_joint_ids = [
            mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, j)
            for j in IK_JOINTS
        ]
        self.ik_qpos_adr = [self.model.jnt_qposadr[jid] for jid in self.ik_joint_ids]
        self.ik_ranges = [self.model.jnt_range[jid] for jid in self.ik_joint_ids]

    def _current_deg(self):
        obs = self.real_arm.get_observation()
        return {joint: obs[f"{joint}.pos"] for joint in ARM_JOINTS}

    def _solve_ik(
        self, target_xyz, current_deg, n_iters=100, damping=0.05, step_size=0.5
    ):
        data = mujoco.MjData(
            self.model
        )  # scratch state -- wrist_flex/wrist_roll held at current value
        for joint, rad in real_deg_to_mj_rad(current_deg).items():
            joint_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, joint)
            data.qpos[self.model.jnt_qposadr[joint_id]] = rad

        for _ in range(n_iters):
            mujoco.mj_forward(self.model, data)
            error = target_xyz - data.site_xpos[self.site_id]
            if np.linalg.norm(error) < 1e-4:
                break
            jacp = np.zeros((3, self.model.nv))
            mujoco.mj_jacSite(self.model, data, jacp, None, self.site_id)
            j_sub = jacp[:, self.ik_qpos_adr]
            jjt = j_sub @ j_sub.T
            delta = j_sub.T @ np.linalg.solve(jjt + damping**2 * np.eye(3), error)
            for k, adr in enumerate(self.ik_qpos_adr):
                data.qpos[adr] += step_size * delta[k]
                lo, hi = self.ik_ranges[k]
                data.qpos[adr] = np.clip(data.qpos[adr], lo, hi)
        mujoco.mj_forward(self.model, data)
        final_error = float(np.linalg.norm(target_xyz - data.site_xpos[self.site_id]))
        joint_rad = {j: data.qpos[adr] for j, adr in zip(IK_JOINTS, self.ik_qpos_adr)}
        return joint_rad, final_error

    def _ramp_to_deg(self, target_deg, note=""):
        """Linearly ramp every joint in `target_deg` from its current position, purely
        in joint-degree space -- step count derived from the *largest single-joint*
        degree delta / `MAX_JOINT_SPEED_DEG_S`, so every joint's per-step delta stays
        safely under lerobot's own `max_relative_target` clamp regardless of how far
        any other joint (or the end-effector) moves. Shared by both a `_go_to()` IK
        result and a direct `UP_DOWN_POSE` target."""
        start_deg = self._current_deg()
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
            self.real_arm.send_action(action)
            time.sleep(self.STEP_DT_S)

        avg_speed = max_delta_deg / (n_steps * self.STEP_DT_S)
        print(
            f"SO-101 arm (real) -> {target_deg} ({note}{n_steps} steps, "
            f"avg speed={avg_speed:.1f}deg/s)"
        )

    def _go_to(self, target_xyz):
        start_deg = self._current_deg()
        joint_rad, ik_error = self._solve_ik(target_xyz, start_deg)
        target_deg = dict(start_deg)
        target_deg.update(
            mj_rad_to_real_deg(joint_rad)
        )  # wrist_flex/wrist_roll stay at current value
        self._ramp_to_deg(target_deg, note=f"IK residual={ik_error:.4f}m, ")

    def apply(self, decoder_type, command):
        if isinstance(command, str):
            target_deg = self._current_deg()
            target_deg[UP_DOWN_AXIS] = UP_DOWN_POSE[command][UP_DOWN_AXIS]
            self._ramp_to_deg(target_deg)
            return
        current_deg = self._current_deg()
        current_xyz = gripperframe_xyz(self.model, self.site_id, current_deg)
        _action_type, offset = command
        target_x = float(np.clip(current_xyz[0] + offset["dx"], *self.x_range))
        target_y = float(np.clip(current_xyz[1] + offset["dy"], *self.y_range))
        self._go_to(np.array([target_x, target_y, self.z]))
