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
    from `(ActionType, {"dx": ..., "dy": ...})` Cartesian-relative commands: solves a
    damped-least-squares IK step against the bundled SO-101 MJCF model (the same one
    `n2o.robot.simulation.so101` uses), then ramps real servo positions toward the
    result, capped at `MAX_CARTESIAN_SPEED_M_S`.

    Ported from `examples/09_real_so101_arm_control.ipynb`. The vendor SDK (`lerobot`)
    has no Cartesian-target call, so this composes low-level joint targets via IK
    instead, the same way `n2o.robot.simulation.so101.SO101ArmController` does for the
    sim -- but on top of *real* joint feedback (`real_arm.get_observation()`) and real
    motor writes (`real_arm.send_action()`).

    `MAX_CARTESIAN_SPEED_M_S` is the actual safety mechanism, not
    `SO101Follower5DofConfig.max_relative_target` -- that config only clips relative to
    the *currently measured* position on each individual `send_action()` call, so a
    fixed step count can still move arbitrarily fast if the arm can't keep up with
    consecutive calls. The number of ramp steps is computed from distance /
    `MAX_CARTESIAN_SPEED_M_S` instead of being fixed, so average speed stays capped
    regardless of how far a single command asks to move.
    """

    MAX_CARTESIAN_SPEED_M_S = (
        0.01  # hard cap -- do not raise without re-verifying on real hardware
    )
    STEP_DT_S = 0.05

    def __init__(
        self, real_arm, *, x_range=(0.26, 0.34), y_range=(-0.10, 0.10), z=0.15
    ):
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

    def _go_to(self, target_xyz):
        start_deg = self._current_deg()
        current_xyz = gripperframe_xyz(self.model, self.site_id, start_deg)
        joint_rad, ik_error = self._solve_ik(target_xyz, start_deg)
        target_deg = dict(start_deg)
        target_deg.update(
            mj_rad_to_real_deg(joint_rad)
        )  # wrist_flex/wrist_roll stay at current value

        distance_m = float(np.linalg.norm(target_xyz - current_xyz))
        n_steps = max(
            1,
            int(np.ceil(distance_m / (self.MAX_CARTESIAN_SPEED_M_S * self.STEP_DT_S))),
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

        avg_speed = distance_m / (n_steps * self.STEP_DT_S)
        print(
            f"SO-101 arm (real) -> {target_deg} (IK residual={ik_error:.4f}m, "
            f"{n_steps} steps, avg speed={avg_speed * 100:.1f}cm/s)"
        )

    def apply(self, decoder_type, command):
        _action_type, offset = command
        current_deg = self._current_deg()
        current_xy = gripperframe_xyz(self.model, self.site_id, current_deg)[:2]
        target_x = float(np.clip(current_xy[0] + offset["dx"], *self.x_range))
        target_y = float(np.clip(current_xy[1] + offset["dy"], *self.y_range))
        self._go_to(np.array([target_x, target_y, self.z]))
