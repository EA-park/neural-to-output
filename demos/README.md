# Demos

Standalone applications built on top of `n2o`/the SO-101 hardware, as opposed to the
numbered tutorial notebooks in [`examples/`](../examples/README.md) — this is why these
have their own `demos` uv dependency group instead of using `examples`'s (which stays
scoped to what the tutorials need).

- `quickstart.py` — the same signal → decoder → command → robot wiring as
  [ROADMAP.md](../ROADMAP.md)'s "quickstart를 UI로" entry describes, hand-written as a
  plain script. For a GUI over this same wiring, see [`apps/`](../apps/README.md).

