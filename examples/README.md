# Examples

## Basic usage

```python
from n2o import N2O
from n2o.signal.dataset import EEG
from n2o.decoder import EEGNet
from n2o.robot.arm import LeRobotSO101
from n2o.robot.hand import AmazingHand

n2o = N2O()
n2o.signal = EEG()
n2o.decoder = EEGNet()
n2o.robot.arm = LeRobotSO101()
n2o.robot.hand = AmazingHand()
n2o.run()
```

`n2o.run()` reads one sample from `signal`, decodes it into a command, and sends that
command to both `robot.arm` and `robot.hand`.

## Built-in components

| Axis                  | Module              | Built-in classes                  |
| ---------------------- | -------------------- | ---------------------------------- |
| Signal dataset          | `n2o.signal.dataset` | `EEG` (non-invasive), `InvasiveEEG`, `EMG` |
| Decoder                 | `n2o.decoder`         | `EEGNet`, `EMGDecoder`             |
| Robot arm                | `n2o.robot.arm`       | `LeRobotSO101`, `Gello`, `MockArm` |
| Robot hand                | `n2o.robot.hand`      | `AmazingHand`, `MockHand`          |

All of the above besides `MockArm`/`MockHand` are interface-only stubs for now (no real
hardware/model integration yet) — swap in `MockArm`/`MockHand` to exercise the pipeline
without physical hardware. More datasets, decoders, and robots will be added over time,
following the same pattern (see `CLAUDE.md`).

## Numbered notebooks

This folder holds runnable, numbered Jupyter notebooks (`01_explore_eeg_decoder.ipynb`,
`02_...ipynb`, ...) meant to be worked through in order. Each notebook is
self-contained — markdown cells explain the concept right next to the code that runs
it — so there isn't always a separate write-up on the docs site; when a notebook does
need a longer conceptual walkthrough, that page lives under
[docs/tutorials/](../docs/tutorials/index.md) and links back to the notebook.

Install the extra packages notebooks need (not part of the core `n2o` dependencies)
with:

```bash
uv sync --group examples
uv run --group examples jupyter lab examples/01_explore_eeg_decoder.ipynb
```

- **`01_explore_eeg_decoder.ipynb`** — loads real EEG data (BCI Competition IV 2a via
  `braindecode`/`moabb`), walks through preprocessing, windowing, and the `EEGNet`
  decoder's actual input/output shapes — i.e. what `n2o.signal.dataset.EEG.read()` and
  `n2o.decoder.EEGNet.decode()` need to produce/consume once they're implemented for
  real.
