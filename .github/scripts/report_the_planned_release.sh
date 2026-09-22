#!/usr/bin/env bash
# Prints what a dry run would have released, so the run says something useful without writing anything.
set -euo pipefail

for name in BUMP NEXT_VERSION; do
  [ -n "${!name+x}" ] || { echo "Missing required environment variable: $name" >&2; exit 1; }
done
echo "Dry run. No branch, commit, pull request, merge, tag or release was created."
echo "It would release ${NEXT_VERSION} as a ${BUMP} bump, with the entries printed above."
