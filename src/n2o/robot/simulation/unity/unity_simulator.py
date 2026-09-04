import json
import socket
import threading
import time

_DEFAULT_PORT = 9999


class UnitySimulator:
    """Visualizes `Part.goal()` targets in a Unity scene instead of MuJoCo -- a drop-in
    alternative to `Simulator` for `Robot.simulator`. `Robot.router()` only ever calls
    `drive(part, target)` on whatever object is assigned there (and `N2O.run()` only
    ever calls `launch_viewer()` on it once, right after building/assigning it), so
    this class matches that same shape instead of subclassing `Simulator` -- there is
    no shared base class to implement, only the calling convention to honor.

    There's no way to make `N2O.run(controller="simulation")` build one of these
    automatically without editing `n2o/__init__.py` (that call site hardcodes
    `n2o.robot.simulation.Simulator`) -- assign an instance onto `robot.simulator`
    yourself *before* calling `n2o.run(...)` instead; `run()` only auto-builds a
    `Simulator` when `robot.simulator is None`, so a pre-assigned `UnitySimulator`
    is used as-is:

        from n2o.robot.simulation.unity import UnitySimulator

        n2o.robot.simulator = UnitySimulator(parts=["arm"])
        n2o.run(controller="simulation")

    Needs no extra Python dependency (stdlib `socket`/`json` only). The Unity side is
    a separate process (Editor play mode, or a built player) listening on
    `host:port` for newline-delimited JSON messages -- one per `drive()` call, of the
    shape `{"part": "arm" | "hand", "target": <target value>}` (same `target` shapes
    `Simulator._arm_ctrl()`/`_hand_ctrl()` consume: a `{joint: degrees}` dict for
    `"arm"`, an 8-length pose list for `"hand"` -- see `AmazingHand.GESTURES`).
    `launch_viewer()` opens the connection and sends one handshake message,
    `{"parts": [...], "attach_hand_to_arm": bool}`, so the Unity side knows which
    part(s) to expect before any `drive()` message arrives. Building/wiring that
    Unity project itself is outside n2o's scope -- this class is only the client half
    of the protocol.
    """

    def __init__(
        self,
        parts=("arm",),
        *,
        attach_hand_to_arm=False,
        host="127.0.0.1",
        port=_DEFAULT_PORT,
        timeout=5.0,
        connect_retries=0,
        connect_retry_interval=1.0,
    ):
        parts = tuple(parts)
        if not parts or any(part not in ("arm", "hand") for part in parts):
            raise ValueError(f"parts must be a non-empty subset of arm/hand: {parts!r}")
        self._parts = parts
        self.attach_hand_to_arm = attach_hand_to_arm
        self._host = host
        self._port = port
        self._timeout = timeout
        self._connect_retries = connect_retries
        self._connect_retry_interval = connect_retry_interval
        self._sock = None
        self._send_lock = threading.Lock()

    def launch_viewer(self):
        """Open the TCP connection to the Unity process and send the handshake
        message -- mirrors `Simulator.launch_viewer()`'s role of opening the live
        view, except the window itself is Unity's own Game/Scene view, not anything
        this process draws. Safe to call more than once; an already-open connection
        is reused rather than reopened.

        Connecting to a Unity process is a real system boundary (a separate,
        possibly-not-yet-running process on a possibly-wrong host/port the caller
        typed in), unlike `Simulator.launch_viewer()`'s in-process MuJoCo window --
        a bare `ConnectionRefusedError`/`socket.timeout` traceback doesn't say what
        to check, so it's wrapped here into one message naming the address.

        `connect_retries` (default `0`, i.e. today's exact behavior -- fail on the
        first refusal) exists for any caller that starts or restarts the remote
        Unity process itself and needs to tolerate its boot window -- a
        freshly-started Unity player takes a few seconds to boot and reach the
        point its own listener actually binds the port, so connecting immediately
        would otherwise almost always hit `ConnectionRefusedError` even though
        nothing is actually wrong.

        A cached socket is only reused after confirming the peer hasn't already
        closed it (see `_peer_has_closed()`) -- without that check, stopping Unity
        (which sends a clean TCP FIN on a graceful Play stop) and then calling
        `drive()` again would silently reuse the dead socket: `sendall()` accepts
        the write into the local kernel buffer and returns without error before
        the OS has necessarily noticed the peer is gone, so the call looks like it
        succeeded even though nothing received it."""
        with self._send_lock:
            if self._sock is not None and self._peer_has_closed():
                self._sock.close()
                self._sock = None
            if self._sock is not None:
                return self._sock

        attempts = self._connect_retries + 1
        last_exc = None
        sock = None
        for attempt in range(attempts):
            try:
                sock = socket.create_connection((self._host, self._port), timeout=self._timeout)
                break
            except OSError as exc:
                last_exc = exc
                if attempt < attempts - 1:
                    time.sleep(self._connect_retry_interval)
        else:
            raise ConnectionError(
                f"failed to connect to a Unity simulator at "
                f"{self._host}:{self._port} -- is a Unity process listening there?"
            ) from last_exc

        with self._send_lock:
            self._sock = sock
        self._send({"parts": list(self._parts), "attach_hand_to_arm": self.attach_hand_to_arm})
        return self._sock

    def _peer_has_closed(self) -> bool:
        """True if the cached socket's peer already sent a TCP FIN (a graceful
        close -- e.g. Unity's own socket teardown on a clean Play stop), checked
        with a non-blocking `MSG_PEEK` so it neither consumes data nor blocks.
        Must be called with `self._send_lock` held -- toggling blocking mode on a
        socket another thread might be mid-`sendall()` on would be a real race.

        Doesn't catch an abrupt kill with no FIN at all -- that case still relies
        on the OS eventually delivering an RST, which isn't guaranteed to have
        happened yet by the time this runs. This closes the common half of the
        gap: a *clean* Unity stop, which is what pressing Play's stop button
        actually does."""
        self._sock.setblocking(False)
        try:
            return self._sock.recv(1, socket.MSG_PEEK) == b""
        except BlockingIOError:
            return False
        except OSError:
            return True
        finally:
            self._sock.setblocking(True)

    def drive(self, part, target):
        """Send `target` for `part` to Unity as one JSON message. `Robot.router()`
        dispatches "arm"/"hand" concurrently on separate threads (see `Robot.router`),
        so sends are serialized with `self._send_lock` the same way `Simulator.drive()`
        serializes access to its shared `mujoco.MjData` -- one TCP connection can't be
        written from two threads at once either."""
        if part not in self._parts:
            raise ValueError(f"{part!r} was not passed to parts={self._parts!r} at construction")
        self.launch_viewer()
        self._send({"part": part, "target": target})

    def close(self):
        """Close the connection to Unity, if one is open. Not called automatically --
        symmetrical with `Simulator`, which never closes its own viewer window either;
        the caller decides when a session is over."""
        if self._sock is not None:
            self._sock.close()
            self._sock = None

    def _send(self, message):
        payload = (json.dumps(message) + "\n").encode("utf-8")
        with self._send_lock:
            self._sock.sendall(payload)
