#!/usr/bin/env bash
# Runtime regression: ship-pr pr-prep advances to pr-create without OOS gating (#3650).
# After the OOS decoupling, run_pr_prep_phase builds the PR body and advances directly
# to pr-create; no OOS_PENDING state is written and no security-sidecar check runs here.
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

if CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
  "$SHIP_PR" \
    --state-file "$state" \
    --implement-tmpdir "$TMPROOT" \
    --merge false \
    --draft false \
    --forked false \
    --repo owner/repo \
    --no-admin-fallback true \
    --no-logs-commit true \
    >/dev/null 2>&1; then
  :
else
  :
fi

# After pr-prep, ship-pr advances to pr-create (which may fail in the test env
# when create-pr.sh or git operations are unavailable; any exit code is acceptable
# as long as pr-prep itself did not stall at 9a1 — verify phase advanced past pr-prep).
phase=$(awk -F= '$1=="PHASE"{print $2; exit}' "$state")
[[ "$phase" != "pr-prep" ]] \
  || fail "ship-pr pr-prep must advance PHASE beyond pr-prep to pr-create or later (got pr-prep)"

# OOS_PENDING must not be written by pr-prep (#3650 decoupling).
if grep -q 'OOS_PENDING=' "$state" 2>/dev/null; then
  fail "ship-pr pr-prep must not write OOS_PENDING after #3650 decoupling (found: $(grep 'OOS_PENDING=' "$state"))"
fi

# Structural: ship-pr.sh must not reference OOS at all.
SHIP_PR_SH="$REPO_ROOT/scripts/ship-pr.sh"
if grep -qi 'oos' "$SHIP_PR_SH" 2>/dev/null; then
  fail "ship-pr.sh must have no OOS references after #3650 decoupling"
fi

echo "PASS: test-ship-pr-oos-pr-prep.sh"
