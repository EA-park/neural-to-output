from n2o.decoder import DecoderConfig


def test_new_fields_default_to_unset():
    config = DecoderConfig()
    assert config.n_times is None
    assert config.windowing_kwargs is None
    assert config.preprocessing_kwargs == {}
    assert config.labels is None
