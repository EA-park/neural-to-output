---
name: generate-sbom
description: Regenerate sbom.md, the project's Software Bill of Materials — a table of pyproject.toml's direct dependencies (project.dependencies + every dependency group) with version, license, repo URL, and purpose, plus a second table of external artifacts (model checkpoints etc. downloaded at runtime, e.g. via huggingface_hub.hf_hub_download) sourced from external_artifacts.json. Use when asked to "generate the SBOM", "update sbom.md", "list project dependencies with licenses", "check the license on this checkpoint/model", or after pyproject.toml/external_artifacts.json changes (also runs automatically via a PostToolUse hook, including when a .py/.ipynb file referencing hf_hub_download is edited).
---

Paths below are relative to the repo root (`neural-to-output/`).

## What this does

`sbom.md` at the repo root holds two markdown tables.

**Package table** — sorted alphabetically by package name, columns: 번호 (No.),
라이브러리명 (name), 버전 (version), 라이선스 (license), 공식 저장소 URL
(repo/homepage URL), 사용 목적 및 주요 기능 (purpose/summary). Only lists packages
`pyproject.toml` **directly** declares — `project.dependencies` plus every entry
across all `dependency-groups` (`dev`, `license`, `examples`, `demos`) —
currently 11 packages. It does *not* include the full transitive closure
`uv.lock` resolves (~234 packages): those are dependencies-of-dependencies
never named in `pyproject.toml` itself, so they're filtered out as noise for
an SBOM meant to answer "what did we choose to depend on." Lives between
`<!-- SBOM:START -->` / `<!-- SBOM:END -->` markers.

**External artifacts table** — model checkpoints, datasets, or anything else
downloaded at runtime from somewhere other than a pip package (currently:
`huggingface_hub.hf_hub_download(...)` calls) — these have no installed
package metadata `pip-licenses` can read, so this table is rendered straight
from [external_artifacts.json](external_artifacts.json), a small
hand-maintained manifest (one object per artifact: `repo_id`, `type`,
`version`, `license`, `license_note`, `url`, `used_in`, `purpose`). Figuring
out an external repo's actual license generally needs a human or agent to go
look — the tool can't infer it, only remind you to. Lives between
`<!-- SBOM-EXTERNAL:START -->` / `<!-- SBOM-EXTERNAL:END -->` markers.

Both tables' prose header above them is written once and preserved on later
runs — re-running only replaces the table between each pair of markers, so
it's safe to run repeatedly without accumulating duplicate content.

## Run (agent path)

```bash
uv run --all-groups python .claude/skills/generate-sbom/generate_sbom.py
```

This drives `pip-licenses` (already a project dependency, in the `license`
group) with `--with-system` (so `pip-licenses` itself, which pip-licenses
excludes from its own report by default, is still included) against
everything `--all-groups` installs, then filters the result down to names
that PEP 503-normalize-match a requirement string somewhere in
`pyproject.toml`'s `project.dependencies` or `dependency-groups`. It does not
parse license/URL/summary out of `pyproject.toml`/`uv.lock` directly — that
metadata isn't in either file, so it reads it off the packages `pip-licenses`
finds actually installed in `.venv`.

Output: prints `sbom.md: wrote N packages, M external artifacts` to stderr
(plus a `WARNING no installed package matched: ...` line if a declared
dependency isn't actually installed — sync first) and (re)writes `sbom.md`.

It also scans `src/`, `examples/`, `demos/`, `tests/` (`.py` and `.ipynb`
files) for `hf_hub_download(...)` call sites and extracts each one's
`repo_id` (handles both `hf_hub_download("org/name", ...)` directly and the
much more common `repo_id = "org/name"` assigned a few lines above the call).
Any `repo_id` found in code but missing from `external_artifacts.json` prints
`WARNING hf_hub_download() references not in external_artifacts.json: ...` —
that's your cue to research the artifact's license (check the host repo's own
license via its API/LICENSE file, and whether the specific artifact declares
a different one — see `external_artifacts.json`'s existing entry for how that
research got documented) and add an entry.

## Auto-update on file changes

A `PostToolUse` hook in [.claude/settings.json](../../settings.json) runs
[hook.sh](hook.sh) after every `Edit`/`Write`/`MultiEdit`, which runs the
generator above when the edited `file_path` is `pyproject.toml`,
`external_artifacts.json`, or a `.py`/`.ipynb` file whose (post-edit) content
contains `hf_hub_download` (a cheap `grep`, not the generator's own more
careful per-cell notebook scan — good enough to decide whether to bother
regenerating). Edits to anything else are a no-op (checked via the hook's
`case` match on `tool_input.file_path` piped in as hook stdin JSON).

`sbom.md` is gitignored (see `.gitignore`) — it's a generated artifact, not a
tracked file. `external_artifacts.json` is tracked — it's the actual source
of truth for the external-artifacts table, not a build output.

## Gotchas

- **`--all-groups` is required.** Without it, `uv run` only resolves the
  default (undeclared) group, missing `dev`/`license`/`examples`/`demos`
  — e.g. `flask`, `pytest` would silently disappear from the table.
- **A package's `License` metadata field can itself be the full multi-line
  license text**, not a short name — hit this for real with `pybv` (a
  transitive dep, since fixed by filtering to direct deps only, but any direct
  dep could do the same thing). Every table cell goes through `clean_cell()`,
  which collapses all whitespace/newlines to single spaces, escapes `|`, and
  truncates past 300 chars — without this the raw license text's embedded
  newlines split across markdown table rows and corrupted the table structure.
- **`pip-licenses`'s `URL` field is Home-page/Project-URL metadata, not always
  literally a GitHub link** (e.g. `pytest` resolves to its docs site). That's
  still the package's own "official" link, so it's used as-is.
- **License field is `pip-licenses`'s own best-effort extraction** (classifier
  first, falls back to metadata) — short-name inconsistencies like `"MIT
  License"` vs `"MIT"` are its limitation, not something this script corrects.
- **`lerobot`'s reported version (`0.6.1`) doesn't reflect that
  `[tool.uv.sources]` actually pins it to a specific fork/commit** — that's
  the version string the installed package's own metadata reports, not a bug
  in the generator.
- **The whole run takes ~3s** on an already-`uv sync`'d `.venv`. A cold
  `.venv` would first need `uv sync --all-groups`, which is slow
  (`torch`/`mujoco`/`lerobot` are large).

## Troubleshooting

- **`pip-licenses: command not found` under plain `uv run`**: means the
  `license` group isn't in the active resolution — use `--all-groups` (or at
  minimum `--group license`), not bare `uv run`.
- **`WARNING no installed package matched: <name>`**: a `pyproject.toml`
  dependency isn't installed in `.venv` — run `uv sync --all-groups` first.
- **`WARNING hf_hub_download() references not in external_artifacts.json: <repo_id>`**:
  code downloads an external artifact the manifest doesn't know about yet —
  research its license and add an entry to `external_artifacts.json`, then
  rerun (or just save the `.py`/`.ipynb` file again — the hook picks it up).
