# Signal

Documentation for supported electrophysiological signal types (e.g. EEG, EMG) and acquisition.

## Dataset vs. Stream

Signal sources come in two shapes, each its own base interface under `n2o.signal`:

- **`n2o.signal.dataset`** — `SignalDataset.read()` reads a bounded, offline recording (e.g. a saved file). Built-ins: `EEG` (non-invasive), `InvasiveEEG`, `EMG`.
- **`n2o.signal.stream`** — `SignalStream.read()` reads the latest chunk from an unbounded, realtime source (e.g. a live device connection). Built-ins: `EEGStream`, `EMGStream`.

`SignalStream` is a sibling interface, not a subclass of `SignalDataset` — the two have genuinely different semantics (indexed access into a finite recording vs. polling a ring buffer), mirroring the split between `mne.io.Raw` and `mne_lsl.stream.StreamLSL` in the MNE ecosystem. Both expose the same `output_spec` class attribute, so `CommandConfig.verify_report()` checks either kind of source against the decoder's `input_spec` identically.

## `SignalConfig`

`SignalConfig` (in `n2o.signal`) is descriptive metadata about the acquisition setup — electrode count, channel names, sample rate, and whether the recording is `SignalType.INVASIVE` or `SignalType.NON_INVASIVE` — separate from `output_spec`'s shape contract:

```python
from n2o.signal import SignalConfig, SignalType

signal_config = SignalConfig(
    num_electrode=14, name=("Fz", "Cz", "Pz"), hz=128, type=SignalType.NON_INVASIVE
)
```

`type` is independent of which class you use (`EEG` vs. `InvasiveEEG` already encode this via class identity) — it lets a `SignalConfig` self-declare it too. `SignalConfig` isn't consumed by `read()` itself; it's for documenting/planning a signal source's setup alongside the rest of the `*Config` family (`DecoderConfig`, `RobotConfig`, `CommandConfig`).

Every concrete class here is currently an interface-only stub (`raise NotImplementedError`).
