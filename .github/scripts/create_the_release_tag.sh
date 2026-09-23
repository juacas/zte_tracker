#!/usr/bin/env bash
# Creates the annotated tag through the Git Data API, refusing a target that master has already moved past.
set -euo pipefail

for name in GH_TOKEN GITHUB_REPOSITORY TAG_MESSAGE TAG_NAME TARGET_SHA; do
  [ -n "${!name+x}" ] || { echo "Missing required environment variable: $name" >&2; exit 1; }
done
# Scratch files belong in the runner temp dir, never in the tree a pull request is built from.
export SCRATCH="${RUNNER_TEMP:-$PWD}"
# A revert stays an ancestor of master, so ancestry alone cannot catch a superseded target.
CURRENT_MASTER=$(gh api "repos/${GITHUB_REPOSITORY}/git/ref/heads/master" --jq '.object.sha')
if [ "$CURRENT_MASTER" != "$TARGET_SHA" ]; then
  echo "Refusing to tag stale target $TARGET_SHA; master is now $CURRENT_MASTER." >&2
  echo "The queued workflow for the newer master commit will handle the release." >&2
  exit 1
fi
python3 - <<'PY'
import json
import os
from pathlib import Path

payload = {
    "tag": os.environ["TAG_NAME"],
    "message": os.environ["TAG_MESSAGE"],
    "object": os.environ["TARGET_SHA"],
    "type": "commit",
}
Path(os.environ["SCRATCH"] + "/tag-payload.json").write_text(json.dumps(payload), encoding="utf-8")
PY
tag_sha=$(gh api "repos/${GITHUB_REPOSITORY}/git/tags" --input "$SCRATCH/tag-payload.json" --jq .sha)
python3 - "$tag_sha" <<'PY'
import json
import os
import sys
from pathlib import Path

payload = {
    "ref": f"refs/tags/{os.environ['TAG_NAME']}",
    "sha": sys.argv[1],
}
Path(os.environ["SCRATCH"] + "/ref-payload.json").write_text(json.dumps(payload), encoding="utf-8")
PY
gh api "repos/${GITHUB_REPOSITORY}/git/refs" --input "$SCRATCH/ref-payload.json" >/dev/null
echo "Created annotated tag."
