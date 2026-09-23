#!/usr/bin/env bash
# Prints the resolved plan to the job summary. Writes nothing.
set -euo pipefail

for name in CHANGELOG_VERSION MANIFEST_VERSION PRERELEASE SHOULD_PUBLISH SHOULD_TAG TAG_MESSAGE TAG_NAME TAG_STATE TARGET_SHA; do
  [ -n "${!name+x}" ] || { echo "Missing required environment variable: $name" >&2; exit 1; }
done
make_latest=true
if [ "$PRERELEASE" = "true" ]; then
  make_latest=false
fi
{
  printf 'Dry run only. No tag, release, asset, or repository write was created.\n'
  printf 'target_sha=%s\n' "$TARGET_SHA"
  printf 'manifest_version=%s\n' "$MANIFEST_VERSION"
  printf 'changelog_version=%s\n' "$CHANGELOG_VERSION"
  printf 'tag_name=%s\n' "$TAG_NAME"
  printf 'tag_state=%s\n' "$TAG_STATE"
  printf 'should_tag=%s\n' "$SHOULD_TAG"
  printf 'should_publish=%s\n' "$SHOULD_PUBLISH"
  printf 'prerelease=%s\n' "$PRERELEASE"
  printf 'draft=false\n'
  printf 'release_name=ZTE_TRACKER_%s\n' "$TAG_NAME"
  printf 'make_latest=%s\n' "$make_latest"
  printf 'tag_message=%s\n' "$TAG_MESSAGE"
}
