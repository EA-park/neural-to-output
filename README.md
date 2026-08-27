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
from n2o.signal.dataset import DatasetLoader
from n2o.decoder import BraindecodeDecoder
from n2o.robot.arm import LeRobotSO101
from n2o.robot.hand import AmazingHand

n2o = N2O()
n2o.signal = DatasetLoader(path="path/to/recording")
n2o.decoder = BraindecodeDecoder("EEGNet", n_chans=59, n_outputs=4, n_times=100)
n2o.robot.arm = LeRobotSO101()
n2o.robot.hand = AmazingHand()
n2o.run()
```

See [examples/](examples/) for the numbered tutorial notebooks, or [demos/](demos/) for
standalone applications (e.g. a real EEG dataset driving the real SO-101 arm through a
web UI).

## What each layer needs to decide

| Layer  | Decisions |
| ------ | --------- |
| Signal | Which dataset/library to read from, and the cue-relative data range (start~end seconds around each cue) |
