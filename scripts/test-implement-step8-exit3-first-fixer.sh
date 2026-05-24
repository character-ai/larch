#!/usr/bin/env bash
# Offline structural checks for /implement Step 8+ Exit 3 first-fixer-non-health
# autonomous path (sentinel, counter, gates) documented in skills/implement/SKILL.md.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SKILL_MD="$REPO_ROOT/skills/implement/SKILL.md"

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

[[ -f "$SKILL_MD" ]] || fail "SKILL.md missing"

grep -Fq 'main-agent-ci-fix-' "$SKILL_MD" || fail "SKILL must reference main-agent-ci-fix sentinel prefix"
grep -Fq 'main-agent-ci-fix.count' "$SKILL_MD" || fail "SKILL must reference main-agent-ci-fix counter path"
grep -Fq 'FORKED_TARGET' "$SKILL_MD" || fail "SKILL must gate on FORKED_TARGET"
grep -Fq 'REPO_UNAVAILABLE' "$SKILL_MD" || fail "SKILL must gate on REPO_UNAVAILABLE"
grep -Fq 'BAIL_FAILURE_DETAIL_LOG' "$SKILL_MD" || fail "SKILL must reference BAIL_FAILURE_DETAIL_LOG redaction gate"
grep -Fq 'FAILED_RUN_ID' "$SKILL_MD" || fail "SKILL must reference FAILED_RUN_ID for autonomous path"

awk '
  /## Step 8\+/ { in8 = 1; next }
  in8 && /^## / { in8 = 0 }
  in8 && /\*\*Exit 3\*\*/ { in3 = 1 }
  in3 && /^- \*\*Exit [0-9]/ && !/\*\*Exit 3\*\*/ { in3 = 0 }
  in3 {
    if ($0 ~ /main-agent-ci-fix\.count/) ccap = 1
    if ($0 ~ /Tool Failures/) tfail = 1
    if ($0 ~ /git add -- <paths>/) gadd = 1
    if ($0 ~ /git-commit\.sh.*Fix CI failure \(main-agent\)/) gcommit = 1
    if ($0 ~ /refresh-run-logs\.sh/) refresh = 1
    if ($0 ~ /git-push\.sh/) push = 1
  }
  END {
    if (!(ccap && tfail && gadd && gcommit && refresh && push)) exit 1
  }
' "$SKILL_MD" || fail "Step 8+ Exit 3 block missing sentinel/counter, tool-failure, git, refresh, or push prose"

printf 'PASS: test-implement-step8-exit3-first-fixer.sh\n'
