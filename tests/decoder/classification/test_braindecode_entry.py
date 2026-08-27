from unittest.mock import patch

import numpy as np
import pytest

from n2o.decoder import BraindecodeDecoder, DecoderType, FeatureType, list_models


def test_list_models_includes_known_architectures():
    models = list_models()
    assert "EEGNet" in models
    assert "ShallowFBCSPNet" in models
    assert models == sorted(models)


def test_construct_rejects_an_unknown_model_name():
    with pytest.raises(ValueError, match="unknown braindecode model"):
        BraindecodeDecoder("NotAModel", n_chans=1, n_outputs=1, n_times=1)


def test_construct_builds_the_named_torch_module():
    decoder = BraindecodeDecoder("EEGNet", n_chans=22, n_outputs=4, n_times=500)
    assert decoder.name == "EEGNet"
    assert decoder.config.type == DecoderType.CLASSIFICATION
    assert decoder.config.input_feature == 22
    assert decoder.config.output_feature == 4
    assert decoder.config.n_times == 500
    assert decoder.output_type == FeatureType.ACTION


def test_decode_returns_a_valid_class_index():
    decoder = BraindecodeDecoder("EEGNet", n_chans=22, n_outputs=4, n_times=500)
    signal = np.random.default_rng(0).normal(size=(22, 500)).astype("float32")
    pred = decoder.decode(signal)
    assert isinstance(pred, int)
    assert 0 <= pred < 4


def test_extra_kwargs_are_forwarded_to_the_model():
    # ShallowFBCSPNet accepts final_conv_length -- forwarding proves **kwargs reaches
    # the underlying braindecode class rather than being silently dropped.
    decoder = BraindecodeDecoder(
        "ShallowFBCSPNet",
        n_chans=22,
        n_outputs=4,
        n_times=1125,
        final_conv_length="auto",
    )
    assert decoder.model.final_conv_length is not None


def test_prepare_without_windowing_kwargs_raises():
    decoder = BraindecodeDecoder("EEGNet", n_chans=4, n_outputs=2, n_times=200)
    with pytest.raises(ValueError, match="windowing_kwargs"):
        decoder.prepare("fake")


def test_prepare_applies_this_decoders_own_preprocessing_and_windowing(
    synthetic_concat_dataset,
):
    # fixture's trials are 2.0s long at 100Hz with no offset -> 200 samples;
    # -0.5s start offset should extend that to 250 samples, same as calling
    # bandpass_standardize()/window_by_event() directly with these kwargs.
    decoder = BraindecodeDecoder(
        "EEGNet",
        n_chans=3,
        n_outputs=2,
        n_times=250,
        windowing_kwargs={"start_offset_sec": -0.5, "stop_offset_sec": 0.0},
    )
    windows = decoder.prepare(synthetic_concat_dataset)
    assert len(windows) == 2
    X0, _y0, _crop = windows[0]
    assert X0.shape == (3, 250)  # EOG channel dropped by bandpass_standardize()
    assert decoder.config.labels == ["left_hand", "right_hand"]


def test_from_pretrained_rejects_an_unknown_model_name():
    with pytest.raises(ValueError, match="unknown braindecode model"):
        BraindecodeDecoder.from_pretrained("NotAModel", "some/repo")


def test_from_pretrained_rejects_a_checkpoint_without_config_json():
    # real network call (HfApi().file_exists only, no download) against a real
    # checkpoint known to have no config.json -- examples/03's own pretrained
    # checkpoint, saved via skorch's save_params() rather than push_to_hub().
    with pytest.raises(ValueError, match="config.json"):
        BraindecodeDecoder.from_pretrained(
            "ShallowFBCSPNet", "braindecode/plot_bcic_iv_2a_moabb_trial"
        )


def test_from_pretrained_builds_around_the_loaded_model():
    # no real Hub-native (push_to_hub-saved) braindecode checkpoint was readily
    # available to test against for real, so this mocks the two external calls
    # (HfApi().file_exists, Model.from_pretrained) and checks from_pretrained()
    # wires their result into a BraindecodeDecoder correctly.
    fresh_model = BraindecodeDecoder(
        "EEGNet", n_chans=22, n_outputs=4, n_times=500
    ).model

    with (
        patch("huggingface_hub.HfApi") as mock_hf_api_cls,
        patch.object(
            type(fresh_model), "from_pretrained", return_value=fresh_model
        ) as mock_from_pretrained,
    ):
        mock_hf_api_cls.return_value.file_exists.return_value = True
        decoder = BraindecodeDecoder.from_pretrained("EEGNet", "some/hub-native-repo")

    mock_from_pretrained.assert_called_once_with("some/hub-native-repo")
    assert decoder.model is fresh_model
    assert decoder.config.input_feature == 22
    assert decoder.config.output_feature == 4
    assert decoder.config.n_times == 500
