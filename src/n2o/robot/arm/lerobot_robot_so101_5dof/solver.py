from pathlib import Path

import mujoco
import numpy as np

from ...solver import Solver

_ASSET_DIR = (
    Path(__file__).resolve().parents[2] / "simulation" / "assets" / "so101" / "mjcf"
)

ARM_JOINTS = [
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
]  # no "gripper" -- the 5-DOF real arm has no gripper motor
IK_JOINTS = ["shoulder_pan", "shoulder_lift", "elbow_flex"]

SIGN = dict.fromkeys(ARM_JOINTS, 1.0)
"""Per-joint sign correcting real-hardware degrees into the MJCF's own rotation
direction. Verify against your physical unit before trusting this: move one joint a
known small amount via `real_arm.send_action(...)`, check whether `gripperframe_xyz()`
moves the expected direction, and flip the sign for that joint here if not."""


def real_deg_to_mj_rad(deg_by_joint):
    """Convert real-hardware degrees to the MJCF model's own radians."""
    return {joint: SIGN[joint] * np.radians(deg) for joint, deg in deg_by_joint.items()}


def mj_rad_to_real_deg(rad_by_joint):
    """Inverse of `real_deg_to_mj_rad()`."""
    return {joint: np.degrees(rad) / SIGN[joint] for joint, rad in rad_by_joint.items()}


class SO101IKSolver(Solver):
    """Pure IK computation for the SO-101 arm -- no hardware/sim I/O, takes the
    caller's own current joint-degree reading and hands back a joint-degree target.
    Solves a damped-least-squares IK step against the bundled SO-101 MJCF model (the
    same one `n2o.robot.simulation` uses/used) to turn a Cartesian offset into a
    joint-space target.

    Lives inside `lerobot_robot_so101_5dof/` (otherwise a verbatim-vendored package,
    see CLAUDE.md) rather than `robot/arm/` itself or the shared `robot/solver/` --
    an intentional exception, since this solver is specific to the SO-101 5-DOF
    driver this vendored package wraps, not a general SO-101-arm-shaped thing.
    `robot/solver/` keeps only the shared `Solver` ABC.

    Ported from the removed `SO101ArmRealController` (`robot/arm/so101_real/
    controller.py`) -- that class mixed this computation together with real hardware
    I/O (`_current_deg()`/`_ramp_to_deg()`); those stay on `SO101Arm` itself
    (`robot/arm/so101.py`), which is the one that owns the real servo connection.

    Not wired into `SO101Arm.move()`/`goal()` yet -- `Command.translate()` doesn't
    currently emit `(ActionType, {"dx", "dy"})` commands for any shipped `Command`
    (only bare gesture names). See `ROADMAP.md`.
    """

    def __init__(self, x_range=(0.26, 0.34), y_range=(-0.10, 0.10), z=0.15):
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

    def gripperframe_xyz(self, deg_by_joint):
        """Forward kinematics: the `gripperframe` site's xyz (meters) from the 5 real
        joint angles (degrees) -- no physics stepping."""
        data = mujoco.MjData(self.model)
        for joint, rad in real_deg_to_mj_rad(deg_by_joint).items():
            joint_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, joint)
            data.qpos[self.model.jnt_qposadr[joint_id]] = rad
        mujoco.mj_forward(self.model, data)
        return data.site_xpos[self.site_id].copy()

    def solve(self, current_deg, dx, dy, n_iters=100, damping=0.05, step_size=0.5):
        """Given the arm's current joint-degree state and a Cartesian offset
        (`dx`/`dy`, meters, clamped to `x_range`/`y_range`/`z`), return
        `(target_deg, ik_error)` -- the full 5-joint degree target (`wrist_flex`/
        `wrist_roll` stay at `current_deg`'s own value, only `IK_JOINTS` change) and
        the residual IK error (meters)."""
        current_xyz = self.gripperframe_xyz(current_deg)
        target_x = float(np.clip(current_xyz[0] + dx, *self.x_range))
        target_y = float(np.clip(current_xyz[1] + dy, *self.y_range))
        target_xyz = np.array([target_x, target_y, self.z])

        joint_rad, ik_error = self._solve_ik(
            target_xyz,
            current_deg,
            n_iters=n_iters,
            damping=damping,
            step_size=step_size,
        )
        target_deg = dict(current_deg)
        target_deg.update(mj_rad_to_real_deg(joint_rad))
        return target_deg, ik_error

    def _solve_ik(self, target_xyz, current_deg, n_iters, damping, step_size):
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
