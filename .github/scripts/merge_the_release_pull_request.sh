#!/usr/bin/env bash
# Merges the release pull request, then waits for master to actually carry it. Deletes the branch and fails if the merge is refused.
# Outputs: merged_sha
set -euo pipefail

for name in BRANCH GH_TOKEN NEXT_VERSION PR_NUMBER GITHUB_REPOSITORY GITHUB_OUTPUT; do
  [ -n "${!name+x}" ] || { echo "Missing required environment variable: $name" >&2; exit 1; }
done
# Scratch files belong in the runner temp dir, never in the tree a pull request is built from.
export SCRATCH="${RUNNER_TEMP:-$PWD}"
cleanup_branch() {
  gh api -X DELETE "repos/${GITHUB_REPOSITORY}/git/refs/heads/${BRANCH}" >/dev/null 2>&1 || true
}

# The commit the pre merge checks ran on, passed in so that anything pushed since makes the merge fail.
: "${HEAD_SHA:?Missing required environment variable: HEAD_SHA}"

python3 - > "$SCRATCH/merge-payload.json" <<'PY'
import json
import os

version = os.environ["NEXT_VERSION"]
print(json.dumps({
    "merge_method": "squash",
    "commit_title": f"chore(release): prepare {version}",
    "commit_message": "",
    # Refuse the merge if anything was pushed to the branch after we read it.
    "sha": os.environ["HEAD_SHA"],
}))
PY
if ! merge_response=$(gh api -X PUT "repos/${GITHUB_REPOSITORY}/pulls/${PR_NUMBER}/merge" --input "$SCRATCH/merge-payload.json" 2>"$SCRATCH/merge-error"); then
  merge_error=$(cat "$SCRATCH/merge-error")
  printf '%s\n' "$merge_error" >&2
  echo "Merging pull request #${PR_NUMBER} was refused, so nothing was tagged or released." >&2
  case "$merge_error" in
    *review*|*approv*|*"not mergeable"*|*405*)
      echo "This is almost always a review, status check, or mergeability rule." >&2
      echo "  Re-run with auto_merge disabled and merge the pull request yourself." >&2
      ;;
    *409*)
      echo "The branch moved after the checks ran, so the merge was refused on purpose." >&2
      echo "Someone pushed to ${BRANCH}, so it was left in place. Review it, then re-run." >&2
      exit 1
      ;;
  esac
  # Deleting the branch closes the pull request too, so the next run starts from a clean master.
  cleanup_branch
  echo "Removed ${BRANCH} and closed #${PR_NUMBER}. master is untouched, so a retry is clean." >&2
  exit 1
fi

# The merge API names the commit it created, so there is no guessing which commit to tag.
MERGED_SHA=$(printf '%s' "$merge_response" | python3 -c 'import json,sys; print(json.load(sys.stdin)["sha"])')
# The ref takes a moment to become readable, and a stale master would ship the wrong tree.
for attempt in 1 2 3 4 5 6; do
  git fetch --force origin refs/heads/master:refs/remotes/origin/master
  CANDIDATE=$(git rev-parse refs/remotes/origin/master)
  [ "$CANDIDATE" = "$MERGED_SHA" ] && break
  if git merge-base --is-ancestor "$MERGED_SHA" "$CANDIDATE"; then
    echo "master moved past the release commit ${MERGED_SHA} before it could be tagged." >&2
    echo "Re-run this workflow: it will publish master's head instead of an out of date tree." >&2
    # The pull request did merge, so the branch is spent and would only be reused by mistake.
    cleanup_branch
    exit 1
  fi
  sleep $((attempt * 5))
done
if [ "$(git rev-parse refs/remotes/origin/master)" != "$MERGED_SHA" ]; then
  echo "master never showed the merge commit ${MERGED_SHA}, so nothing was tagged or released." >&2
  echo "Check pull request #${PR_NUMBER} before re-running, the branch ${BRANCH} was left in place on purpose." >&2
  exit 1
fi
cleanup_branch
echo "master is now ${MERGED_SHA} carrying ${NEXT_VERSION}."
printf 'merged_sha=%s\n' "$MERGED_SHA" >> "$GITHUB_OUTPUT"
