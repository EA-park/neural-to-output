# neural-to-output
An open-source framework for translating human electrophysiological signals into robot actions.

## Install

Not yet published to PyPI. Clone the repository and install with [uv](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/EA-park/neural-to-output.git
cd neural-to-output
uv sync
```

## Usage

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

See [examples/](examples/) for more.

## Documentation

Full documentation is available at https://EA-park.github.io/neural-to-output/.
