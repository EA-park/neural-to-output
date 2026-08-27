from .base import Classification
from .braindecode_entry import (
    BRAINDECODE_MODEL_REGISTRY,
    BraindecodeDecoder,
    list_models,
)
from .new_ofner_eegnet import NewOfnerEEGNet
from .ofner_eegnet import OfnerEEGNet

__all__ = [
    "BRAINDECODE_MODEL_REGISTRY",
    "BraindecodeDecoder",
    "Classification",
    "NewOfnerEEGNet",
    "OfnerEEGNet",
    "list_models",
]
