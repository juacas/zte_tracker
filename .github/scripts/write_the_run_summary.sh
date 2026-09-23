#!/usr/bin/env bash
# Writes the version and the changelog to the run summary page, on every run, whatever the outcome.
set -euo pipefail

: "${GITHUB_STEP_SUMMARY:?Missing required environment variable: GITHUB_STEP_SUMMARY}"

dry_run="${DRY_RUN:-}"
planned_version="${PLANNED_VERSION:-}"
tag_name="${TAG_NAME:-}"
target_sha="${TARGET_SHA:-}"
manifest_version="${MANIFEST_VERSION:-}"
prerelease="${PRERELEASE:-}"
tag_message="${TAG_MESSAGE:-}"
changelog_entries="${CHANGELOG_ENTRIES:-}"
pr_url="${PR_URL:-}"
publish_result="${PUBLISH_RESULT:-}"

case "$dry_run:$publish_result" in
  true:*)      outcome="Dry run. Nothing was tagged, released or written." ;;
  *:success)   outcome="Released." ;;
  *:skipped)   outcome="Nothing to publish. The version on master is already released." ;;
  *:failure)   outcome="The publish step failed. No release was produced." ;;
  *:cancelled) outcome="The run was cancelled." ;;
  *)           outcome="The run stopped before publishing." ;;
esac

{
  printf '| | |\n|---|---|\n'
  if [ "$dry_run" = "true" ]; then
    printf '| Would release | %s |\n' "${planned_version:-nothing, this run does not bump a version}"
    printf '| Current version | %s |\n' "${manifest_version:-unknown}"
  else
    printf '| Version | %s |\n' "${tag_name:-none, this run does not bump a version}"
  fi
  printf '| Outcome | %s |\n' "$outcome"
  if [ -n "$target_sha" ]; then printf '| Commit | `%s` |\n' "${target_sha:0:12}"; fi
  if [ "$prerelease" = "true" ]; then printf '| Prerelease | yes |\n'; fi
  if [ -n "$pr_url" ]; then printf '| Release pull request | %s |\n' "$pr_url"; fi
  printf '\n## Changelog\n\n'
  if [ -n "$changelog_entries" ]; then
    printf '%s\n' "$changelog_entries"
  elif [ -n "$tag_message" ]; then
    printf '%s\n' "$tag_message" | tr ';' '\n' | sed 's/^ *//; s/^./- &/'
  else
    printf 'No changelog was produced for this run.\n'
  fi
} >> "$GITHUB_STEP_SUMMARY"
