from .base import Decoder
from .config import DecoderConfig, DecoderType, FeatureType
from .eeg import EEGNet
from .emg import EMGDecoder

__all__ = [
    "Decoder",
    "DecoderConfig",
    "DecoderType",
    "EEGNet",
    "EMGDecoder",
    "FeatureType",
]
