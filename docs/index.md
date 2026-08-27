# N2O: Neural to Output

An open-source framework for translating human electrophysiological signals into robot actions.

## Overview

`neural-to-output` provides the building blocks for turning raw electrophysiological
signals (e.g. EEG, EMG) into robot actions. The pipeline is fixed: a **signal** source
is decoded by a **decoder** into a raw prediction, which a **command** translates into
per-part actions sent to a **robot**'s arm/hand/camera — or, when the decoder's output
is language-typed, routed to a **controller** instead.

See [Getting Started](getting-started/index.md) to set up the project locally, or
[Architecture](architecture.md) for how the pipeline fits together.

## Where to look next

- **Just want to run something?** [`examples/`](https://github.com/EA-park/neural-to-output/tree/main/examples)
  holds numbered, self-contained Jupyter notebooks — the project's tutorial content, worked
  through step by step.
- **Want to understand how the pieces connect?** That's what this site is for — usage
  documentation for each pipeline stage, not a restatement of the notebooks.
