import time
from pathlib import Path

import mujoco
import numpy as np

from ..arm import RobotArm
from ..controller import Controller
from ._quiet import quiet_glfw_warnings, quiet_stderr

_ASSET_DIR = Path(__file__).parent / "assets" / "so101" / "mjcf"

ARM_JOINTS = [
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
]

ARM_ACTION_POSE = {
    "up": dict(zip(ARM_JOINTS, [0.0, 0.6, -0.3, 0.0, 0.0, 0.0])),
    "down": dict(zip(ARM_JOINTS, [0.0, -0.6, 0.3, 0.0, 0.0, 0.0])),
}


class SO101ArmController(Controller):
    """The SO-101 vendor SDK (lerobot) has no high-level `"up"`/`"down"` calls, so this
    composes low-level joint targets instead -- see `examples/06_official_simulation_
    arm_and_hand.ipynb`, which this class ports."""

    def __init__(self, arm_sim):
        self.arm_sim = arm_sim

    def apply(self, decoder_type, action):
        pose = ARM_ACTION_POSE[action]
        target_ctrl = np.array([pose[joint] for joint in ARM_JOINTS])
        self.arm_sim._drive_ctrl(target_ctrl)


class SO101ArmSim(RobotArm):
    """Drives the real SO-101 MJCF model (MuJoCo, official TheRobotStudio/SO-ARM100
    source -- see `assets/so101/NOTICE.md`) to visualize `move()` calls without real
    hardware. Ported from `examples/06_official_simulation_arm_and_hand.ipynb`.
    """

    def __init__(self):
        self.input_spec = {"action": "up | down"}
        self.model = mujoco.MjModel.from_xml_path(str(_ASSET_DIR / "scene.xml"))
        self.data = mujoco.MjData(self.model)
        self.renderer = None
        self.camera = None
        self.viewer = None
        self.controller = SO101ArmController(self)

    def launch_viewer(self):
        """Open a live, interactive MuJoCo viewer window -- once attached, `move()`
        calls animate in it in (roughly) real time instead of just fast-forwarding
        physics with nothing to look at. Stays open until you close the window or call
        `self.viewer.close()`."""
        import mujoco.viewer

        quiet_glfw_warnings()
        with quiet_stderr():
            self.viewer = mujoco.viewer.launch_passive(self.model, self.data)
        return self.viewer

    def render(self):
        """Return the latest frame as an RGB array, for a caller that wants to look at
        it -- unlike the source notebook, nothing here auto-displays a frame/animation
        on every `move()` (that's Jupyter-only presentation glue, wrong for a general
        library method). The renderer/GL context is built lazily, here, on first call
        -- `move()`/`_drive_ctrl()` never touch it, so driving physics works in a
        headless environment with no OpenGL context at all."""
        if self.renderer is None:
            with quiet_stderr():
                self.renderer = mujoco.Renderer(self.model, height=360, width=480)
            self.camera = mujoco.MjvCamera()
            mujoco.mjv_defaultCamera(self.camera)
            self.camera.distance = 0.85
            self.camera.azimuth = 140
            self.camera.elevation = -25
            self.camera.lookat = np.array([0.1, 0.0, 0.08])
        self.renderer.update_scene(self.data, camera=self.camera)
        return self.renderer.render().copy()

    VIEWER_STEP_DT_S = (
        1 / 60
    )  # paces a live viewer to ~60fps-watchable, not physical real time

    def _drive_ctrl(self, target_ctrl):
        start_ctrl = self.data.ctrl.copy()
        n_steps = 60
        for step in range(n_steps):
            alpha = (step + 1) / n_steps
            self.data.ctrl[:] = start_ctrl + alpha * (target_ctrl - start_ctrl)
            mujoco.mj_step(self.model, self.data)
            if self.viewer is not None:
                self.viewer.sync()
                time.sleep(self.VIEWER_STEP_DT_S)

    def move(self, decoder_type, command):
        self.controller.apply(decoder_type, command)
