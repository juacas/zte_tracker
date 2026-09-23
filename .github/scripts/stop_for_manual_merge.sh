#!/usr/bin/env bash
# Ends the run with the pull request left open, for when auto_merge is off.
set -euo pipefail

for name in NEXT_VERSION PR_URL; do
  [ -n "${!name+x}" ] || { echo "Missing required environment variable: $name" >&2; exit 1; }
done
# Nothing publishes on merge any more, so the text has to send the merger back to the Actions tab.
echo "Review and merge ${PR_URL}, then start Auto Release again from the Actions tab to publish ${NEXT_VERSION}."
echo "Start it right after merging, so nothing lands on master between the merge and the tag."
