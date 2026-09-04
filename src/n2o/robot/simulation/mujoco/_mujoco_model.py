import time

from ._quiet import prefer_x11_glfw, quiet_glfw_warnings, quiet_stderr

# Must run at import time, here, rather than inside `launch_viewer()` below --
# a bare `import mujoco` (e.g. `_MujocoModel.__init__()`'s own, run the moment a
# `Simulator` is constructed, well before any viewer is launched) already imports
# `glfw` as a side effect, and `prefer_x11_glfw()` only has an effect before that
# first `import glfw` anywhere in the process. This module is the first thing
# `n2o.robot.simulation` imports (`__init__.py` -> `simulator.py` -> here), so
# running it at this module's import time is as early as it can run.
prefer_x11_glfw()

VIEWER_STEP_DT_S = (
    1 / 60
)  # paces a live viewer to ~60fps-watchable, not physical real time


class ViewerClosed(RuntimeError):
    """Raised by `drive_ctrl()` once the live viewer window it was pacing itself
    against has been closed (OS close button, Q/Escape, or `self.viewer.close()`)
    -- a plain `RuntimeError` subclass, so it needs no special handling to reach a
    caller: `Robot.router()`'s own dispatch already re-raises whatever a part's
    `move()`/`Simulator.drive()` raised, `N2O.run()`'s cycle loop doesn't catch
    anything but `KeyboardInterrupt` so it propagates straight out, and
    `apps/console.py`'s `RunWorker` already turns any such exception into an
    "실행 오류" dialog -- this message is what ends up as that dialog's summary
    line."""


class _MujocoModel:
    """Owns one MJCF model/data pair plus its (lazy) viewer/renderer -- the part-
    agnostic pieces that used to be duplicated between the removed `SO101ArmSim` and
    `AmazingHandSim`. `Simulator` (one per `Robot`) owns exactly one of these --
    shared by every part it drives, so they animate in a single window/physics
    world instead of one each (see `Simulator._build_model()`).

    Takes an already-built `mujoco.MjModel` rather than an XML path, so a caller can
    hand it either a plain `mujoco.MjModel.from_xml_path(...)` (one part alone) or a
    `mujoco.MjSpec.compile()` result (multiple parts merged into one spec first).
    """

    def __init__(self, model):
        import mujoco

        self.model = model
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
            # GLFW's Wayland backend draws window decorations (title bar, close
            # button) itself via libdecor, which silently falls back to a bare,
            # undecorated window on a system with no libdecor plugin installed --
            # X11 (including XWayland, on a Wayland session) always decorates
            # through the window manager instead, so it's the more reliable choice
            # whenever this glfw build actually supports it. `init_hint()` only has
            # an effect before the process's first `glfw.init()` call, and
            # `launch_passive()` below makes that call itself, on its own
            # background thread -- calling `glfw.init()` ourselves here, first, on
            # this (main) thread pins the platform decision to our hint before that
            # thread gets a chance to pick its own default (verified empirically: on
            # a Wayland session, leaving `glfw.init()` for `launch_passive()`'s
            # thread to call still produced an undecorated window despite the same
            # `init_hint()` call, while calling it here first fixed it).
            if glfw.platform_supported(glfw.PLATFORM_X11):
                glfw.init_hint(glfw.PLATFORM, glfw.PLATFORM_X11)
            glfw.window_hint(glfw.DECORATED, glfw.TRUE)
            glfw.init()
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
        headless.

        Raises `ViewerClosed` the moment a live viewer's window has been closed,
        instead of continuing to step/pace physics nobody can see anymore -- a
        caller (e.g. `N2O.run()`'s cycle loop, via `Robot.router()`) sees that as
        any other exception mid-run and stops, rather than the pipeline silently
        running the rest of its cycles headless with no way to tell. Checked once
        per step (not just once up front) so a window closed mid-ramp is caught
        within one physics step, not only between separate `drive_ctrl()` calls."""
        import mujoco

        start_ctrl = self.data.ctrl.copy()
        for step in range(n_steps):
            if self.viewer is not None and not self.viewer.is_running():
                raise ViewerClosed(
                    "the live viewer window was closed -- stopping the simulation"
                )
            alpha = (step + 1) / n_steps
            self.data.ctrl[:] = start_ctrl + alpha * (target_ctrl - start_ctrl)
            mujoco.mj_step(self.model, self.data)
            if self.viewer is not None:
                self.viewer.sync()
                time.sleep(VIEWER_STEP_DT_S)
