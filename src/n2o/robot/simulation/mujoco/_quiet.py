import contextlib
import os
import warnings


def prefer_x11_glfw():
    """Steer the `glfw` package (mujoco.viewer's window backend) towards its bundled
    X11 build instead of auto-selecting Wayland from `XDG_SESSION_TYPE` (see the pip
    `glfw` package's own `library._get_package_path_variant()`).

    GLFW's native Wayland backend draws window decorations (title bar, close
    button) itself via libdecor, which silently falls back to a bare, undecorated
    window wherever no libdecor plugin is installed -- X11 (including XWayland, on
    an otherwise-Wayland desktop) always gets decorated by the window manager
    instead, so it's the more reliable choice for a title bar to actually show up.

    Must run before the first `import glfw` anywhere in the process -- the `glfw`
    package picks and loads its shared library once, at that import, and never
    reloads it afterwards. Only kicks in when a real X11/XWayland display is
    reachable (`DISPLAY` set) and the caller hasn't already forced a variant.
    """
    if (
        os.environ.get("DISPLAY")
        and not os.environ.get("PYGLFW_LIBRARY_VARIANT")
        and not os.environ.get("PYGLFW_LIBRARY")
    ):
        os.environ["PYGLFW_LIBRARY_VARIANT"] = "x11"


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
