#!/usr/bin/env bash
# Picks the next version from the bump input, or infers it from conventional commit subjects since the last stable tag.
# Outputs: base_version, bump, commit_count, next_version, should_prepare
set -euo pipefail

for name in BUMP_INPUT GH_TOKEN RELEASE_NOTES GITHUB_OUTPUT GITHUB_REPOSITORY; do
  [ -n "${!name+x}" ] || { echo "Missing required environment variable: $name" >&2; exit 1; }
done
case "$BUMP_INPUT" in
  auto|patch|minor|major) ;;
  *) echo "Unsupported bump: $BUMP_INPUT" >&2; exit 1 ;;
esac

git fetch --force --tags origin refs/heads/master:refs/remotes/origin/master

# Scratch files belong in the runner temp dir, never in the tree a pull request is built from.
SCRATCH="${RUNNER_TEMP:-$PWD}"
export RELEASE_COMMITS="$SCRATCH/release-commits.txt"
export RELEASE_ENTRIES="$SCRATCH/release-entries.md"

# Never detach here: it would swap the file this shell is still reading.
MANIFEST_VERSION=$(python3 - <<'PY'
import json
from pathlib import Path

manifest = Path("custom_components/zte_tracker/manifest.json")
print(json.loads(manifest.read_text(encoding="utf-8"))["version"])
PY
)
if [[ ! "$MANIFEST_VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Malformed manifest version: $MANIFEST_VERSION" >&2
  exit 1
fi

# Highest stable tag reachable from master, by version order: two tags can share a creation second.
LAST_STABLE_TAG=$(git for-each-ref --merged HEAD --format='%(refname:strip=2)' refs/tags | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | sort -V | tail -n1 || true)
if [ -n "$LAST_STABLE_TAG" ] && [ "$LAST_STABLE_TAG" != "$MANIFEST_VERSION" ]; then
  echo "master already carries unreleased $MANIFEST_VERSION over tag $LAST_STABLE_TAG. Publishing that instead of bumping."
  printf 'should_prepare=false\n' >> "$GITHUB_OUTPUT"
  exit 0
fi

if [ -n "$LAST_STABLE_TAG" ]; then
  RANGE="${LAST_STABLE_TAG}..HEAD"
else
  RANGE="HEAD"
fi
COMMIT_COUNT=$(git rev-list --count "$RANGE")
if [ "$COMMIT_COUNT" -eq 0 ]; then
  echo "No commits since $LAST_STABLE_TAG. Nothing to release."
  printf 'should_prepare=false\n' >> "$GITHUB_OUTPUT"
  exit 0
fi

git log --reverse --format='%H%x1f%s%x1f%b%x1e' "$RANGE" > "$RELEASE_COMMITS"
BUMP=$BUMP_INPUT
if [ "$BUMP" = auto ]; then
  BUMP=$(python3 - <<'PY'
import os
import re
from pathlib import Path

BREAKING_SUBJECT = re.compile(r"^[a-z]+(\(.+\))?!:")

bump = "patch"
for record in Path(os.environ["RELEASE_COMMITS"]).read_text(encoding="utf-8").split("\x1e"):
    if not record.strip():
        continue
    fields = (record.strip("\n").split("\x1f") + ["", "", ""])[:3]
    subject, body = fields[1], fields[2]
    if BREAKING_SUBJECT.match(subject) or "BREAKING CHANGE" in body:
        bump = "major"
        break
    # An unclassifiable subject counts as a patch. That is what the bump input is for.
    if subject.startswith("feat") and bump == "patch":
        bump = "minor"
print(bump)
PY
)
fi

NEXT_VERSION=$(python3 - "$MANIFEST_VERSION" "$BUMP" <<'PY'
import sys

major, minor, patch = (int(part) for part in sys.argv[1].lstrip("v").split("."))
bump = sys.argv[2]
if bump == "major":
    major, minor, patch = major + 1, 0, 0
elif bump == "minor":
    minor, patch = minor + 1, 0
else:
    patch += 1
print(f"v{major}.{minor}.{patch}")
PY
)

# Same commit to pull request mapping the changelog job uses, so both dialects stay identical.
entries="$RELEASE_ENTRIES"
: > "$entries"
while IFS= read -r sha; do
  for attempt in 1 2 3; do
    if pulls_json=$(gh api -H "Accept: application/vnd.github+json" "repos/${GITHUB_REPOSITORY}/commits/${sha}/pulls"); then
      break
    fi
    if [ "$attempt" -eq 3 ]; then
      echo "Unable to resolve PR metadata for $sha." >&2
      exit 1
    fi
    sleep $((attempt * 3))
  done
  pr_line=$(PULLS_JSON="$pulls_json" python3 - <<'PY'
import json
import os

pulls = json.loads(os.environ["PULLS_JSON"])

def rank(pull):
    merged = pull.get("merged_at") is not None
    to_master = (pull.get("base") or {}).get("ref") == "master"
    return (merged and to_master, merged, pull.get("number") or 0)

if pulls:
    best = sorted(pulls, key=rank, reverse=True)[0]
    print(f"{best['title']}\t{best['number']}")
PY
)
  if [ -n "$pr_line" ]; then
    title=${pr_line%$'\t'*}
    number=${pr_line##*$'\t'}
    printf -- '- %s (#%s)\n' "$title" "$number" >> "$entries"
  else
    subject=$(git log -1 --pretty=%s "$sha")
    short_sha=$(git rev-parse --short "$sha")
    printf -- '- %s (%s)\n' "$subject" "$short_sha" >> "$entries"
  fi
done < <(git rev-list --reverse "$RANGE")
if [ ! -s "$entries" ]; then
  printf -- '- No changes since last release\n' > "$entries"
fi
{
  printf 'Planned release: %s -> %s (%s bump over %s commit(s) in %s)\n' "$MANIFEST_VERSION" "$NEXT_VERSION" "$BUMP" "$COMMIT_COUNT" "$RANGE"
  if [ -n "$RELEASE_NOTES" ]; then
    printf '\n%s\n' "$RELEASE_NOTES"
  fi
  printf '\n'
  cat "$entries"
}
{
  printf 'should_prepare=true\n'
  printf 'next_version=%s\n' "$NEXT_VERSION"
  printf 'bump=%s\n' "$BUMP"
  printf 'base_version=%s\n' "$MANIFEST_VERSION"
  printf 'commit_count=%s\n' "$COMMIT_COUNT"
} >> "$GITHUB_OUTPUT"
