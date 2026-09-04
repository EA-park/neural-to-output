import pytest

pytest.importorskip("mujoco")

from n2o import N2O
from n2o.command import Command
from n2o.decoder import Decoder, DecoderConfig, DecoderType, FeatureType
from n2o.robot import ControllerType
from n2o.robot.arm import SO101Arm
from n2o.robot.hand import AmazingHand
from n2o.robot.simulation import Simulator
from n2o.signal.dataset import DatasetLoader


@pytest.fixture(autouse=True)
def _no_real_viewer_window(monkeypatch):
    """`N2O.run(controller="simulation")` opens a live viewer automatically (see
    `Simulator.launch_viewer()`) -- make it a no-op so these tests never open a
    real window. Leaving `_model.viewer` at its default `None` (rather than faking
    a viewer object) also sidesteps `_MujocoModel.drive_ctrl()`'s per-step
    `viewer.is_running()` check entirely: any fake viewer whose `is_running()`
    ever returns `False` makes `drive_ctrl()` raise `ViewerClosed` immediately
    (see `test_mujoco_model.py`), and one that always returns `True` would hang
    the `atexit`-registered `wait_for_viewers()` at test-process shutdown."""
    monkeypatch.setattr(Simulator, "launch_viewer", lambda self: None)


class _FakeSignal(DatasetLoader):
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


def _raise_must_not_drive_real_hardware(cmd):
    raise AssertionError("controller='simulation' must not call move()")


def _n2o_with_real_parts() -> N2O:
    # Real SO101Arm/AmazingHand -- not the old dedicated *Sim stand-ins (removed).
    # controller="simulation" now routes through Robot.router(), which calls these
    # parts' own goal() (pure computation) and feeds the result to the shared
    # Simulator -- move() (real hardware) is never called, so an unconnected
    # instance is safe to use here.
    n2o = N2O()
    n2o.signal = _FakeSignal()
    n2o.decoder = _ActionDecoder()
    n2o.command = Command()
    n2o.robot.arm = SO101Arm()
    n2o.robot.hand = AmazingHand()
    n2o.robot.arm.move = _raise_must_not_drive_real_hardware
    n2o.robot.hand.move = _raise_must_not_drive_real_hardware
    return n2o


def test_run_simulation_builds_a_simulator_instead_of_driving_real_hardware():
    n2o = _n2o_with_real_parts()

    n2o.run(controller="simulation")

    assert isinstance(n2o.robot.simulator, Simulator)


def test_run_simulation_reuses_the_same_simulator_across_calls():
    n2o = _n2o_with_real_parts()

    n2o.run(controller="simulation")
    simulator = n2o.robot.simulator
    n2o.run(controller="simulation")

    assert n2o.robot.simulator is simulator


def test_run_simulation_only_covers_parts_actually_assigned():
    n2o = _n2o_with_real_parts()
    n2o.robot.hand = None

    n2o.run(controller="simulation")

    assert n2o.robot.simulator._parts == ("arm",)


def test_run_simulation_excludes_parts_overridden_to_motor_driver():
    # part_controllers overrides the global controller="simulation" for "hand"
    # specifically -- the auto-built Simulator must not cover it.
    n2o = _n2o_with_real_parts()
    n2o.robot.part_controllers = {"hand": ControllerType.MOTOR_DRIVER}
    n2o.robot.hand.move = lambda cmd: None  # hand really does drive now

    n2o.run(controller="simulation")

    assert n2o.robot.simulator._parts == ("arm",)


def test_run_simulation_skips_auto_build_for_parts_with_their_own_simulator():
    # A part already covered by part_simulators (e.g. a caller-built per-part mix)
    # must not also be pulled into the auto-built global Simulator.
    n2o = _n2o_with_real_parts()
    n2o.robot.part_simulators = {"hand": Simulator(["hand"])}

    n2o.run(controller="simulation")

    assert n2o.robot.simulator._parts == ("arm",)
