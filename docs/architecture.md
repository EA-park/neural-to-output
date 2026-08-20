# Architecture

## Pipeline

`n2o` wires three interchangeable components into a single orchestrator, `N2O`: a
`signal` source is decoded by a `decoder` into a command, which is sent to a
`robot`'s `arm` and `hand`.

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

`N2O.run()` reads one sample from `signal`, decodes it into a command via `decoder`,
and sends that command to both `robot.arm` and `robot.hand`.

## Package layout

`src/n2o/` mirrors the pipeline as sibling packages. Each follows the same pattern: a
`base.py` abstract base class defining the interface, one file per concrete
implementation, and an `__init__.py` that re-exports the public names.

| Package              | Interface              | Built-in implementations                   |
| --------------------- | ----------------------- | -------------------------------------------- |
| `n2o.signal.dataset`   | `SignalDataset.read()`   | `EEG` (non-invasive), `InvasiveEEG`, `EMG`   |
| `n2o.decoder`          | `Decoder.decode(signal)` | `EEGNet`, `EMGDecoder`                       |
| `n2o.robot.arm`        | `RobotArm.move(command)` | `LeRobotSO101`, `Gello`, `MockArm`           |
| `n2o.robot.hand`       | `RobotHand.move(command)`| `AmazingHand`, `MockHand`                    |

`n2o.robot.Robot` is a plain container binding one `arm` + one `hand` instance.

Every implementation besides `MockArm`/`MockHand` is currently an interface-only stub
(`raise NotImplementedError`) — no real hardware or model integration exists yet. Use
the `Mock*` classes to exercise the full pipeline without physical hardware.

See [Tutorials → Adding a Component](tutorials/adding-a-component.md) for how to add a
new dataset, decoder, or robot.
