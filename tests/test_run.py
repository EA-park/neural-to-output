import time

import pytest

from n2o import N2O
from n2o.command import Command
from n2o.decoder import Decoder, DecoderConfig, DecoderType, FeatureType
from n2o.robot.arm import RobotArm
from n2o.robot.hand import RobotHand
from n2o.robot.language_controller import LanguageController
from n2o.signal.dataset import DatasetLoader


class _FakeSignal(DatasetLoader):
    """A `.read()` stand-in for `n2o.signal` -- doesn't need real `path=`/`name=`
    validation (or a real metadata file on disk), so it skips `DatasetLoader.__init__`."""

    def __init__(self):
        self.path = None
        self.name = None

    def read(self):
        return "sample"


class _RecordingArm(RobotArm):
    def __init__(self):
        self.moved_with = None

    def move(self, decoder_type, command):
        self.moved_with = command


class _RecordingHand(RobotHand):
    def __init__(self):
        self.moved_with = None

    def move(self, decoder_type, command):
        self.moved_with = command


class _RecordingController(LanguageController):
    def __init__(self):
        self.acted_with = None

    def act(self, command, robot):
        self.acted_with = command


class _ActionDecoder(Decoder):
    output_type = FeatureType.ACTION

    def __init__(self):
        self.config = DecoderConfig(type=DecoderType.CLASSIFICATION)

    def decode(self, signal):
        return {"arm": "action-command", "hand": "action-command"}

    def preprocess(self, raw_dataset, **kwargs):
        raise NotImplementedError

    def window(self, raw_dataset, **kwargs):
        raise NotImplementedError


class _LanguageDecoder(Decoder):
    output_type = FeatureType.LANGUAGE

    def __init__(self):
        self.config = DecoderConfig()

    def decode(self, signal):
        return "language-command"

    def preprocess(self, raw_dataset, **kwargs):
        raise NotImplementedError

    def window(self, raw_dataset, **kwargs):
        raise NotImplementedError


def _n2o_with(decoder) -> N2O:
    n2o = N2O()
    n2o.signal = _FakeSignal()
    n2o.decoder = decoder
    n2o.robot.arm = _RecordingArm()
    n2o.robot.hand = _RecordingHand()
    n2o.controller = _RecordingController()
    n2o.command = Command()
    return n2o


def test_action_output_type_routes_to_arm_and_hand():
    n2o = _n2o_with(_ActionDecoder())
    n2o.run()
    assert n2o.robot.arm.moved_with == "action-command"
    assert n2o.robot.hand.moved_with == "action-command"
    assert n2o.controller.acted_with is None


def test_language_output_type_routes_to_controller():
    n2o = _n2o_with(_LanguageDecoder())
    n2o.run()
    assert n2o.controller.acted_with == "language-command"
    assert n2o.robot.arm.moved_with is None
    assert n2o.robot.hand.moved_with is None


def test_action_output_type_skips_move_when_arm_is_none():
    n2o = _n2o_with(_ActionDecoder())
    n2o.robot.arm = None

    n2o.run()  # must not raise AttributeError

    assert n2o.robot.hand.moved_with == "action-command"


def test_action_output_type_skips_move_when_hand_is_none():
    n2o = _n2o_with(_ActionDecoder())
    n2o.robot.hand = None

    n2o.run()  # must not raise AttributeError

    assert n2o.robot.arm.moved_with == "action-command"


class _ArmOnlyCommand(Command):
    """Like `GripSpreadCommand`/`OfnerCommand`: only one part gets a real gesture
    per call, the other stays `None` -- not because that part doesn't exist
    (`robot.arm`/`robot.hand` are both set), but because this particular decoded
    label has nothing to say about it."""

    def translate(self, decoder, decoded_signal):
        return {"type": decoder.config.type, "arm": "up", "hand": None}


class _HandOnlyCommand(Command):
    def translate(self, decoder, decoded_signal):
        return {"type": decoder.config.type, "arm": None, "hand": "grip"}


def test_action_output_type_skips_move_when_commands_hand_value_is_none():
    n2o = _n2o_with(_ActionDecoder())
    n2o.command = _ArmOnlyCommand()

    n2o.run()  # must not raise KeyError/TypeError inside hand.move()'s controller

    assert n2o.robot.arm.moved_with == "up"
    assert n2o.robot.hand.moved_with is None


def test_action_output_type_skips_move_when_commands_arm_value_is_none():
    n2o = _n2o_with(_ActionDecoder())
    n2o.command = _HandOnlyCommand()

    n2o.run()  # must not raise KeyError/TypeError inside arm.move()'s controller

    assert n2o.robot.arm.moved_with is None
    assert n2o.robot.hand.moved_with == "grip"


class _LabelDecoder(Decoder):
    output_type = FeatureType.ACTION

    def __init__(self):
        self.config = DecoderConfig(type=DecoderType.CLASSIFICATION)

    def decode(self, signal):
        return "left_hand"

    def preprocess(self, raw_dataset, **kwargs):
        raise NotImplementedError

    def window(self, raw_dataset, **kwargs):
        raise NotImplementedError


class _MotorImageryCommand(Command):
    def translate(self, decoder, decoded_signal):
        command = {"type": decoder.config.type, "arm": None, "hand": None}
        if decoded_signal == "left_hand":
            command["arm"], command["hand"] = "up", "grip"
        return command


class _TypedRecordingArm(RobotArm):
    def __init__(self):
        self.moved_with = None

    def move(self, decoder_type, command):
        self.moved_with = (decoder_type, command)


class _TypedRecordingHand(RobotHand):
    def __init__(self):
        self.moved_with = None

    def move(self, decoder_type, command):
        self.moved_with = (decoder_type, command)


def test_run_dispatches_translated_per_part_commands():
    n2o = N2O()
    n2o.signal = _FakeSignal()
    n2o.decoder = _LabelDecoder()
    n2o.robot.arm = _TypedRecordingArm()
    n2o.robot.hand = _TypedRecordingHand()
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

    def preprocess(self, raw_dataset, **kwargs):
        raise NotImplementedError

    def window(self, raw_dataset, **kwargs):
        raise NotImplementedError


def test_run_raises_for_unsupported_output_type():
    n2o = N2O()
    n2o.signal = _FakeSignal()
    n2o.decoder = _UntypedDecoder()
    n2o.robot.arm = _TypedRecordingArm()
    n2o.robot.hand = _TypedRecordingHand()

    with pytest.raises(ValueError, match="unsupported decoder.output_type"):
        n2o.run()


class _CountingSignal(DatasetLoader):
    def __init__(self):
        self.path = None
        self.name = None
        self.read_count = 0

    def read(self):
        self.read_count += 1
        return "sample"


class _CountingArm(RobotArm):
    def __init__(self):
        self.move_count = 0

    def move(self, decoder_type, command):
        self.move_count += 1


def test_run_reads_decoder_cycle_and_prints_each_result(capsys):
    n2o = N2O()
    signal = _CountingSignal()
    n2o.signal = signal
    n2o.decoder = _ActionDecoder()
    n2o.decoder.cycle = 3
    n2o.robot.arm = _CountingArm()
    n2o.robot.hand = _CountingArm()
    n2o.command = Command()

    n2o.run()

    assert signal.read_count == 3
    assert n2o.robot.arm.move_count == 3
    assert n2o.robot.hand.move_count == 3
    printed = capsys.readouterr().out
    assert printed.count("추론 진행 중") == 3
    assert printed.count("추론 결과") == 3
    assert "[1/3]" in printed
    assert "[3/3]" in printed


def test_run_waits_between_cycles_when_not_simulated_and_something_moved(monkeypatch):
    slept = []
    monkeypatch.setattr(time, "sleep", lambda seconds: slept.append(seconds))

    n2o = N2O()
    signal = _CountingSignal()
    n2o.signal = signal
    n2o.decoder = _ActionDecoder()
    n2o.decoder.cycle = 3
    n2o.robot.arm = _CountingArm()
    n2o.robot.hand = _CountingArm()
    n2o.command = Command()

    n2o.run(simulation=False)

    # 3 cycles -> waits after cycle 1 and 2, not after the last one
    assert slept == [N2O._REAL_HARDWARE_SETTLE_S] * 2


def test_run_does_not_wait_when_nothing_moved_that_cycle(monkeypatch):
    slept = []
    monkeypatch.setattr(time, "sleep", lambda seconds: slept.append(seconds))
    n2o = _n2o_with(_LanguageDecoder())
    n2o.decoder.cycle = 3
    n2o.signal = _CountingSignal()

    n2o.run(simulation=False)

    assert slept == []


def test_run_prints_the_resolved_label_not_the_raw_class_index(capsys):
    # output_type=LANGUAGE (not ACTION) so this only exercises run()'s printing --
    # Command.translate() assumes an already-dict-shaped decoded_signal, which a raw
    # class index isn't, so ACTION would fail here for an unrelated reason.
    class _LabeledDecoder(Decoder):
        output_type = FeatureType.LANGUAGE

        def __init__(self):
            self.config = DecoderConfig(
                type=DecoderType.CLASSIFICATION,
                labels=["rest", "grip"],
            )

        def decode(self, signal):
            return 1

        def preprocess(self, raw_dataset, **kwargs):
            raise NotImplementedError

        def window(self, raw_dataset, **kwargs):
            raise NotImplementedError

    n2o = _n2o_with(_LabeledDecoder())

    n2o.run()

    printed = capsys.readouterr().out
    assert "'grip'" in printed
    assert "추론 결과: 1" not in printed


def test_run_defaults_to_a_single_cycle():
    n2o = _n2o_with(_ActionDecoder())
    n2o.run()
    assert n2o.robot.arm.moved_with == "action-command"


class _SlowSignal(DatasetLoader):
    """Blocks `read()` for `delay_s` -- long enough, relative to a tiny monkeypatched
    `_PROGRESS_TICK_S`, that `_decode_with_progress()`'s background thread is still
    alive for several ticks."""

    def __init__(self, delay_s):
        self.path = None
        self.name = None
        self.delay_s = delay_s

    def read(self):
        time.sleep(self.delay_s)
        return "sample"


def test_decode_with_progress_reprints_while_still_running(monkeypatch, capsys):
    n2o = _n2o_with(_ActionDecoder())
    n2o.signal = _SlowSignal(delay_s=0.25)
    monkeypatch.setattr(N2O, "_PROGRESS_TICK_S", 0.05)

    n2o.run()

    printed = capsys.readouterr().out
    label = "[1/1] 추론 진행 중"
    # 0.25s / 0.05s-per-tick means several reprints, not just the initial one -- a
    # fast decode (this test's own default _FakeSignal, elsewhere) prints it exactly
    # once, so seeing it more than once here proves the re-print loop actually ran.
    assert printed.count(label) >= 3


def test_decode_with_progress_reraises_the_background_threads_exception():
    class _RaisingDecoder(Decoder):
        output_type = FeatureType.ACTION

        def __init__(self):
            self.config = DecoderConfig(type=DecoderType.CLASSIFICATION)

        def decode(self, signal):
            raise RuntimeError("boom")

        def preprocess(self, raw_dataset, **kwargs):
            raise NotImplementedError

        def window(self, raw_dataset, **kwargs):
            raise NotImplementedError

    n2o = _n2o_with(_RaisingDecoder())

    with pytest.raises(RuntimeError, match="boom"):
        n2o.run()
