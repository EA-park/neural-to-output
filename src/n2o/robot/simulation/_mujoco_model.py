import time

from ._quiet import quiet_glfw_warnings, quiet_stderr

VIEWER_STEP_DT_S = (
    1 / 60
)  # paces a live viewer to ~60fps-watchable, not physical real time


class _MujocoModel:
    """Owns one MJCF model/data pair plus its (lazy) viewer/renderer -- the part-
    agnostic pieces that used to be duplicated between the removed `SO101ArmSim` and
    `AmazingHandSim`. `Simulator` (one per `Robot`) owns one of these per part it
    actually drives.
    """

    def __init__(self, xml_path):
        import mujoco

        self.model = mujoco.MjModel.from_xml_path(str(xml_path))
        self.data = mujoco.MjData(self.model)
        self.renderer = None
        self.camera = None
        self.viewer = None

    def launch_viewer(self):
        """Open a live, interactive MuJoCo viewer window -- once attached,
        `drive_ctrl()` calls animate in it in (roughly) real time instead of just
        fast-forwarding physics with nothing to look at. Stays open until the window
        is closed (via its own OS close button, pressing Q/Escape while it has focus,
        or `self.viewer.close()`)."""
        import glfw
        import mujoco.viewer

        def _quit_on_key(keycode):
            if keycode in (glfw.KEY_Q, glfw.KEY_ESCAPE):
                self.viewer.close()

        quiet_glfw_warnings()
        with quiet_stderr():
            self.viewer = mujoco.viewer.launch_passive(
                self.model, self.data, key_callback=_quit_on_key
            )
        return self.viewer

    def render(
        self, *, distance=0.5, azimuth=140, elevation=-25, lookat=(0.0, 0.0, 0.08)
    ):
        """Return the latest frame as an RGB array. The renderer/GL context is built
        lazily, here, on first call -- `drive_ctrl()` never touches it, so driving
        physics works in a headless environment with no OpenGL context at all."""
        import mujoco
        import numpy as np

        if self.renderer is None:
            with quiet_stderr():
                self.renderer = mujoco.Renderer(self.model, height=360, width=480)
            self.camera = mujoco.MjvCamera()
            mujoco.mjv_defaultCamera(self.camera)
            self.camera.distance = distance
            self.camera.azimuth = azimuth
            self.camera.elevation = elevation
            self.camera.lookat = np.array(lookat)
        self.renderer.update_scene(self.data, camera=self.camera)
        return self.renderer.render().copy()

    def drive_ctrl(self, target_ctrl, n_steps=60):
        """Linearly ramp `self.data.ctrl` from its current value to `target_ctrl`
        over `n_steps` physics steps -- no GL/viewer dependency, safe to call
        headless."""
        import mujoco

        start_ctrl = self.data.ctrl.copy()
        for step in range(n_steps):
            alpha = (step + 1) / n_steps
            self.data.ctrl[:] = start_ctrl + alpha * (target_ctrl - start_ctrl)
            mujoco.mj_step(self.model, self.data)
            if self.viewer is not None:
                self.viewer.sync()
                time.sleep(VIEWER_STEP_DT_S)
