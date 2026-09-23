#!/usr/bin/env bash
# Builds the release branch name and pull request body for peter-evans/create-pull-request.
# Outputs: base_sha, body_path, branch
set -euo pipefail

for name in AUTO_MERGE GH_TOKEN GITHUB_OUTPUT GITHUB_REPOSITORY GITHUB_RUN_ID NEXT_VERSION; do
  [ -n "${!name+x}" ] || { echo "Missing required environment variable: $name" >&2; exit 1; }
done

case "$AUTO_MERGE" in true|false) ;; *) echo "Invalid auto_merge value: $AUTO_MERGE" >&2; exit 1 ;; esac
BRANCH="chore/release-${NEXT_VERSION}-${GITHUB_RUN_ID}"
BASE_SHA=$(gh api "repos/${GITHUB_REPOSITORY}/git/ref/heads/master" --jq '.object.sha')
# Same scratch dir as the planning step; each run: is a fresh shell, so it cannot be inherited.
export RELEASE_ENTRIES="${RUNNER_TEMP:-$PWD}/release-entries.md"
export RELEASE_PR_BODY="${RUNNER_TEMP:-$PWD}/release-pr-body.md"
python3 - <<'PY'
import os
from pathlib import Path

version = os.environ["NEXT_VERSION"]
entries = Path(os.environ["RELEASE_ENTRIES"]).read_text(encoding="utf-8").strip("\n")
auto = os.environ.get("AUTO_MERGE") == "true"
tail = (
    "This run merges this pull request itself, then tags and publishes."
    if auto
    else "Merge this pull request, then start Auto Release again from the Actions tab, "
    "with the defaults, to tag and publish " + version + "."
)
Path(os.environ["RELEASE_PR_BODY"]).write_text(
    f"Opened by Auto Release for {version}.\n\n{entries}\n\n{tail}\n",
    encoding="utf-8",
)
PY
{
  printf 'branch=%s\n' "$BRANCH"
  printf 'base_sha=%s\n' "$BASE_SHA"
  printf 'body_path=%s\n' "$RELEASE_PR_BODY"
} >> "$GITHUB_OUTPUT"
echo "Prepared pull request metadata for ${BRANCH} at ${BASE_SHA}."
