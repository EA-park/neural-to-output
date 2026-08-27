# Decoder

Documentation for decoding algorithms that translate a signal into a raw prediction.

## `DecoderConfig`

[`DecoderConfig`][n2o.decoder.config.DecoderConfig] (in `n2o.decoder`) carries a decoder's shape and behavior, set once at
construction and read back throughout the pipeline:

```python
from n2o.decoder import DecoderConfig, DecoderType

decoder_config = DecoderConfig(
    type=DecoderType.CLASSIFICATION,
    input_feature=59,
    output_feature=4,
    windowing_kwargs={"start_offset_sec": 0.0, "stop_offset_sec": 2.0},
)
```

- `type` — `DecoderType.CLASSIFICATION` or `.REGRESSION`, or a `tuple[DecoderType, ...]`
  for a decoder wrapping more than one internal model with no shared trunk.
- `n_times` / `windowing_kwargs` / `preprocessing_kwargs` — feed `Decoder.prepare()`
  (below). `prepare()` raises if `windowing_kwargs` was never set — there's no
  dataset-agnostic default.
- `labels` — the class-index-ordered label list, filled in automatically by a
  `Classification` decoder's own `window()`. Always `None` for `Regression` (a
  continuous target has no discrete label list). `Command.translate()` reads
  `decoder.config.labels[decoded_signal]` once this is set.

## `prepare()`: raw recording -> decoder-ready windows

`Decoder.__call__()` (what `N2O.run()` calls, not `decode()` directly) auto-detects a
raw, unwindowed recording — the shape `DatasetLoader.read()`/`StreamLoader.read()`
return — and calls `prepare()` on it once, caching the result:

```python
def prepare(self, raw_dataset):
    self.preprocess(raw_dataset, **self.config.preprocessing_kwargs)
    return self.window(raw_dataset, **self.config.windowing_kwargs)
```

An already-windowed array (the common per-step case for a live stream) skips this and
goes straight to `decode()`. `self.cycle` (default `1`) decides which prepared window a
later `__call__()` picks — `cycle <= 1` always decodes the most recent window; `cycle >
1` picks one of `cycle` windows spread evenly across the prepared set, advancing (and
wrapping) each call. `N2O.run()` reads `getattr(self.decoder, "cycle", 1)` to decide how
many steps to loop.

## `Classification` vs. `Regression`

Every concrete decoder subclasses [`Classification`][n2o.decoder.classification.base.Classification] or [`Regression`][n2o.decoder.regression.base.Regression] (in
`n2o.decoder.classification`/`n2o.decoder.regression`) — not [`Decoder`][n2o.decoder.base.Decoder] directly, unless
its `preprocess()`/`window()` genuinely needs a third shape neither provides. Both
implement `preprocess()` identically (`bandpass_standardize()` — 4-38Hz bandpass +
exponential-moving-standardize), but `window()` differs by what the target looks like:

- `Classification.window()` = [`window_by_event()`][n2o.decoder.utils.windowing.window_by_event] — one event-locked window per trial,
  a single per-trial label. This is where `config.labels` gets set.
- `Regression.window()` = [`window_by_sliding()`][n2o.decoder.utils.windowing.window_by_sliding] — overlapping fixed-length windows
  tiled across the whole recording, ignoring trial/event boundaries (a continuous
  target like a joint angle doesn't have one value per discrete trial).

`n2o.decoder.utils` (`preprocessing.py`/`windowing.py`) holds these as plain functions,
also usable directly on whatever `signal.read()` returns:

```python
from n2o.decoder.utils import bandpass_standardize, window_by_event, label_names

bandpass_standardize(raw_dataset)
windows = window_by_event(raw_dataset, start_offset_sec=...)
labels = label_names(windows)
```

## Building a model by name: `BraindecodeDecoder`

`n2o.decoder.classification.braindecode_entry` mirrors the dataset registry's approach
for `braindecode.models`: every `braindecode.models.EEGModuleMixin` subclass (~60
architectures) is registered at import time, and [`BraindecodeDecoder`][n2o.decoder.classification.braindecode_entry.BraindecodeDecoder]`(Classification)`
builds any of them by name:

```python
from n2o.decoder.classification import BraindecodeDecoder, list_models
from n2o.decoder.utils import expected_window_samples

n_times = expected_window_samples(
    raw_dataset, start_offset_sec=0.0, stop_offset_sec=2.0
)
decoder = BraindecodeDecoder("EEGNetv4", n_chans=22, n_outputs=4, n_times=n_times)
```

[`expected_window_samples()`][n2o.decoder.utils.windowing.expected_window_samples] predicts what `window_by_event()` will produce without
actually windowing first, so the model's layer shapes (`n_chans`/`n_outputs`/`n_times`
are required constructor arguments — unlike a moabb dataset class, a model isn't
zero-arg constructible) can be fixed before calling `prepare()`.

`BraindecodeDecoder.from_pretrained(name, repo_id, **kwargs)` only supports checkpoints
published via braindecode's own `model.push_to_hub()` (a real `config.json` on the Hub
repo) — shape and weights both load automatically. A checkpoint saved via skorch's
`EEGClassifier.save_params()` instead has no recoverable shape; build with the plain
constructor for those (see `examples/03_explore_eegnet_decoder.ipynb`).

## Routing: `output_type`

Separate from `DecoderConfig`, every `Decoder` subclass must declare an `output_type`
ClassVar — a [`FeatureType`][n2o.decoder.config.FeatureType] (`ACTION` or `LANGUAGE`) describing what kind of prediction
it produces:

```python
from n2o.decoder import Decoder, FeatureType


class MyLanguageDecoder(Decoder):
    output_type = FeatureType.LANGUAGE

    def decode(self, signal): ...
```

`N2O.run()` reads this at runtime to decide the next pipeline stage — see
[Architecture → Routing](../architecture.md#routing-featuretype-and-controller).
Anything else, including the undeclared default, makes `run()` raise `ValueError` —
there's no silent fallback.
