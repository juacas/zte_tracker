#!/usr/bin/env bash
# Fails the run before anything is written if the repository settings forbid an unattended merge.
set -euo pipefail

for name in AUTO_MERGE GH_TOKEN GITHUB_REPOSITORY; do
  [ -n "${!name+x}" ] || { echo "Missing required environment variable: $name" >&2; exit 1; }
done
# Scratch files belong in the runner temp dir, never in the tree a pull request is built from.
export SCRATCH="${RUNNER_TEMP:-$PWD}"
SETTING_PR='Enable Settings > Actions > General > Workflow permissions > Allow GitHub Actions to create and approve pull requests.'

# GITHUB_TOKEN can never bypass a ruleset, so a pull request is the only route to master.
if [ "$AUTO_MERGE" != "true" ]; then
  echo "auto_merge is off, so you merge the release pull request yourself and the branch rules are left to you."
elif rules_json=$(gh api "repos/${GITHUB_REPOSITORY}/rules/branches/master" 2>/dev/null); then
  printf '%s' "$rules_json" > "$SCRATCH/branch-rules.json"
  python3 - "$SCRATCH/branch-rules.json" <<'PY'
import json
import sys
from pathlib import Path

rules = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
problems = []
for rule in rules:
    if rule.get("type") != "pull_request":
        continue
    parameters = rule.get("parameters") or {}
    count = parameters.get("required_approving_review_count") or 0
    if count:
        problems.append(
            f"The master ruleset requires {count} approving review(s), which the pipeline cannot give itself.\n"
            "  Set the required approvals to 0, or merge the release pull request by hand."
        )
    if parameters.get("required_review_thread_resolution"):
        problems.append("The master ruleset requires review thread resolution, which blocks an unattended merge.")
checks = [rule for rule in rules if rule.get("type") == "required_status_checks"]
if checks:
    problems.append(
        "The master ruleset has required status checks. They must all pass before the pipeline can merge,\n"
        "  and repository auto-merge is disabled, so the merge would be refused."
    )
if problems:
    print("Cannot run an unattended release:", file=sys.stderr)
    for problem in problems:
        print("- " + problem, file=sys.stderr)
    raise SystemExit(1)
print("Branch ruleset allows the pipeline to merge its own pull request.")
PY
else
  echo "Could not read the master branch rules. Continuing, and any rule that blocks the merge will be reported there."
fi

# Admin scope, which GITHUB_TOKEN does not have, so a failure here is not a verdict.
if permissions_json=$(gh api "repos/${GITHUB_REPOSITORY}/actions/permissions/workflow" 2>/dev/null); then
  if [ "$(printf '%s' "$permissions_json" | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin).get("can_approve_pull_request_reviews", True)))')" = "false" ]; then
    echo "Actions is not allowed to create pull requests, and this pipeline needs to open one." >&2
    echo "  $SETTING_PR" >&2
    exit 1
  fi
  echo "Actions is allowed to create pull requests."
else
  echo "Could not read the Actions workflow permissions, which needs admin scope. If the pull request cannot be opened:"
  echo "  $SETTING_PR"
fi
