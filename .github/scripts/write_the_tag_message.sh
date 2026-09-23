#!/usr/bin/env bash
# Builds the annotated tag message and release body from the changelog section.
# Outputs: tag_message, changelog_entries
set -euo pipefail

for name in CHANGELOG_VERSION DRY_RUN GH_TOKEN GITHUB_OUTPUT GITHUB_REPOSITORY; do
  [ -n "${!name+x}" ] || { echo "Missing required environment variable: $name" >&2; exit 1; }
done
# Highest stable tag reachable, by version order: creation date ties can pick the wrong base.
LAST_STABLE_TAG=$(git for-each-ref --merged HEAD --format='%(refname:strip=2)' refs/tags | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | sort -V | tail -n1 || true)
if [ -n "$LAST_STABLE_TAG" ]; then
  RANGE="${LAST_STABLE_TAG}..HEAD"
else
  RANGE="HEAD"
fi

entries="${RUNNER_TEMP:-$PWD}/release-entries.md"
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
# One pull request usually holds several commits, and the API names it for every one of them.
awk '!seen[$0]++' "$entries" > "$entries.unique" && mv "$entries.unique" "$entries"
# The commit that bumped the manifest is part of this release, not a change worth listing in it.
sed -i '/^- chore(release): /d' "$entries"

if [ ! -s "$entries" ]; then
  printf -- '- No changes since last release\n' > "$entries"
fi

python3 - "$entries" <<'PY' >> "$GITHUB_OUTPUT"
import sys
import uuid
from pathlib import Path

entries = [line.removeprefix("- ").strip() for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines() if line.strip()]
visible = entries[:3]
extra = len(entries) - len(visible)
message = "; ".join(visible)
if extra:
    message = f"{message}; and {extra} more"
delimiter = f"EOF_TAG_MESSAGE_{uuid.uuid4().hex}"
print(f"tag_message<<{delimiter}")
print(message)
print(delimiter)
# The tag message is capped for readability; the run summary shows every entry.
delimiter = f"EOF_ENTRIES_{uuid.uuid4().hex}"
print(f"changelog_entries<<{delimiter}")
for entry in entries:
    print(f"- {entry}")
print(delimiter)
PY
