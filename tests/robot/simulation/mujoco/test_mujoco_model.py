import pytest

pytest.importorskip("mujoco")

import numpy as np

from n2o.robot.simulation.mujoco import ViewerClosed
from n2o.robot.simulation.mujoco._mujoco_model import _MujocoModel


class _FakeViewer:
    def __init__(self, running):
        self._running = running

    def is_running(self):
        return self._running

    def sync(self):
        pass


def _model_with_arm():
    import mujoco

    xml = """
    <mujoco>
      <worldbody>
        <body>
          <joint name="j" type="hinge" axis="0 0 1"/>
          <geom type="sphere" size="0.01"/>
        </body>
      </worldbody>
      <actuator>
        <position name="a" joint="j"/>
      </actuator>
    </mujoco>
    """
    return _MujocoModel(mujoco.MjModel.from_xml_string(xml))


def test_drive_ctrl_runs_headless_with_no_viewer():
    model = _model_with_arm()

    model.drive_ctrl(np.array([0.5]), n_steps=3)  # must not raise

    assert model.data.ctrl[0] == pytest.approx(0.5)


def test_drive_ctrl_completes_normally_while_the_viewer_is_running():
    model = _model_with_arm()
    model.viewer = _FakeViewer(running=True)

    model.drive_ctrl(np.array([0.5]), n_steps=3)  # must not raise

    assert model.data.ctrl[0] == pytest.approx(0.5)


def test_drive_ctrl_raises_viewer_closed_once_the_viewer_stops_running():
    model = _model_with_arm()
    model.viewer = _FakeViewer(running=False)

    with pytest.raises(ViewerClosed, match="live viewer window was closed"):
        model.drive_ctrl(np.array([0.5]), n_steps=3)


def test_drive_ctrl_stops_mid_ramp_once_the_viewer_closes():
    """A viewer that stops running partway through the ramp (not just before the
    first step) is caught within that same `drive_ctrl()` call, not only on the
    next one -- `data.ctrl` ends up only partially advanced, not silently pushed
    all the way to `target_ctrl` as if nothing had happened."""
    model = _model_with_arm()
    viewer = _FakeViewer(running=True)
    model.viewer = viewer

    real_is_running = viewer.is_running
    calls = []

    def _is_running_then_stop():
        calls.append(1)
        if len(calls) >= 3:
            return False
        return real_is_running()

    viewer.is_running = _is_running_then_stop

    with pytest.raises(ViewerClosed):
        model.drive_ctrl(np.array([0.5]), n_steps=10)

    assert model.data.ctrl[0] != pytest.approx(0.5)  # never reached the full target
