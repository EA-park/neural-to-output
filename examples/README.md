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

## Numbered scripts

This folder will also hold runnable, numbered scripts (`01_run_the_robot.py`,
`02_...py`, ...) meant to be worked through in order. Each one pairs with a tutorial
under [docs/tutorials/](../docs/tutorials/index.md) on the docs site — the tutorial
explains the concept, the script here is what you actually run.
