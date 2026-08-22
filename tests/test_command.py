import pytest

from n2o import N2O
from n2o.command import ActionType, Command
from n2o.decoder import Decoder, DecoderConfig, DecoderType, FeatureType
from n2o.robot.arm import RobotArm
from n2o.robot.hand import RobotHand
from n2o.signal.dataset import SignalDataset


class _FakeDecoder:
    def __init__(self, type_):
        self.config = DecoderConfig(type=type_)


def test_command_translate_defaults_to_part_keyed_decoded_signal():
    command = Command()
    result = command.translate(
        _FakeDecoder(DecoderType.CLASSIFICATION), {"arm": "up", "hand": "grip"}
    )
    assert result == {"type": DecoderType.CLASSIFICATION, "arm": "up", "hand": "grip"}


def test_command_translate_spreads_tuple_decoder_type_keys():
    command = Command()
    decoded_signal = {
        "arm": (ActionType.CARTESIAN_RELATIVE, {"dx": 0.5}),
        "hand": "grip",
    }
    result = command.translate(
        _FakeDecoder((DecoderType.CLASSIFICATION, DecoderType.REGRESSION)),
        decoded_signal,
    )
    assert result["type"] == (DecoderType.CLASSIFICATION, DecoderType.REGRESSION)
    assert result["arm"] == (ActionType.CARTESIAN_RELATIVE, {"dx": 0.5})
    assert result["hand"] == "grip"


class _FakeSignal(SignalDataset):
    def read(self):
        return "sample"


class _LabelDecoder(Decoder):
    output_type = FeatureType.ACTION

    def __init__(self):
        self.config = DecoderConfig(type=DecoderType.CLASSIFICATION)

    def decode(self, signal):
        return "left_hand"


class _MotorImageryCommand(Command):
    def translate(self, decoder, decoded_signal):
        command = {"type": decoder.config.type, "arm": None, "hand": None}
        if decoded_signal == "left_hand":
            command["arm"], command["hand"] = "up", "grip"
        return command


class _RecordingArm(RobotArm):
    def __init__(self):
        self.moved_with = None

    def move(self, decoder_type, command):
        self.moved_with = (decoder_type, command)


class _RecordingHand(RobotHand):
    def __init__(self):
        self.moved_with = None

    def move(self, decoder_type, command):
        self.moved_with = (decoder_type, command)


def test_run_dispatches_translated_per_part_commands():
    n2o = N2O()
    n2o.signal = _FakeSignal()
    n2o.decoder = _LabelDecoder()
    n2o.robot.arm = _RecordingArm()
    n2o.robot.hand = _RecordingHand()
    n2o.command = _MotorImageryCommand()

    n2o.run()

    assert n2o.robot.arm.moved_with == (DecoderType.CLASSIFICATION, "up")
    assert n2o.robot.hand.moved_with == (DecoderType.CLASSIFICATION, "grip")


class _UntypedDecoder(Decoder):
    output_type = FeatureType.SIGNAL

    def __init__(self):
        self.config = DecoderConfig()

    def decode(self, signal):
        return "sample"


def test_run_raises_for_unsupported_output_type():
    n2o = N2O()
    n2o.signal = _FakeSignal()
    n2o.decoder = _UntypedDecoder()
    n2o.robot.arm = _RecordingArm()
    n2o.robot.hand = _RecordingHand()

    with pytest.raises(ValueError, match="unsupported decoder.output_type"):
        n2o.run()
