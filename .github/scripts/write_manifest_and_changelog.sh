#!/usr/bin/env bash
# Writes the requested version into manifest.json, and optionally prepends the changelog section.
set -euo pipefail

[ -n "${NEXT_VERSION+x}" ] || { echo "Missing required environment variable: NEXT_VERSION" >&2; exit 1; }
WRITE_CHANGELOG="${WRITE_CHANGELOG:-true}"
case "$WRITE_CHANGELOG" in true|false) ;; *) echo "WRITE_CHANGELOG must be true or false." >&2; exit 1 ;; esac
if [ "$WRITE_CHANGELOG" = "true" ]; then
  # Same scratch dir as the planning step; each run: is a fresh shell, so it cannot be inherited.
  export RELEASE_ENTRIES="${RUNNER_TEMP:-$PWD}/release-entries.md"
fi
python3 - <<'PY'
import json
import os
import re
from pathlib import Path

version = os.environ["NEXT_VERSION"]
write_changelog = os.environ.get("WRITE_CHANGELOG", "true") == "true"

manifest_path = Path("custom_components/zte_tracker/manifest.json")
raw = manifest_path.read_text(encoding="utf-8")
current = json.loads(raw)["version"]
# Rewrite the value in place so key order, indentation and spacing survive untouched.
needle = json.dumps("version") + ": " + json.dumps(current)
if raw.count(needle) != 1:
    raise SystemExit(f"Cannot locate a unique version entry in {manifest_path}")
manifest_path.write_text(raw.replace(needle, json.dumps("version") + ": " + json.dumps(version), 1), encoding="utf-8")
if json.loads(manifest_path.read_text(encoding="utf-8"))["version"] != version:
    raise SystemExit("Manifest rewrite did not take effect")

if write_changelog:
    section = [f"## {version}", ""]
    notes = os.environ.get("RELEASE_NOTES", "").strip()
    if notes:
        # A ## line here would read as the next version heading, cutting this section short for every parser,
        # including the one below that replaces a repeated run's section.
        notes = "\n".join(re.sub(r"^##(?!#)", "###", line) for line in notes.splitlines())
        section += [notes, ""]
    section += Path(os.environ["RELEASE_ENTRIES"]).read_text(encoding="utf-8").strip("\n").splitlines() + [""]

    changelog_path = Path("CHANGELOG.md")
    lines = changelog_path.read_text(encoding="utf-8").splitlines()
    # Drop any section for this version first, so a repeated run replaces it instead of stacking a second one.
    kept, skipping = [], False
    for line in lines:
        if line.startswith("## "):
            skipping = line.strip() == f"## {version}"
        if not skipping:
            kept.append(line)
    insert_at = next((i for i, line in enumerate(kept) if line.startswith("## ")), len(kept))
    kept[insert_at:insert_at] = section
    changelog_path.write_text("\n".join(kept).rstrip("\n") + "\n", encoding="utf-8")
PY
git --no-pager diff --stat
