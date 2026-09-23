#!/usr/bin/env bash
# Ends the run with the pull request left open, for when auto_merge is off.
set -euo pipefail

for name in NEXT_VERSION PR_URL; do
  [ -n "${!name+x}" ] || { echo "Missing required environment variable: $name" >&2; exit 1; }
done
# Merging pushes to master, which retriggers this workflow, so no runner waits here.
echo "Review and merge ${PR_URL} to publish ${NEXT_VERSION}."
echo "That merge pushes to master, which starts this workflow again and publishes the release."
