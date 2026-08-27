import pytest

from n2o.command import GripSpreadCommand
from n2o.decoder import DecoderConfig, DecoderType


class _FakeDecoder:
    def __init__(self, type_):
        self.config = DecoderConfig(type=type_)


@pytest.mark.parametrize(
    "label,gesture",
    [
        ("feet", "index_pointing"),
        ("left_hand", "grip"),
        ("right_hand", "release"),
        ("tongue", "perfect"),
    ],
)
def test_translate_maps_each_label_to_its_gesture(label, gesture):
    command = GripSpreadCommand()
    result = command.translate(_FakeDecoder(DecoderType.CLASSIFICATION), label)
    assert result == {
        "type": DecoderType.CLASSIFICATION,
        "arm": None,
        "hand": gesture,
    }


def test_translate_rejects_an_unknown_label():
    command = GripSpreadCommand()
    with pytest.raises(KeyError):
        command.translate(_FakeDecoder(DecoderType.CLASSIFICATION), "unknown_label")
