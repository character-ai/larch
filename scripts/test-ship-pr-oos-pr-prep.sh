#!/usr/bin/env bash
# Runtime regression: ship-pr pr-prep materialize failure with manifest OOS forces OOS_PENDING.
set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
SHIP_PR="$REPO_ROOT/scripts/ship-pr.sh"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[[ -f "$SHIP_PR" ]] || fail "scripts/ship-pr.sh missing: $SHIP_PR"

TMPROOT=$(mktemp -d "${TMPDIR:-/tmp}/test-ship-pr-oos-pr-prep.XXXXXX")
trap 'rm -rf "$TMPROOT"' EXIT

MANIFEST="$TMPROOT/manifest.json"
cat >"$MANIFEST" <<'JSON'
{
  "schema_version": "1",
  "status": "complete",
  "summary_bullets": ["summary"],
  "oos_observations": [{"title": "OOS", "description": "needs filing", "phase": "implement"}]
}
JSON

state="$TMPROOT/ship-pr-state.sh"
cat >"$state" <<EOF
PHASE=pr-prep
BRANCH_NAME=feature/test-ship-pr-oos
ISSUE_NUMBER=1
RUN_ID=test-ship-pr-oos-pr-prep
REPO=owner/repo
REPO_UNAVAILABLE=false
FORKED_TARGET=false
MERGE=false
DRAFT=false
DEFERRED=false
PR_CLOSED=false
DONE_RENAME_APPLIED=false
STALL_TRACKING=false
STALL_STEP=
BAIL_NEEDS_USER_INPUT=false
BAIL_REASON=
BAIL_FAILURE_DETAIL_LOG=
CI_PASSED=false
OOS_PENDING=false
PR_NUMBER=
PR_URL=
PR_TITLE=
RESUME_PHASE=
CALLER_KIND=
REBASE_COUNT=0
FIX_ATTEMPTS=0
ITERATION=0
TRANSIENT_RETRIES=0
FAILED_RUN_ID=
MANIFEST_PATH=$MANIFEST
TOOL_LABEL=codex
DESIGN_ONLY_DONE=false
EXPECTED_SESSION_ID=
EXPECTED_TMPDIR_BASENAME_PREFIX=claude-implement-test_
NO_LOGS_COMMIT=false
IMPLEMENT_TMPDIR=$TMPROOT
CI_FIX_REBASE_PENDING=false
EOF

: >"$TMPROOT/execution-issues.md"

set +e
LARCH_TEST_MATERIALIZE_FORCE_FAIL=true \
  CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
  "$SHIP_PR" \
    --state-file "$state" \
    --implement-tmpdir "$TMPROOT" \
    --merge false \
    --draft false \
    --forked false \
    --repo owner/repo \
    --no-admin-fallback true \
    --no-logs-commit true \
    >/dev/null 2>&1
rc=$?
set -e

[[ "$rc" -eq 0 ]] || fail "ship-pr must exit 0 after pr-prep OOS handoff (got rc=$rc)"
grep -Fq 'OOS_PENDING=true' "$state" \
  || fail "ship-pr pr-prep must set OOS_PENDING=true when materialize fails with manifest OOS"
if grep -Fq 'PHASE=pr-prep' "$state" || grep -Fq 'PHASE=pr-create' "$state"; then
  :
else
  fail "ship-pr must leave PHASE at pr-prep or pr-create when OOS_PENDING blocks PR creation"
fi
fail_glob=$(find "$TMPROOT" -maxdepth 1 -name 'ship-pr-fail-pr-prep-*' -type f 2>/dev/null | head -n 1)
[[ -n "$fail_glob" ]] \
  || fail "pr-prep must capture materialize failure output for operator review"

SHIP_PR_SH="$REPO_ROOT/scripts/ship-pr.sh"
grep -Fq 'security-oos-observations.md' "$SHIP_PR_SH" \
  || fail "ship-pr.sh must block pr-prep on non-empty security-oos-observations.md"
grep -Fq 'security-routed manifest OOS requires private SECURITY.md disposition' "$SHIP_PR_SH" \
  || fail "ship-pr.sh must refuse clearing OOS_PENDING while security sidecar remains"

echo "PASS: test-ship-pr-oos-pr-prep.sh"
