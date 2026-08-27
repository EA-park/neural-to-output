import pytest

from n2o.command import OfnerCommand
from n2o.command.ofner_command import LABEL_TO_GESTURE
from n2o.decoder import DecoderConfig, DecoderType

_LABELS = [
    "rest",
    "right_elbow_extension",
    "right_elbow_flexion",
    "right_hand_close",
    "right_hand_open",
    "right_pronation",
    "right_supination",
]


class _FakeDecoder:
    def __init__(self, labels):
        self.config = DecoderConfig(type=DecoderType.CLASSIFICATION, labels=labels)


@pytest.mark.parametrize("index,label", list(enumerate(_LABELS)))
def test_translate_maps_each_label_index_to_its_gesture(index, label):
    command = OfnerCommand()

    result = command.translate(_FakeDecoder(_LABELS), index)

    part, gesture = LABEL_TO_GESTURE[label]
    expected = {"type": DecoderType.CLASSIFICATION, "arm": None, "hand": None}
    expected[part] = gesture
    assert result == expected


def test_translate_rejects_an_out_of_range_index():
    command = OfnerCommand()
    with pytest.raises(IndexError):
        command.translate(_FakeDecoder(_LABELS), len(_LABELS))
