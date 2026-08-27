import pytest

pytest.importorskip("mujoco")

from n2o.robot.simulation import wait_for_viewers


class _FakeSim:
    def __init__(self, viewer=None):
        self.viewer = viewer


class _FakeViewer:
    def __init__(self, running_for_calls):
        self._remaining = running_for_calls
        self.calls = 0

    def is_running(self):
        self.calls += 1
        if self._remaining <= 0:
            return False
        self._remaining -= 1
        return True


def test_returns_immediately_with_no_sims():
    wait_for_viewers()  # must not hang or raise


def test_ignores_none_and_viewer_less_sims():
    wait_for_viewers(None, _FakeSim(viewer=None))  # must not hang or raise


def test_blocks_until_every_viewer_stops_running(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _seconds: None)
    viewer_a = _FakeViewer(running_for_calls=2)
    viewer_b = _FakeViewer(running_for_calls=0)

    wait_for_viewers(_FakeSim(viewer_a), None, _FakeSim(viewer_b))

    assert viewer_a.calls >= 3  # 2 "still running" + 1 "stopped" check
    assert not viewer_a.is_running()
