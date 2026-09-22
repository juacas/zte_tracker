#!/usr/bin/env bash
# Merges the release pull request, then waits for master to actually carry it. Deletes the branch and fails if the merge is refused.
# Outputs: merged_sha
set -euo pipefail

for name in BASE_SHA BRANCH GH_TOKEN NEXT_VERSION PR_NUMBER GITHUB_REPOSITORY GITHUB_OUTPUT; do
  [ -n "${!name+x}" ] || { echo "Missing required environment variable: $name" >&2; exit 1; }
done
# Scratch files belong in the runner temp dir, never in the tree a pull request is built from.
export SCRATCH="${RUNNER_TEMP:-$PWD}"
cleanup_branch() {
  gh api -X DELETE "repos/${GITHUB_REPOSITORY}/git/refs/heads/${BRANCH}" >/dev/null 2>&1 || true
}

python3 - > "$SCRATCH/merge-payload.json" <<'PY'
import json
import os

version = os.environ["NEXT_VERSION"]
print(json.dumps({
    "merge_method": "squash",
    "commit_title": f"chore(release): prepare {version}",
    "commit_message": "",
}))
PY
if ! merge_error=$(gh api -X PUT "repos/${GITHUB_REPOSITORY}/pulls/${PR_NUMBER}/merge" --input "$SCRATCH/merge-payload.json" 2>&1 >/dev/null); then
  printf '%s\n' "$merge_error" >&2
  echo "Merging pull request #${PR_NUMBER} was refused, so nothing was tagged or released." >&2
  case "$merge_error" in
    *review*|*approv*|*"not mergeable"*|*405*)
      echo "This is almost always a review, status check, or mergeability rule." >&2
      echo "  Re-run with auto_merge disabled and merge the pull request yourself." >&2
      ;;
  esac
  # Deleting the branch closes the pull request too, so the next run starts from a clean master.
  cleanup_branch
  echo "Removed ${BRANCH} and closed #${PR_NUMBER}. master is untouched, so a retry is clean." >&2
  exit 1
fi

# The merge API returns before the ref is readable, and a stale master would ship the wrong tree.
MERGED_SHA=""
for attempt in 1 2 3 4 5 6; do
  git fetch --force origin refs/heads/master:refs/remotes/origin/master
  CANDIDATE=$(git rev-parse refs/remotes/origin/master)
  if [ "$CANDIDATE" != "$BASE_SHA" ] && [ "$(git show "${CANDIDATE}:custom_components/zte_tracker/manifest.json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["version"])')" = "$NEXT_VERSION" ]; then
    MERGED_SHA=$CANDIDATE
    break
  fi
  sleep $((attempt * 5))
done
if [ -z "$MERGED_SHA" ]; then
  echo "master never showed ${NEXT_VERSION} after the merge, so nothing was tagged or released." >&2
  echo "Check pull request #${PR_NUMBER} before re-running, the branch ${BRANCH} was left in place on purpose." >&2
  exit 1
fi
cleanup_branch
echo "master is now ${MERGED_SHA} carrying ${NEXT_VERSION}."
printf 'merged_sha=%s\n' "$MERGED_SHA" >> "$GITHUB_OUTPUT"
