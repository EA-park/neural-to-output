import atexit
import time

_live_models = []
_atexit_registered = False


def enable_live_view(*models):
    """Register `wait_for_viewers()` as a single `atexit` hook (idempotent -- calling
    this multiple times, e.g. once per part, doesn't stack up multiple hooks) so the
    process blocks at interpreter shutdown -- not on every call -- until every live
    viewer window opened so far is closed.

    Called by `Simulator.launch_viewer()` right after opening one, so a caller never
    has to invoke this directly. Registering the wait at `atexit` rather than
    blocking here means repeated `drive()`/`launch_viewer()` calls keep animating the
    same live window(s) instead of pausing after every single call. Accumulating
    every model into one shared wait (instead of one `atexit` hook per model) means a
    single Ctrl+C closes every open window at once, rather than needing one interrupt
    per window.
    """
    global _atexit_registered
    for model in models:
        if model is not None and model.viewer is not None and model not in _live_models:
            _live_models.append(model)
    if not _atexit_registered:
        atexit.register(wait_for_viewers)
        _atexit_registered = True


def wait_for_viewers(*models):
    """Block until every live viewer window in `models` is closed -- or, called with
    no arguments (as the `atexit` hook does), every model registered so far via
    `enable_live_view()`. Entries that are `None` or never had `launch_viewer()`
    called are ignored.

    A `mujoco.viewer.launch_passive()` window runs in its own thread -- it vanishes
    the instant the process exits, so a caller needs something like this to keep the
    process alive while the window(s) stay open/interactive. Ctrl+C while waiting
    closes every remaining window and returns immediately, instead of leaving them
    dangling or raising `KeyboardInterrupt` out of an `atexit` handler.
    """
    targets = models if models else _live_models
    viewers = [m.viewer for m in targets if m is not None and m.viewer is not None]
    try:
        while any(viewer.is_running() for viewer in viewers):
            time.sleep(0.1)
    except KeyboardInterrupt:
        for viewer in viewers:
            if viewer.is_running():
                viewer.close()
