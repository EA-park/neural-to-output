import json

import pytest

from n2o.robot.simulation.unity.unity_simulator import UnitySimulator


class _FakeSocket:
    """Stands in for a connected TCP socket -- records every `sendall()` payload,
    no real network I/O. `peer_has_sent_fin` simulates a peer that already closed
    its end (e.g. Unity's Play stopping cleanly) -- flip it to `True` to make
    `recv(..., MSG_PEEK)` behave like a real closed socket does (returns `b""`)."""

    def __init__(self):
        self.sent = []
        self.closed = False
        self.peer_has_sent_fin = False

    def sendall(self, payload):
        self.sent.append(json.loads(payload.decode("utf-8")))

    def close(self):
        self.closed = True

    def setblocking(self, flag):
        pass

    def recv(self, bufsize, flags=0):
        if self.peer_has_sent_fin:
            return b""
        raise BlockingIOError()


@pytest.fixture
def fake_connection(monkeypatch):
    sockets = []

    def _fake_create_connection(address, timeout=None):
        sock = _FakeSocket()
        sockets.append(sock)
        return sock

    monkeypatch.setattr(
        "n2o.robot.simulation.unity.unity_simulator.socket.create_connection",
        _fake_create_connection,
    )
    return sockets


def test_rejects_unknown_parts():
    with pytest.raises(ValueError, match="parts must be a non-empty subset"):
        UnitySimulator(parts=["tentacle"])


def test_launch_viewer_sends_one_handshake_message(fake_connection):
    sim = UnitySimulator(parts=["arm", "hand"], attach_hand_to_arm=True)

    sim.launch_viewer()
    sim.launch_viewer()

    assert len(fake_connection) == 1
    assert fake_connection[0].sent == [
        {"parts": ["arm", "hand"], "attach_hand_to_arm": True}
    ]


def test_launch_viewer_reconnects_after_peer_closes_gracefully(fake_connection):
    """Regression test: reusing a cached socket whose peer already sent a FIN
    (e.g. Unity's Play stopping cleanly) must not silently look like success --
    `launch_viewer()` should detect the closed peer and open a fresh connection
    instead of handing back the dead one."""
    sim = UnitySimulator(parts=["arm"])
    sim.launch_viewer()
    assert len(fake_connection) == 1
    fake_connection[0].peer_has_sent_fin = True

    sim.launch_viewer()

    assert len(fake_connection) == 2
    assert fake_connection[0].closed
    assert not fake_connection[1].closed


def test_drive_sends_part_and_target(fake_connection):
    sim = UnitySimulator(parts=["arm"])

    sim.drive("arm", {"shoulder_pan": 12.0})

    sock = fake_connection[0]
    assert sock.sent[-1] == {"part": "arm", "target": {"shoulder_pan": 12.0}}


def test_drive_rejects_a_part_not_passed_at_construction(fake_connection):
    sim = UnitySimulator(parts=["arm"])

    with pytest.raises(ValueError, match="was not passed to parts"):
        sim.drive("hand", [0.0] * 8)


def test_close_closes_the_socket(fake_connection):
    sim = UnitySimulator(parts=["arm"])
    sim.launch_viewer()

    sim.close()

    assert fake_connection[0].closed


def test_launch_viewer_wraps_a_refused_connection(monkeypatch):
    def _refuse(address, timeout=None):
        raise ConnectionRefusedError("[Errno 111] Connection refused")

    monkeypatch.setattr(
        "n2o.robot.simulation.unity.unity_simulator.socket.create_connection", _refuse
    )
    sim = UnitySimulator(parts=["arm"], host="127.0.0.1", port=9700)

    with pytest.raises(ConnectionError, match="127.0.0.1:9700"):
        sim.launch_viewer()


def test_launch_viewer_retries_before_giving_up(monkeypatch, fake_connection):
    """A freshly launched Unity process (Editor entering Play, or a Standalone
    Player booting) takes a few seconds to actually bind its listening port --
    connect_retries lets a caller tolerate that boot window instead of failing on
    the very first refusal."""
    attempts = []

    def _fake_create_connection(address, timeout=None):
        attempts.append(1)
        if len(attempts) < 3:
            raise ConnectionRefusedError("[Errno 111] Connection refused")
        sock = _FakeSocket()
        fake_connection.append(sock)
        return sock

    monkeypatch.setattr(
        "n2o.robot.simulation.unity.unity_simulator.socket.create_connection",
        _fake_create_connection,
    )
    monkeypatch.setattr("n2o.robot.simulation.unity.unity_simulator.time.sleep", lambda s: None)

    sim = UnitySimulator(
        parts=["arm"], host="127.0.0.1", port=9700, connect_retries=5, connect_retry_interval=0.01
    )

    sim.launch_viewer()  # must not raise

    assert len(attempts) == 3
    assert len(fake_connection) == 1


def test_launch_viewer_raises_after_exhausting_retries(monkeypatch):
    calls = []

    def _always_refuse(address, timeout=None):
        calls.append(1)
        raise ConnectionRefusedError("[Errno 111] Connection refused")

    monkeypatch.setattr(
        "n2o.robot.simulation.unity.unity_simulator.socket.create_connection", _always_refuse
    )
    monkeypatch.setattr("n2o.robot.simulation.unity.unity_simulator.time.sleep", lambda s: None)

    sim = UnitySimulator(
        parts=["arm"], host="127.0.0.1", port=9700, connect_retries=2, connect_retry_interval=0.01
    )

    with pytest.raises(ConnectionError, match="127.0.0.1:9700"):
        sim.launch_viewer()

    assert len(calls) == 3  # initial attempt + 2 retries
