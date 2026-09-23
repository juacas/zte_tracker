#!/usr/bin/env bash
# Finds a release pull request an earlier run left open, so a retry acts on it instead of opening a second one.
# Env: GH_TOKEN, GITHUB_OUTPUT, GITHUB_REPOSITORY
# Outputs: pr_number, pr_url, version, branch, base_sha
set -euo pipefail

for name in GH_TOKEN GITHUB_OUTPUT GITHUB_REPOSITORY; do
  [ -n "${!name+x}" ] || { echo "Missing required environment variable: $name" >&2; exit 1; }
done

open=$(gh api "repos/${GITHUB_REPOSITORY}/pulls?state=open&base=master&per_page=100" \
  --jq '.[] | select(.head.ref | startswith("chore/release-"))
        | [(.number | tostring), .html_url, .title, .head.ref, .base.sha] | @tsv')

count=$(printf '%s' "$open" | grep -c . || true)
if [ "$count" -eq 0 ]; then
  echo "No release pull request is open, so this run prepares one."
  {
    printf 'pr_number=\n'; printf 'pr_url=\n'; printf 'version=\n'
    printf 'branch=\n'; printf 'base_sha=\n'
  } >> "$GITHUB_OUTPUT"
  exit 0
fi
if [ "$count" -gt 1 ]; then
  echo "More than one release pull request is open, so this run cannot tell which one to finish:" >&2
  printf '%s\n' "$open" >&2
  echo "Close the ones you do not want, then start this workflow again." >&2
  exit 1
fi

IFS=$'\t' read -r number url title branch base_sha <<<"$open"
version=${title##*: }
case "$version" in
  v[0-9]*) ;;
  *) echo "Cannot read a version out of the pull request title: $title" >&2; exit 1 ;;
esac
echo "${url} is already open for ${version}, so this run finishes it instead of opening another."
{
  printf 'pr_number=%s\n' "$number"
  printf 'pr_url=%s\n' "$url"
  printf 'version=%s\n' "$version"
  printf 'branch=%s\n' "$branch"
  printf 'base_sha=%s\n' "$base_sha"
} >> "$GITHUB_OUTPUT"
