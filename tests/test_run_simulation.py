import pytest

pytest.importorskip("mujoco")

import time
from typing import ClassVar

from n2o import N2O
from n2o.command import Command
from n2o.decoder import Decoder, DecoderConfig, DecoderType, FeatureType
from n2o.robot.arm import RobotArm
from n2o.robot.hand import RobotHand
from n2o.robot.simulation import AmazingHandSim, SO101ArmSim
from n2o.signal.dataset import DatasetLoader


class _FakeViewer:
    def sync(self):
        pass

    def is_running(self):
        return False  # already "closed" -- any atexit-registered wait returns instantly

    def close(self):
        pass


@pytest.fixture(autouse=True)
def _no_real_viewer_window(monkeypatch):
    """`N2O.run(simulation=True)` now opens a live viewer automatically (see
    `n2o.robot.simulation.enable_live_view`) -- fake out `mujoco.viewer.launch_passive`
    so these tests never open a real window or leave a real `atexit` wait registered
    that would hang the test process at shutdown."""
    monkeypatch.setattr(
        "mujoco.viewer.launch_passive", lambda model, data: _FakeViewer()
    )


class _FakeSignal(DatasetLoader):
    output_spec: ClassVar[dict] = {"channels": 59, "samples": 100}

    def __init__(self):
        self.path = None
        self.name = None

    def read(self):
        return "sample"


class _ActionDecoder(Decoder):
    output_type = FeatureType.ACTION

    def __init__(self):
        self.config = DecoderConfig(type=DecoderType.CLASSIFICATION)

    def decode(self, signal):
        return {"arm": "up", "hand": "grip"}

    def preprocess(self, raw_dataset, **kwargs):
        raise NotImplementedError

    def window(self, raw_dataset, **kwargs):
        raise NotImplementedError


class _UnusedArm(RobotArm):
    def move(self, decoder_type, command):
        raise AssertionError("simulation=True must not call the real robot.arm.move()")


class _UnusedHand(RobotHand):
    def move(self, decoder_type, command):
        raise AssertionError("simulation=True must not call the real robot.hand.move()")


def _n2o_with_real_and_sim_parts() -> N2O:
    n2o = N2O()
    n2o.signal = _FakeSignal()
    n2o.decoder = _ActionDecoder()
    n2o.command = Command()
    n2o.robot.arm = _UnusedArm()
    n2o.robot.hand = _UnusedHand()
    return n2o


def test_run_simulation_drives_mujoco_sim_instead_of_robot_arm_and_hand():
    n2o = _n2o_with_real_and_sim_parts()

    n2o.run(simulation=True)

    assert isinstance(n2o._sim_arm, SO101ArmSim)
    assert isinstance(n2o._sim_hand, AmazingHandSim)


def test_run_simulation_reuses_the_same_sim_instance_across_calls():
    n2o = _n2o_with_real_and_sim_parts()

    n2o.run(simulation=True)
    sim_arm, sim_hand = n2o._sim_arm, n2o._sim_hand
    n2o.run(simulation=True)

    assert n2o._sim_arm is sim_arm
    assert n2o._sim_hand is sim_hand


def test_run_simulation_skips_sim_hand_when_robot_hand_is_none():
    n2o = _n2o_with_real_and_sim_parts()
    n2o.robot.hand = None

    n2o.run(simulation=True)

    assert isinstance(n2o._sim_arm, SO101ArmSim)
    assert n2o._sim_hand is None


def test_run_waits_the_simulation_settle_time_between_cycles(monkeypatch):
    slept = []
    monkeypatch.setattr(time, "sleep", lambda seconds: slept.append(seconds))
    n2o = _n2o_with_real_and_sim_parts()
    n2o.decoder.cycle = 3

    n2o.run(simulation=True)

    # move() in simulation is already synchronous (see SO101ArmSim._drive_ctrl()),
    # which itself calls time.sleep() to pace the live viewer -- that's expected and
    # unrelated. What run() adds on top is N2O._SIMULATION_SETTLE_S (3s, shorter than
    # the real-hardware wait) between cycles, so a live viewer is actually watchable
    # -- not the real-hardware settle wait (N2O._REAL_HARDWARE_SETTLE_S, 10s).
    assert (
        slept.count(N2O._SIMULATION_SETTLE_S) == 2
    )  # 3 cycles -> 2 waits, not after the last
    assert N2O._REAL_HARDWARE_SETTLE_S not in slept
