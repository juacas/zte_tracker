#!/usr/bin/env bash
# Creates the annotated tag through the Git Data API, refusing a target that master has already moved past.
set -euo pipefail

for name in GH_TOKEN GITHUB_REPOSITORY PRERELEASE TAG_MESSAGE TAG_NAME TARGET_SHA; do
  [ -n "${!name+x}" ] || { echo "Missing required environment variable: $name" >&2; exit 1; }
done
case "$PRERELEASE" in true|false) ;; *) echo "Invalid prerelease value: $PRERELEASE" >&2; exit 1 ;; esac
# Scratch files belong in the runner temp dir, never in the tree a pull request is built from.
export SCRATCH="${RUNNER_TEMP:-$PWD}"
# A revert stays an ancestor of master, so ancestry alone cannot catch a superseded target.
CURRENT_MASTER=$(gh api "repos/${GITHUB_REPOSITORY}/git/ref/heads/master" --jq '.object.sha')
if [ "$CURRENT_MASTER" != "$TARGET_SHA" ]; then
  echo "Refusing to tag stale target $TARGET_SHA; master is now $CURRENT_MASTER." >&2
  echo "Start Auto Release again from the Actions tab: it publishes master's head without bumping a second version." >&2
  exit 1
fi

OBJECT_SHA="$TARGET_SHA"
export OBJECT_SHA
if [ "$PRERELEASE" = "true" ]; then
  MANIFEST_VERSION=$(python3 -c 'import json; from pathlib import Path; print(json.loads(Path("custom_components/zte_tracker/manifest.json").read_text(encoding="utf-8"))["version"])')
  if [ "$MANIFEST_VERSION" != "$TAG_NAME" ]; then
    echo "Prerelease manifest version $MANIFEST_VERSION does not match tag $TAG_NAME." >&2
    exit 1
  fi
  BASE_TREE=$(gh api "repos/${GITHUB_REPOSITORY}/git/commits/${TARGET_SHA}" --jq .tree.sha)
  python3 - <<'PY'
import json
import os
from pathlib import Path

manifest = Path("custom_components/zte_tracker/manifest.json").read_text(encoding="utf-8")
payload = {
    "content": manifest,
    "encoding": "utf-8",
}
Path(os.environ["SCRATCH"] + "/blob-payload.json").write_text(json.dumps(payload), encoding="utf-8")
PY
  BLOB_SHA=$(gh api "repos/${GITHUB_REPOSITORY}/git/blobs" --input "$SCRATCH/blob-payload.json" --jq .sha)
  python3 - "$BASE_TREE" "$BLOB_SHA" <<'PY'
import json
import os
import sys
from pathlib import Path

payload = {
    "base_tree": sys.argv[1],
    "tree": [
        {
            "path": "custom_components/zte_tracker/manifest.json",
            "mode": "100644",
            "type": "blob",
            "sha": sys.argv[2],
        }
    ],
}
Path(os.environ["SCRATCH"] + "/tree-payload.json").write_text(json.dumps(payload), encoding="utf-8")
PY
  TREE_SHA=$(gh api "repos/${GITHUB_REPOSITORY}/git/trees" --input "$SCRATCH/tree-payload.json" --jq .sha)
  python3 - "$TREE_SHA" <<'PY'
import json
import os
import sys
from pathlib import Path

payload = {
    "message": f"chore(release): prepare {os.environ['TAG_NAME']}",
    "tree": sys.argv[1],
    "parents": [os.environ["TARGET_SHA"]],
    "author": {
        "name": "github-actions[bot]",
        "email": "41898282+github-actions[bot]@users.noreply.github.com",
    },
    "committer": {
        "name": "github-actions[bot]",
        "email": "41898282+github-actions[bot]@users.noreply.github.com",
    },
}
Path(os.environ["SCRATCH"] + "/commit-payload.json").write_text(json.dumps(payload), encoding="utf-8")
PY
  OBJECT_SHA=$(gh api "repos/${GITHUB_REPOSITORY}/git/commits" --input "$SCRATCH/commit-payload.json" --jq .sha)
  export OBJECT_SHA
fi

python3 - <<'PY'
import json
import os
from pathlib import Path

payload = {
    "tag": os.environ["TAG_NAME"],
    "message": os.environ["TAG_MESSAGE"],
    "object": os.environ["OBJECT_SHA"],
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
