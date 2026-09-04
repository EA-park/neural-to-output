# Third-Party

Documentation for vendored copies of upstream projects, kept at the repo root under
`third_party/`.

## Why this exists

Some hardware this project drives ships reference code that isn't a pip/uv-installable
package — no root `pyproject.toml`/`setup.py` upstream, just example scripts, CAD, and
docs. `third_party/` holds a verbatim copy of that reference material, each in its own
subfolder plus a `NOTICE.md` documenting provenance (upstream repo/commit, what was
copied, license) — since it can't be pulled in as a normal dependency the way
`braindecode`/`moabb` are.

## Current occupant: `third_party/AmazingHand/`

`Demo/`, `PythonExample/`, `LICENSE`, and `README.md`, copied unmodified from
[pollen-robotics/AmazingHand](https://github.com/pollen-robotics/AmazingHand) at tag
`v1.0`. Dual-licensed upstream: Apache-2.0 for software, CC BY 4.0 for the CAD/mesh
files under `Demo/AHSimulation/`. See
[`third_party/AmazingHand/NOTICE.md`](https://github.com/EA-park/neural-to-output/blob/main/third_party/AmazingHand/NOTICE.md)
for the full breakdown.

[`AmazingHand.move()`](../robot/hand/index.md)
was ported from `PythonExample/AmazingHand_Demo.py`'s `rustypot` usage and per-motor
calibration formula — kept here as a reference to check that mapping against, not
imported by `n2o` at runtime (`PythonExample/AmazingHand_Demo.py` itself has
import-time side effects — it opens a hardcoded serial port at module load — so it's
meant to be read, not imported).

## Adding a new vendored dependency

1. Copy the relevant upstream files into a new `third_party/<name>/` subfolder.
2. Write a `NOTICE.md` there documenting the source repo, the exact ref/commit
   vendored, and the license(s) involved — see the `AmazingHand` one as a template.
3. Add an entry to
   [`.claude/skills/generate-sbom/vendored_dependencies.json`](https://github.com/EA-park/neural-to-output/blob/main/.claude/skills/generate-sbom/vendored_dependencies.json)
   so it shows up in [`sbom.md`](https://github.com/EA-park/neural-to-output/blob/main/sbom.md)'s
   vendored-dependencies table — the `generate-sbom` skill warns if a `third_party/`
   subfolder isn't covered by that manifest.
