from pathlib import Path

from .viewer import enable_live_view

_ARM_ASSET = Path(__file__).parent / "assets" / "so101" / "mjcf" / "scene.xml"
_HAND_ASSET = (
    Path(__file__).parent / "assets" / "amazing_hand_right" / "mjcf" / "demo_scene.xml"
)


class Simulator:
    """Visualizes `Part.goal()` targets in MuJoCo -- what `Robot.router()` calls in
    `ControllerType.SIMULATION` mode when `robot.simulator` is set. Independent from
    the real `Part` classes (`SO101Arm`/`AmazingHand`): those only ever compute
    targets via `goal()`, this is what actually drives a physics model with them.

    `drive()` never touches a GL context (safe to call headless/in CI); a viewer
    window only opens if `launch_viewer()` is called explicitly.
    """

    def __init__(self):
        self._arm = None
        self._hand = None

    def drive(self, part, target):
        model = self._ensure(part)
        target_ctrl = self._arm_ctrl(model, target) if part == "arm" else self._hand_ctrl(target)
        model.drive_ctrl(target_ctrl)

    def launch_viewer(self, part):
        model = self._ensure(part)
        model.launch_viewer()
        enable_live_view(model)
        return model.viewer

    def render(self, part):
        return self._ensure(part).render()

    def _arm_ctrl(self, model, target_deg):
        import mujoco

        from ..arm.lerobot_robot_so101_5dof.solver import real_deg_to_mj_rad

        target_rad = real_deg_to_mj_rad(target_deg)
        target_ctrl = model.data.ctrl.copy()
        for joint, rad in target_rad.items():
            actuator_id = mujoco.mj_name2id(model.model, mujoco.mjtObj.mjOBJ_ACTUATOR, joint)
            target_ctrl[actuator_id] = rad
        return target_ctrl

    def _hand_ctrl(self, target_pose):
        import numpy as np

        return np.asarray(target_pose, dtype=float)

    def _ensure(self, part):
        if part == "arm":
            if self._arm is None:
                from ._mujoco_model import _MujocoModel

                self._arm = _MujocoModel(_ARM_ASSET)
            return self._arm
        elif part == "hand":
            if self._hand is None:
                from ._mujoco_model import _MujocoModel

                self._hand = _MujocoModel(_HAND_ASSET)
            return self._hand
        raise ValueError(f"unknown part: {part!r}")
