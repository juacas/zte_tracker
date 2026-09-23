#!/usr/bin/env bash
# Writes the version and the changelog to the run summary page, on every run, whatever the outcome.
set -euo pipefail

: "${GITHUB_STEP_SUMMARY:?Missing required environment variable: GITHUB_STEP_SUMMARY}"

dry_run="${DRY_RUN:-}"
planned_version="${PLANNED_VERSION:-}"
tag_name="${TAG_NAME:-}"
tag_state="${TAG_STATE:-}"
target_sha="${TARGET_SHA:-}"
manifest_version="${MANIFEST_VERSION:-}"
prerelease="${PRERELEASE:-}"
tag_message="${TAG_MESSAGE:-}"
pr_url="${PR_URL:-}"
publish_result="${PUBLISH_RESULT:-}"

# A dry run reports what it would have released; a real run reports what it did release.
version="$planned_version"
if [ "$dry_run" != "true" ] && [ -n "$tag_name" ]; then
  version="$tag_name"
fi

case "$dry_run:$publish_result" in
  true:*)      outcome="Dry run. Nothing was tagged, released or written." ;;
  *:success)   outcome="Released." ;;
  *:skipped)   outcome="Nothing to publish. The version on master is already released." ;;
  *:failure)   outcome="The publish step failed. No release was produced." ;;
  *:cancelled) outcome="The run was cancelled." ;;
  *)           outcome="The run stopped before publishing." ;;
esac

{
  printf '## Release summary\n\n'
  printf '| | |\n|---|---|\n'
  printf '| Version | %s |\n' "${version:-none, this run does not bump a version}"
  printf '| Outcome | %s |\n' "$outcome"
  if [ -n "$manifest_version" ]; then printf '| Version on master | %s |\n' "$manifest_version"; fi
  if [ -n "$tag_name" ]; then printf '| Tag | %s (%s) |\n' "$tag_name" "${tag_state:-unknown}"; fi
  if [ -n "$target_sha" ]; then printf '| Target commit | `%s` |\n' "${target_sha:0:12}"; fi
  if [ "$prerelease" = "true" ]; then printf '| Prerelease | yes |\n'; fi
  if [ -n "$pr_url" ]; then printf '| Release pull request | %s |\n' "$pr_url"; fi
  printf '\n### Changelog\n\n'
  if [ -n "$tag_message" ]; then
    printf '%s\n' "$tag_message" | tr ';' '\n' | sed 's/^ *//; s/^./- &/'
  else
    printf 'No changelog was produced for this run.\n'
  fi
} >> "$GITHUB_STEP_SUMMARY"
