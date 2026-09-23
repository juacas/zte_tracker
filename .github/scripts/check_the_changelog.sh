#!/usr/bin/env bash
# Fails if the target commit has no changelog section for the version being released.
set -euo pipefail

[ -n "${VERSION+x}" ] || { echo "Missing required environment variable: VERSION" >&2; exit 1; }
python3 - <<'PY'
import os
from pathlib import Path

expected = f"## {os.environ['VERSION']}"
headings = {
    line.strip()
    for line in Path("CHANGELOG.md").read_text(encoding="utf-8").splitlines()
    if line.startswith("## ")
}
if expected not in headings:
    raise SystemExit(f"Missing CHANGELOG.md section: {expected}")
PY
