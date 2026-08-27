from n2o.command import ActionType, Command
from n2o.decoder import DecoderConfig, DecoderType


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
