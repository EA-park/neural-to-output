# Installation

## Prerequisites

- [uv](https://docs.astral.sh/uv/) for dependency management
- [direnv](https://direnv.net/) for loading local environment variables (optional)
- Python `>=3.12`

## Setup

Clone the repository and install the core dependencies:

```bash
uv sync
```

Copy the environment template and let direnv load it:

```bash
cp .envrc.example .envrc
direnv allow
```

Install whichever [dependency group](index.md#dependency-groups) matches what you're
doing next — e.g. `uv sync --group examples` to work through the tutorial notebooks, or
`uv sync --group dev` to run the test suite.
