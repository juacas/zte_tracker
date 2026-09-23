#!/usr/bin/env bash
# Waits for a human to merge the release pull request, so auto_merge off still publishes in one run.
# Env: GH_TOKEN, GITHUB_OUTPUT, GITHUB_REPOSITORY, NEXT_VERSION, PR_NUMBER, PR_URL, WAIT_MINUTES
# Outputs: merged_sha
set -euo pipefail

for name in GH_TOKEN GITHUB_OUTPUT GITHUB_REPOSITORY NEXT_VERSION PR_NUMBER PR_URL WAIT_MINUTES; do
  [ -n "${!name+x}" ] || { echo "Missing required environment variable: $name" >&2; exit 1; }
done
case "$WAIT_MINUTES" in '' | *[!0-9]*) echo "Invalid WAIT_MINUTES value: $WAIT_MINUTES" >&2; exit 1 ;; esac
[ "$WAIT_MINUTES" -ge 1 ] || { echo "WAIT_MINUTES must be at least 1" >&2; exit 1; }

deadline=$((SECONDS + WAIT_MINUTES * 60))
echo "Review and merge ${PR_URL} to release ${NEXT_VERSION}."
echo "This run waits up to ${WAIT_MINUTES} minutes for that merge, then tags and publishes it."

while :; do
  # A transient API error must not be read as "not merged yet", so an empty answer only retries.
  answer=$(gh api "repos/${GITHUB_REPOSITORY}/pulls/${PR_NUMBER}" \
    --jq '[.state, (.merged | tostring), (.merge_commit_sha // "")] | @tsv' 2>/dev/null) || answer=""
  if [ -n "$answer" ]; then
    IFS=$'\t' read -r state merged merge_sha <<<"$answer"
    if [ "$merged" = "true" ]; then
      [ -n "$merge_sha" ] || { echo "${PR_URL} is merged but GitHub reported no merge commit." >&2; exit 1; }
      printf 'merged_sha=%s\n' "$merge_sha" >> "$GITHUB_OUTPUT"
      echo "Merged as ${merge_sha}. Tagging and publishing ${NEXT_VERSION}."
      exit 0
    fi
    if [ "$state" = "closed" ]; then
      echo "${PR_URL} was closed without merging, so ${NEXT_VERSION} was not released." >&2
      exit 1
    fi
  fi
  if [ "$SECONDS" -ge "$deadline" ]; then
    echo "Waited ${WAIT_MINUTES} minutes and ${PR_URL} is still open." >&2
    echo "Merge it and start Auto Release again: it publishes the merged version instead of bumping a new one." >&2
    exit 1
  fi
  sleep 20
done
