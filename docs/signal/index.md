# Signal

Documentation for electrophysiological signal sources (e.g. EEG, EMG) — offline
datasets and realtime streams.

## Dataset vs. Stream

Signal sources come in two shapes, each its own interface under `n2o.signal`:

- **[`n2o.signal.dataset.DatasetLoader`][n2o.signal.dataset.loader.DatasetLoader]** — offline/indexed sources. A concrete class
  (not an ABC), constructed with exactly one of `path` (a local folder) or `name` (a
  registered dataset library, e.g. `"Ofner2017"`).
- **[`n2o.signal.stream.StreamLoader`][n2o.signal.stream.loader.StreamLoader]** — realtime/device sources. A sibling to
  `DatasetLoader`, not a subclass of it (mirrors `mne.io.Raw` vs.
  `mne_lsl.stream.StreamLSL`). No concrete stream ships yet.

## `DatasetLoader`

```python
from n2o.signal.dataset import DatasetLoader

loader = DatasetLoader(name="BNCI2014_001")
info = loader.info()  # DatasetInfo: origin, cue-relative data range, channel count
raw_dataset = loader.read()  # a raw, unwindowed recording
```

`DatasetLoader.list_libraries()` / `library_tree()` show what's registered — the
registry (`DATASET_LIBRARY`) is populated almost entirely from `moabb.datasets` at
import time (one dynamic entry per moabb dataset class, ~150 of them), so most public
BCI datasets need no code to add. `library_tree()` refuses to return the full tree
inline past `inline_limit` (default 30) unless you pass `to_file=` to write it out
instead.

`read()` only *loads* — it fetches the raw recording and returns it as-is. Turning
that into decoder-ready windows is the [decoder](../decoder/index.md)'s job, not the
signal source's.

### `path=` mode

There's no registry entry to source metadata from for a local recording, so
`DatasetLoader(path=...)` requires a `dataset_info.py` file to already exist inside
`path` (raised as `FileNotFoundError` at construction, not lazily). Generate one with
[`write_metadata_template()`][n2o.signal.dataset.metadata_template.write_template]:

```python
import n2o.signal.dataset as dataset

dataset.write_metadata_template(path)  # writes a blank, hand-fillable template
```

Fill it in, then construct `DatasetLoader(path=...)`. `read()` stays a
`NotImplementedError` stub for this mode.

## `StreamLoader`

Same read-a-sample shape as `DatasetLoader`, but for an unbounded, realtime source
(polling the latest chunk rather than indexed access into a finite recording) — no
concrete implementation exists yet, so there's nothing to add here beyond the base
interface until a real device integration lands.

## `SignalConfig`

[`SignalConfig`][n2o.signal.config.SignalConfig] (in `n2o.signal`) is descriptive metadata about an acquisition setup —
electrode count, channel names, sample rate, and whether it's `SignalType.INVASIVE` or
`SignalType.NON_INVASIVE`:

```python
from n2o.signal import SignalConfig, SignalType

signal_config = SignalConfig(
    num_electrode=14, name=("Fz", "Cz", "Pz"), hz=128, type=SignalType.NON_INVASIVE
)
```

It's not consumed by `read()` itself — it's for documenting/planning a signal source's
setup alongside the rest of the `*Config` family (`DecoderConfig`, `RobotConfig`,
`CommandConfig`).
