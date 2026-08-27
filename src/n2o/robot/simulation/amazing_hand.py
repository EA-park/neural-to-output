import time
from pathlib import Path

import mujoco
import numpy as np

from ..controller import Controller
from ..hand import RobotHand
from ._quiet import quiet_glfw_warnings, quiet_stderr

_ASSET_DIR = Path(__file__).parent / "assets" / "amazing_hand_right" / "mjcf"

HAND_ACTION_POSE = {
    "grip": np.array([1.4, 0.0] * 4),
    "release": np.zeros(8),
    # Ported qualitatively from AmazingHand-main/PythonExample/AmazingHand_Demo.py's
    # gesture functions (Move_Index/Middle/Ring/Thumb(Angle_1, Angle_2, Speed) real
    # servo-degree calls) -- not an exact biomechanical conversion. Each finger here
    # is a single [curl, 0.0] pair on the same 0 (open, matches "release") .. 1.4 rad
    # (fully closed, matches "grip") scale grip/release already use; motor2 stays 0.0
    # for every gesture, same as grip/release. [index, middle, ring, thumb] order,
    # matching HAND_ACTION_POSE's own existing 8-value layout.
    "open_hand": np.zeros(8),  # OpenHand() -- same pose as "release"
    "close_hand": np.array([1.4, 0.0] * 4),  # CloseHand() -- same pose as "grip"
    "clench_hand": np.array([0.3, 0.0, 0.0, 0.0, 1.0, 0.0, 1.2, 0.0]),  # ClenchHand()
    "victory": np.array(
        [0.0, 0.0, 0.0, 0.0, 1.4, 0.0, 1.4, 0.0]
    ),  # Victory() -- index+middle extended, ring+thumb closed
    "index_pointing": np.array(
        [0.0, 0.0, 1.4, 0.0, 1.4, 0.0, 1.4, 0.0]
    ),  # Index_Pointing()
    "nonono": np.array(
        [0.2, 0.0, 1.4, 0.0, 1.4, 0.0, 1.4, 0.0]
    ),  # Nonono() -- Index_Pointing() plus a wag; static mid-wag snapshot here
    "perfect": np.array(
        [1.3, 0.0, 0.0, 0.0, 0.4, 0.0, 1.1, 0.0]
    ),  # Perfect() -- index+thumb curled together, middle extended
}


class AmazingHandController(Controller):
    """AmazingHand's real SDK (rustypot) has no high-level `grip()`/`release()` calls,
    so this composes low-level joint targets instead -- see `examples/06_official_
    simulation_arm_and_hand.ipynb`, which this class ports."""

    def __init__(self, hand_sim):
        self.hand_sim = hand_sim

    def apply(self, decoder_type, action):
        target_ctrl = HAND_ACTION_POSE[action]
        self.hand_sim._drive_ctrl(target_ctrl)


class AmazingHandSim(RobotHand):
    """Drives the real AmazingHand MJCF model (MuJoCo -- see `assets/amazing_hand_
    right/NOTICE.md`) to visualize `move()` calls without real hardware. Ported from
    `examples/06_official_simulation_arm_and_hand.ipynb`.
    """

    def __init__(self):
        self.input_spec = {"action": "grip | release"}
        self.model = mujoco.MjModel.from_xml_path(str(_ASSET_DIR / "demo_scene.xml"))
        self.data = mujoco.MjData(self.model)
        self.renderer = None
        self.camera = None
        self.viewer = None
        self.controller = AmazingHandController(self)

    def launch_viewer(self):
        """Open a live, interactive MuJoCo viewer window -- see `SO101ArmSim.
        launch_viewer()`."""
        import mujoco.viewer

        quiet_glfw_warnings()
        with quiet_stderr():
            self.viewer = mujoco.viewer.launch_passive(self.model, self.data)
        return self.viewer

    def render(self):
        """Return the latest frame as an RGB array -- see `SO101ArmSim.render()`, same
        lazy renderer/GL-context construction (only on first call, never from
        `move()`/`_drive_ctrl()`)."""
        if self.renderer is None:
            with quiet_stderr():
                self.renderer = mujoco.Renderer(self.model, height=360, width=480)
            self.camera = mujoco.MjvCamera()
            mujoco.mjv_defaultCamera(self.camera)
            self.camera.distance = 0.35
            self.camera.azimuth = 120
            self.camera.elevation = -20
            self.camera.lookat = np.array([0.0, 0.0, 0.05])
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
