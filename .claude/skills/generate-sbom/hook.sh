#!/usr/bin/env bash
# PostToolUse hook: regenerate sbom.md whenever Claude Code edits pyproject.toml, the
# external-artifacts manifest, or a .py/.ipynb file that references hf_hub_download()
# (a new or changed external model/checkpoint download -- see generate_sbom.py's
# scan_hf_hub_download_repo_ids()/find_undocumented_artifacts() for how the generator
# then warns if that repo_id isn't yet in external_artifacts.json).
# Wired in .claude/settings.json under hooks.PostToolUse (matcher: Edit|Write|MultiEdit).
set -euo pipefail

file_path="$(cat | python3 -c "import json,sys; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))")"

case "$file_path" in
  */pyproject.toml|pyproject.toml)
    cd "${CLAUDE_PROJECT_DIR:-.}"
    uv run --all-groups python .claude/skills/generate-sbom/generate_sbom.py
    ;;
  */external_artifacts.json|external_artifacts.json)
    cd "${CLAUDE_PROJECT_DIR:-.}"
    uv run --all-groups python .claude/skills/generate-sbom/generate_sbom.py
    ;;
  *.py|*.ipynb)
    if [ -f "$file_path" ] && grep -q "hf_hub_download" "$file_path" 2>/dev/null; then
      cd "${CLAUDE_PROJECT_DIR:-.}"
      uv run --all-groups python .claude/skills/generate-sbom/generate_sbom.py
    fi
    ;;
esac
