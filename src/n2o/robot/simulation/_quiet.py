import contextlib
import os
import warnings


def quiet_glfw_warnings():
    """Permanently silence `glfw.GLFWError` warnings (e.g. Wayland's "does not
    provide the window position") process-wide, once.

    `mujoco.viewer.launch_passive()` opens the actual window on a background thread,
    which can still be mid-setup after `launch_passive()` itself has already
    returned -- `quiet_stderr()`'s fd redirect (below) only covers code running
    synchronously inside its own `with` block, so a warning raised slightly later, on
    that background thread, would leak past it. Filtering the warning category
    instead has no such timing window -- `warnings.filters` is process-global, so it
    applies regardless of which thread raises it or when.
    """
    import glfw

    warnings.filterwarnings("ignore", category=glfw.GLFWError)


@contextlib.contextmanager
def quiet_stderr():
    """Temporarily redirect the OS-level stderr file descriptor to `/dev/null`.

    GLFW/libdecor (window creation) and MuJoCo's own GL context setup print their
    warnings (missing decoration plugins, Wayland quirks, benign GL context errors)
    directly to the C-level stderr file descriptor, not through Python's `warnings`
    module -- so nothing short of an fd-level redirect silences them. These are
    non-fatal (the window/renderer still works either way); this just keeps them out
    of the terminal during window/renderer creation specifically.
    """
    stderr_fd = 2
    saved_fd = os.dup(stderr_fd)
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull_fd, stderr_fd)
        yield
    finally:
        os.dup2(saved_fd, stderr_fd)
        os.close(devnull_fd)
        os.close(saved_fd)
