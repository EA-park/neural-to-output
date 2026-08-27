from __future__ import annotations

import inspect

import braindecode.models as _braindecode_models

from ..config import DecoderConfig, DecoderType, FeatureType
from .base import Classification

BRAINDECODE_MODEL_REGISTRY: dict[str, type] = {
    name: obj
    for name, obj in vars(_braindecode_models).items()
    if inspect.isclass(obj)
    and issubclass(obj, _braindecode_models.EEGModuleMixin)
    and obj is not _braindecode_models.EEGModuleMixin
}
"""braindecode.models architecture classes, keyed by class name -- e.g. `"EEGNet"`,
`"ShallowFBCSPNet"`, `"Deep4Net"`. Populated once at import time by introspecting
`braindecode.models` for every `EEGModuleMixin` subclass (the shared base every real
braindecode architecture inherits from), the same "don't hand-write one entry per
upstream class" approach `signal/dataset/moabb_entry.py` uses for moabb datasets.

Unlike a moabb dataset class, a model architecture isn't zero-arg constructible -- its
layers are shaped by the input/output it's built for, so `BraindecodeDecoder` (below)
always requires `n_chans`/`n_outputs`/`n_times` explicitly. There's no dataset-agnostic
default for those, mirroring `window_by_event()`'s `start_offset_sec`.
"""


def list_models() -> list[str]:
    """Names of registered braindecode model architectures, e.g. `["ATCNet", ..., "ShallowFBCSPNet"]`."""
    return sorted(BRAINDECODE_MODEL_REGISTRY)


class BraindecodeDecoder(Classification):
    """Generic `Classification` decoder wrapping one `braindecode.models` architecture,
    selected by name.

    ```python
    decoder = BraindecodeDecoder("EEGNet", n_chans=22, n_outputs=4, n_times=500)
    decoder.decode(window)  # -> predicted class index
    ```

    `self.model` is the raw `torch.nn.Module` (untrained on construction) -- reach into
    it directly to load pretrained weights (`decoder.model.load_state_dict(...)`) or wrap
    it in a `skorch`/`braindecode.EEGClassifier` for training or checkpoint loading that
    needs skorch's own save/load format (see `examples/03_explore_eegnet_decoder.ipynb`
    for a real pretrained-checkpoint example). `output_type` defaults to
    `FeatureType.ACTION` since a class index is the common case; override it on the
    instance for a `FeatureType.LANGUAGE` model.

    For a checkpoint published via braindecode's own Hub-native `model.push_to_hub()`
    (i.e. its repo has a `config.json`), `from_pretrained(name, repo_id)` skips
    specifying `n_chans`/`n_outputs`/`n_times` by hand entirely -- see its own
    docstring for why a non-Hub-native checkpoint (e.g. one saved via skorch's own
    `save_params()`, like `examples/03`'s) can't be auto-detected this way and needs
    the plain constructor below instead.

    `preprocessing_kwargs`/`windowing_kwargs` (optional) record how *this* decoder
    expects a raw recording to be prepared before it can decode it -- the same
    preprocessing/windowing config the underlying weights were trained with, if this
    decoder is wrapping a pretrained checkpoint. Set `windowing_kwargs` (at least
    `start_offset_sec`) at construction and call `prepare(raw_dataset)` afterwards
    instead of calling `n2o.decoder.bandpass_standardize()`/`.window_by_event()`
    yourself with the right numbers remembered by hand -- `prepare()` itself lives on
    `Decoder`, `preprocess()`/`window()` on `Classification`, both reading
    `self.config`.
    """

    output_type = FeatureType.ACTION

    def __init__(
        self,
        name: str,
        *,
        n_chans: int,
        n_outputs: int,
        n_times: int,
        preprocessing_kwargs: dict | None = None,
        windowing_kwargs: dict | None = None,
        **kwargs,
    ):
        if name not in BRAINDECODE_MODEL_REGISTRY:
            raise ValueError(f"unknown braindecode model {name!r}; see list_models()")
        config = DecoderConfig(
            type=DecoderType.CLASSIFICATION,
            input_feature=n_chans,
            output_feature=n_outputs,
            n_times=n_times,
            windowing_kwargs=windowing_kwargs,
            preprocessing_kwargs=preprocessing_kwargs or {},
        )
        super().__init__(config)
        self.name = name
        self.model = BRAINDECODE_MODEL_REGISTRY[name](
            n_chans=n_chans, n_outputs=n_outputs, n_times=n_times, **kwargs
        )

    @classmethod
    def from_pretrained(
        cls,
        name: str,
        repo_id: str,
        *,
        preprocessing_kwargs: dict | None = None,
        windowing_kwargs: dict | None = None,
        **kwargs,
    ) -> BraindecodeDecoder:
        """Build a `name`-architecture decoder from a Hub-native pretrained checkpoint
        (one published via `model.push_to_hub()`, i.e. `repo_id` has its own
        `config.json`) -- shape (`n_chans`/`n_outputs`/`n_times`) and weights load
        fully automatically via braindecode's own `Model.from_pretrained()`, no shape
        specified by hand.

        Only Hub-native checkpoints are supported here. A checkpoint saved via
        skorch's own `EEGClassifier.save_params()` (e.g.
        `braindecode/plot_bcic_iv_2a_moabb_trial`, used by
        `examples/03_explore_eegnet_decoder.ipynb`) has no `config.json` at all --
        checked directly against real checkpoint repos, shape isn't recoverable from
        its raw weight tensors either (a tensor's shape encodes `n_chans`/`n_outputs`
        at a different position per architecture, and `n_times` is unrecoverable
        post-pooling/conv without replaying each architecture's own shape math, which
        braindecode exposes no inverse of). Build the decoder with the plain
        constructor (explicit `n_chans`/`n_outputs`/`n_times`) for that kind instead.

        `windowing_kwargs`/`preprocessing_kwargs` still can't be auto-derived even for
        a Hub-native checkpoint -- a `config.json` only records the model's own
        constructor args, not the data-prep recipe its weights were trained with -- so
        pass them explicitly here if `prepare()` will be called afterwards. Extra
        `**kwargs` are forwarded to `Model.from_pretrained()` (e.g. `n_outputs=...` to
        rebuild the head for a different class count).
        """
        if name not in BRAINDECODE_MODEL_REGISTRY:
            raise ValueError(f"unknown braindecode model {name!r}; see list_models()")
        from huggingface_hub import HfApi

        if not HfApi().file_exists(repo_id, "config.json"):
            raise ValueError(
                f"{repo_id!r} has no config.json -- shape can't be auto-detected for "
                "a non-Hub-native checkpoint (e.g. one saved via skorch's own "
                "save_params()). Build the decoder with explicit "
                "n_chans/n_outputs/n_times instead."
            )
        model = BRAINDECODE_MODEL_REGISTRY[name].from_pretrained(repo_id, **kwargs)
        decoder = cls(
            name,
            n_chans=model.n_chans,
            n_outputs=model.n_outputs,
            n_times=model.n_times,
            preprocessing_kwargs=preprocessing_kwargs,
            windowing_kwargs=windowing_kwargs,
        )
        decoder.model = model
        return decoder

    def decode(self, signal):
        """Run `signal` (an `(n_chans, n_times)` array) through the model; return the
        predicted class index."""
        import torch

        self.model.eval()
        with torch.no_grad():
            x = torch.as_tensor(signal).float().unsqueeze(0)
            logits = self.model(x)
            return int(logits.argmax(dim=1).item())
