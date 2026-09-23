#!/usr/bin/env bash
# Bumps manifest.json and prepends the changelog section. The only script that edits the working tree.
set -euo pipefail

for name in NEXT_VERSION RELEASE_NOTES; do
  [ -n "${!name+x}" ] || { echo "Missing required environment variable: $name" >&2; exit 1; }
done
# Same scratch dir as the planning step; each run: is a fresh shell, so it cannot be inherited.
export RELEASE_ENTRIES="${RUNNER_TEMP:-$PWD}/release-entries.md"
python3 - <<'PY'
import json
import os
import re
from pathlib import Path

version = os.environ["NEXT_VERSION"]

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
