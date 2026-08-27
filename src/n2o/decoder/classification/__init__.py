from .base import Classification
from .braindecode_entry import (
    BRAINDECODE_MODEL_REGISTRY,
    BraindecodeDecoder,
    list_models,
)
from .ofner_eegnet import OfnerEEGNet
from .new_ofner_eegnet import NewOfnerEEGNet

__all__ = [
    "BRAINDECODE_MODEL_REGISTRY",
    "BraindecodeDecoder",
    "Classification",
    "OfnerEEGNet",
    "NewOfnerEEGNet",
    "list_models",
]
