# Installation

## Prerequisites

- [uv](https://docs.astral.sh/uv/) for dependency management
- [direnv](https://direnv.net/) for loading local environment variables (optional)

## Setup

Clone the repository and install dependencies:

```bash
uv sync
```

Copy the environment template and let direnv load it:

```bash
cp .envrc.example .envrc
direnv allow
```
