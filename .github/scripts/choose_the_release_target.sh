#!/usr/bin/env bash
# Decides what commit to release and under what tag, and refuses to move an existing tag or go backwards.
# Outputs: changelog_version, dry_run, manifest_version, prerelease, should_publish, should_tag, tag_name, tag_state, target_sha
set -euo pipefail

for name in DRY_RUN GH_TOKEN GITHUB_OUTPUT GITHUB_REPOSITORY MODE PREPARED_SHA TARGET_SHA_INPUT; do
  [ -n "${!name+x}" ] || { echo "Missing required environment variable: $name" >&2; exit 1; }
done
case "$MODE" in
  stable|rc) ;;
  *) echo "Unsupported release mode: $MODE" >&2; exit 1 ;;
esac
case "$DRY_RUN" in true|false) ;; *) echo "Invalid dry_run value: $DRY_RUN" >&2; exit 1 ;; esac

git fetch --force --tags origin refs/heads/master:refs/remotes/origin/master
# A draft release is invisible to HACS, so only a published one counts as released.
release_exists() {
  [ "$(gh release view "$1" --repo "$GITHUB_REPOSITORY" --json isDraft --jq .isDraft 2>/dev/null)" = "false" ]
}
if [ -n "$TARGET_SHA_INPUT" ]; then
  if [[ ! "$TARGET_SHA_INPUT" =~ ^[0-9a-fA-F]{7,40}$ ]]; then
    echo "target_sha must be a commit SHA." >&2
    exit 1
  fi
  TARGET_SHA=$(git rev-parse --verify --quiet "${TARGET_SHA_INPUT}^{commit}") || {
    echo "target_sha does not resolve to a commit." >&2
    exit 1
  }
elif [ -n "$PREPARED_SHA" ]; then
  # The commit prepare just merged, so the release cannot drift onto a newer master.
  for attempt in 1 2 3; do
    git rev-parse --verify --quiet "${PREPARED_SHA}^{commit}" >/dev/null && break
    sleep $((attempt * 5))
    git fetch --force --tags origin refs/heads/master:refs/remotes/origin/master
  done
  TARGET_SHA=$(git rev-parse --verify --quiet "${PREPARED_SHA}^{commit}") || {
    echo "The commit prepared by this run is not visible on master." >&2
    exit 1
  }
else
  TARGET_SHA=$(git rev-parse refs/remotes/origin/master)
fi
TARGET_SHA=$(git rev-parse "$TARGET_SHA^{commit}")
if ! git merge-base --is-ancestor "$TARGET_SHA" refs/remotes/origin/master; then
  echo "target_sha must be reachable from master." >&2
  exit 1
fi
# Never check out the target: this script may not exist at that commit.
MANIFEST_VERSION=$(git show "${TARGET_SHA}:custom_components/zte_tracker/manifest.json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["version"])')
if [[ ! "$MANIFEST_VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Malformed manifest version: $MANIFEST_VERSION" >&2
  exit 1
fi

PRERELEASE=false
CHANGELOG_VERSION="$MANIFEST_VERSION"
if [ "$MODE" = "rc" ]; then
  PRERELEASE=true
  VERSION_BODY=${MANIFEST_VERSION#v}
  IFS=. read -r MAJOR MINOR PATCH <<EOF_VERSION
$VERSION_BODY
EOF_VERSION
  NEXT_PATCH=$((PATCH + 1))
  CHANGELOG_VERSION="v${MAJOR}.${MINOR}.${NEXT_PATCH}"
  RC_PREFIX="${CHANGELOG_VERSION}-rc"
  EXISTING_COUNT=$(git for-each-ref --format='%(refname:strip=2)' "refs/tags/${RC_PREFIX}.*" | grep -Ec "^${RC_PREFIX//./\\.}\\.[0-9]+$" || true)
  LAST_RC_NUMBER=$(git for-each-ref --format='%(refname:strip=2)' "refs/tags/${RC_PREFIX}.*" | sed -nE "s/^${RC_PREFIX//./\\.}\\.([0-9]+)$/\\1/p" | sort -n | tail -n1)
  TAG_NAME="${RC_PREFIX}.$((${LAST_RC_NUMBER:-0} + 1))"
  # HACS only looks at the newest 30 releases, so a long rc run can bury the last stable one.
  if [ "$EXISTING_COUNT" -ge 25 ]; then
    echo "Refusing another RC: publish a stable release before approaching HACS's 30-release window." >&2
    exit 1
  fi
else
  TAG_NAME="$MANIFEST_VERSION"
fi

# Gate every stable run, including a republish of an existing tag, or an older version can be made Latest.
if [ "$MODE" = "stable" ]; then
  HIGHEST_STABLE=$(git tag --list | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | grep -vxF "$TAG_NAME" | sort -V | tail -n1 || true)
  if [ -n "$HIGHEST_STABLE" ]; then
    HIGHEST_OR_NEW=$(printf '%s\n%s\n' "$HIGHEST_STABLE" "$TAG_NAME" | sort -V | tail -n1)
    if [ "$HIGHEST_OR_NEW" != "$TAG_NAME" ]; then
      echo "Stable version $TAG_NAME must be newer than $HIGHEST_STABLE." >&2
      exit 1
    fi
  fi
fi

if git rev-parse --verify --quiet "refs/tags/${TAG_NAME}" >/dev/null; then
  SHOULD_TAG=false
  TAG_COMMIT=$(git rev-list -n 1 "$TAG_NAME")
  if [ "$TAG_COMMIT" = "$TARGET_SHA" ]; then
    if release_exists "$TAG_NAME"; then
      echo "Tag already points at this commit and its release is published, nothing to do."
      SHOULD_PUBLISH=false
      TAG_STATE=already-here
    else
      echo "Tag $TAG_NAME exists at this commit but no release was published. Resuming publication."
      SHOULD_PUBLISH=true
      TAG_STATE=orphan-tag
    fi
  elif git merge-base --is-ancestor "$TAG_COMMIT" "$TARGET_SHA"; then
    if release_exists "$TAG_NAME"; then
      echo "Version $TAG_NAME was already released at $TAG_COMMIT. Bump the manifest to release again."
      SHOULD_PUBLISH=false
      TAG_STATE=already-released
    else
      echo "Tag $TAG_NAME exists at $TAG_COMMIT but no release was published. Resuming publication."
      SHOULD_PUBLISH=true
      TAG_STATE=orphan-tag
      # Validate and publish the tagged tree, not master's newer head.
      TARGET_SHA="$TAG_COMMIT"
      TAG_MANIFEST=$(git show "${TARGET_SHA}:custom_components/zte_tracker/manifest.json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["version"])')
      # An rc tag name never equals the manifest version, so only stable can be checked this way.
      if [ "$MODE" = "stable" ] && [ "$TAG_MANIFEST" != "$TAG_NAME" ]; then
        echo "Tag $TAG_NAME sits on a tree whose manifest says $TAG_MANIFEST. Refusing." >&2
        exit 1
      fi
    fi
  else
    echo "Tag $TAG_NAME points at $TAG_COMMIT, which is not an ancestor of $TARGET_SHA" >&2
    exit 1
  fi
else
  SHOULD_TAG=true
  SHOULD_PUBLISH=true
  TAG_STATE=missing
fi

{
  printf 'tag_name=%s\n' "$TAG_NAME"
  printf 'changelog_version=%s\n' "$CHANGELOG_VERSION"
  printf 'manifest_version=%s\n' "$MANIFEST_VERSION"
  printf 'prerelease=%s\n' "$PRERELEASE"
  printf 'dry_run=%s\n' "$DRY_RUN"
  printf 'should_tag=%s\n' "$SHOULD_TAG"
  printf 'should_publish=%s\n' "$SHOULD_PUBLISH"
  printf 'tag_state=%s\n' "$TAG_STATE"
  printf 'target_sha=%s\n' "$TARGET_SHA"
} >> "$GITHUB_OUTPUT"
