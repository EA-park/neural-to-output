from typing import ClassVar

from n2o import N2O
from n2o.command import CommandConfig
from n2o.decoder import Decoder
from n2o.robot.arm import MockArm
from n2o.robot.hand import MockHand
from n2o.signal.dataset import DatasetLoader


class _FakeSignal(DatasetLoader):
    output_spec: ClassVar[dict] = {"channels": 59, "samples": 100}

    def __init__(self):
        self.path = None
        self.name = None


class _FakeDecoder(Decoder):
    input_spec: ClassVar[dict] = {"channels": 59, "samples": 100}
    output_spec: ClassVar[dict] = {"x": "float", "y": "float"}

    def decode(self, signal):
        raise NotImplementedError

    def preprocess(self, raw_dataset, **kwargs):
        raise NotImplementedError

    def window(self, raw_dataset, **kwargs):
        raise NotImplementedError


def _n2o_with_specs() -> N2O:
    n2o = N2O()
    n2o.signal = _FakeSignal()
    n2o.decoder = _FakeDecoder()
    n2o.robot.arm = MockArm()
    n2o.robot.hand = MockHand()
    return n2o


def test_verify_report_reports_unknown_without_command_config():
    report = CommandConfig().verify_report(_n2o_with_specs())
    assert not report.ok
    assert report.checks[0].status == "match"  # signal <-> decoder
    assert report.checks[1].status == "unknown"  # decoder -> command (undeclared)
    assert report.checks[2].status == "unknown"  # command -> robot.arm (undeclared)
    assert report.checks[3].status == "unknown"  # command -> robot.hand (undeclared)


def test_verify_report_matches_once_command_config_bridges_the_gap():
    n2o = _n2o_with_specs()
    n2o.robot.arm.input_spec = {"joint_targets": "dict[str, float]"}
    n2o.robot.hand.input_spec = {"joint_targets": "dict[str, float]"}
    command_config = CommandConfig(
        input_feature={"x": "float", "y": "float"},
        output_feature={"joint_targets": "dict[str, float]"},
    )

    report = command_config.verify_report(n2o)

    assert report.ok
    assert not report.has_mismatch


def test_verify_report_flags_mismatch():
    n2o = _n2o_with_specs()
    n2o.decoder.output_spec = {"x": "float", "y": "float"}
    command_config = CommandConfig(input_feature={"unexpected_key": "float"})

    report = command_config.verify_report(n2o)

    assert not report.ok
    assert report.has_mismatch
    assert "MISMATCH" in str(report)
