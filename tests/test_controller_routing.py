from n2o import N2O
from n2o.command import Command
from n2o.controller import LanguageController
from n2o.decoder import Decoder, DecoderConfig, DecoderType, FeatureType
from n2o.robot.arm import RobotArm
from n2o.robot.hand import RobotHand
from n2o.signal.dataset import SignalDataset


class _FakeSignal(SignalDataset):
    def read(self):
        return "sample"


class _ActionDecoder(Decoder):
    output_type = FeatureType.ACTION

    def __init__(self):
        self.config = DecoderConfig(type=DecoderType.CLASSIFICATION)

    def decode(self, signal):
        return {"arm": "action-command", "hand": "action-command"}


class _LanguageDecoder(Decoder):
    output_type = FeatureType.LANGUAGE

    def __init__(self):
        self.config = DecoderConfig()

    def decode(self, signal):
        return "language-command"


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
