import atexit
import time


def enable_live_view(*sims):
    """Launch a live viewer for each of `sims` that doesn't already have one
    (`sim.viewer is None`), and register an `atexit` hook so the process blocks at
    interpreter shutdown -- not on every call -- until that viewer is closed.

    This is what `N2O.run(simulation=True)` calls automatically the moment it builds
    a simulated arm/hand, so a caller never has to invoke this directly -- `n2o.run
    (simulation=True)` alone is enough to see it move live. Registering the wait at
    `atexit` rather than blocking here means a loop calling `run(simulation=True)`
    many times keeps animating the same live window instead of pausing after every
    single call.
    """
    for sim in sims:
        if sim is not None and sim.viewer is None:
            sim.launch_viewer()
            atexit.register(wait_for_viewers, sim)


def wait_for_viewers(*sims):
    """Block until every live viewer window opened via `launch_viewer()` on `sims`
    has been closed. Entries that are `None` (e.g. `n2o.simulated_hand` when only the
    arm was simulated) or never had `launch_viewer()` called are ignored.

    A `mujoco.viewer.launch_passive()` window runs in its own thread -- it vanishes
    the instant the process exits, so a caller needs something like this after
    `N2O.run(simulation=True)` to keep the process alive while the window(s) stay
    open/interactive.
    """
    viewers = [sim.viewer for sim in sims if sim is not None and sim.viewer is not None]
    while any(viewer.is_running() for viewer in viewers):
        time.sleep(0.1)
