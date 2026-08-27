import numpy as np

from n2o.decoder import DecoderType, FeatureType, OfnerEEGNet


def test_construct_loads_the_bundled_checkpoint():
    decoder = OfnerEEGNet()
    assert decoder.config.type == DecoderType.CLASSIFICATION
    assert decoder.config.input_feature == 61
    assert decoder.config.output_feature == 7
    assert decoder.config.n_times == 1536
    assert decoder.config.windowing_kwargs == {
        "start_offset_sec": 0.0,
        "stop_offset_sec": 0.0,
    }
    assert decoder.output_type == FeatureType.ACTION
    assert decoder.cycle == 3


def test_construct_sets_ofner2017s_own_class_labels():
    decoder = OfnerEEGNet()
    assert decoder.config.labels == [
        "rest",
        "right_elbow_extension",
        "right_elbow_flexion",
        "right_hand_close",
        "right_hand_open",
        "right_pronation",
        "right_supination",
    ]


def test_decode_returns_a_valid_class_index():
    decoder = OfnerEEGNet()
    signal = np.random.default_rng(0).normal(size=(61, 1536)).astype("float32")
    pred = decoder.decode(signal)
    assert isinstance(pred, int)
    assert 0 <= pred < 7


def test_two_instances_load_the_same_weights():
    # proves the checkpoint actually loads (not just a fresh random model each time)
    a = OfnerEEGNet()
    b = OfnerEEGNet()
    for p_a, p_b in zip(a.model.parameters(), b.model.parameters()):
        assert (p_a == p_b).all()
