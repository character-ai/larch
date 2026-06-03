#!/usr/bin/env bash
# Offline regression for ship-pr.sh CI-fix rebase path (Phase 1 #3364).
# Structural pins plus a sandbox guard for ship-pr-rrr-phase14 resume handoff.
# shellcheck disable=SC2016
set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
SHIP_PR="$REPO_ROOT/scripts/ship-pr.sh"

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

[[ -f "$SHIP_PR" ]] || fail "scripts/ship-pr.sh missing: $SHIP_PR"

# ---------------------------------------------------------------------------
# (A) ci-behind-count → run_rebase_rebump defer-push before CI-fix push.
# ---------------------------------------------------------------------------
grep -Fq 'run_rebase_rebump "$phase" defer-push' "$SHIP_PR" \
    || fail "(A) ship-pr.sh must call run_rebase_rebump with defer-push when behind main"
grep -Fq 'ci-behind-count.sh' "$SHIP_PR" \
    || fail "(A) ship-pr.sh must consult ci-behind-count.sh before defer-rebase"
grep -Fq 'if [ "$behind" -gt 0 ]; then' "$SHIP_PR" \
    || fail "(A) ship-pr.sh must defer-rebase only when BEHIND_COUNT > 0 (concurrency acceptance pin)"

# ---------------------------------------------------------------------------
# (B) run_rebase_rebump uses rebase-push --no-push --keep-on-conflict.
# ---------------------------------------------------------------------------
grep -Fq 'rebase-push.sh" --no-push --keep-on-conflict' "$SHIP_PR" \
    || fail "(B) run_rebase_rebump must invoke rebase-push.sh --no-push --keep-on-conflict"

# ---------------------------------------------------------------------------
# (C) Phase 1–4 handoff tokens for non-bump CI-fix conflicts.
# ---------------------------------------------------------------------------
grep -Fq 'RESUME_PHASE ship-pr-rrr-phase14' "$SHIP_PR" \
    || fail "(C) missing RESUME_PHASE ship-pr-rrr-phase14 state_set"
grep -Fq 'CALLER_KIND ship_pr_pre_push' "$SHIP_PR" \
    || fail "(C) missing CALLER_KIND ship_pr_pre_push state_set"
grep -Fq 'emit_kv CONFLICT_FILES' "$SHIP_PR" \
    || fail "(C) missing CONFLICT_FILES emit_kv on conflict stall"
grep -Fq 'ship-pr-rrr-after-phase14.flag' "$SHIP_PR" \
    || fail "(C) missing ship-pr-rrr-after-phase14.flag handoff token"

# ---------------------------------------------------------------------------
# (D) Phase 1: no per-PR bump drop/rebump inside ship-pr.sh.
# ---------------------------------------------------------------------------
grep -Fq 'drop-bump-commit' "$SHIP_PR" \
    && fail "(D) ship-pr.sh must not reference drop-bump-commit after Phase 1"
grep -Fq 'classify-bump.sh' "$SHIP_PR" \
    && fail "(D) ship-pr.sh must not reference classify-bump.sh after Phase 1"

# ---------------------------------------------------------------------------
# (D2) Fork carve-out in implement-finalize postbump branch validation.
# ---------------------------------------------------------------------------
FINALIZE="$REPO_ROOT/scripts/implement-finalize.sh"
grep -Fq 'FORKED_TARGET' "$FINALIZE" \
    || fail "(D2) implement-finalize.sh must reference FORKED_TARGET in postbump branch guard"
grep -Fq 'main|master)' "$FINALIZE" \
    || fail "(D2) implement-finalize.sh must guard main/master branch names"
grep -Fq 'forked' "$FINALIZE" \
    || fail "(D2) implement-finalize.sh must include forked-target carve-out for main/master"

# ---------------------------------------------------------------------------
# (E) Runtime: --resume-phase ship-pr-rrr-phase14 requires handoff flag.
# ---------------------------------------------------------------------------
TMPROOT=$(mktemp -d "${TMPDIR:-/tmp}/test-ship-pr-rebase.XXXXXX")
trap 'rm -rf "$TMPROOT"' EXIT

write_ci_state() {
    local path=$1 phase=$2
    cat >"$path" <<EOF
PHASE=$phase
BRANCH_NAME=feature/test-ship-pr-rebase
ISSUE_NUMBER=3364
RUN_ID=test-ship-pr-rebase
REPO=owner/repo
REPO_UNAVAILABLE=false
FORKED_TARGET=false
MERGE=true
DRAFT=false
DEFERRED=false
PR_CLOSED=false
DONE_RENAME_APPLIED=false
STALL_TRACKING=true
STALL_STEP=10
BAIL_NEEDS_USER_INPUT=false
BAIL_REASON=
BAIL_FAILURE_DETAIL_LOG=
CI_PASSED=false
OOS_PENDING=false
PR_NUMBER=99
PR_URL=https://github.example/pr/99
PR_TITLE=Test PR
RESUME_PHASE=
CALLER_KIND=
REBASE_COUNT=0
FIX_ATTEMPTS=0
ITERATION=0
TRANSIENT_RETRIES=0
FAILED_RUN_ID=
MANIFEST_PATH=
TOOL_LABEL=claude
DESIGN_ONLY_DONE=false
EXPECTED_SESSION_ID=
EXPECTED_TMPDIR_BASENAME_PREFIX=claude-implement-test_
NO_LOGS_COMMIT=false
IMPLEMENT_TMPDIR=$TMPROOT
CI_FIX_REBASE_PENDING=false
EOF
}

state="$TMPROOT/ship-pr-state.sh"
write_ci_state "$state" ci-initial

set +e
out=$(
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
        "$SHIP_PR" \
        --state-file "$state" \
        --implement-tmpdir "$TMPROOT" \
        --merge true \
        --draft false \
        --forked false \
        --repo owner/repo \
        --no-admin-fallback true \
        --no-logs-commit true \
        --resume-phase ship-pr-rrr-phase14 \
        2>&1
)
rc=$?
set -e

[[ "$rc" -eq 2 ]] || fail "(E) expected exit 2 for missing handoff flag, got $rc"
grep -Fq 'ship-pr-rrr-after-phase14.flag' <<<"$out" \
    || fail "(E) expected die_usage mentioning ship-pr-rrr-after-phase14.flag"

# ---------------------------------------------------------------------------
# (F) Runtime: legacy --resume-phase step8b_rebase tolerates pre-Phase-1 argv.
# ---------------------------------------------------------------------------
write_bump_state() {
    local path=$1
    cat >"$path" <<EOF
PHASE=bump
BRANCH_NAME=feature/test-ship-pr-rebase
ISSUE_NUMBER=3364
RUN_ID=test-ship-pr-rebase
REPO=owner/repo
REPO_UNAVAILABLE=false
FORKED_TARGET=false
MERGE=true
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
RESUME_PHASE=step8b_rebase
CALLER_KIND=ship_pr_pre_push
REBASE_COUNT=0
FIX_ATTEMPTS=0
ITERATION=0
TRANSIENT_RETRIES=0
FAILED_RUN_ID=
MANIFEST_PATH=
TOOL_LABEL=claude
DESIGN_ONLY_DONE=false
EXPECTED_SESSION_ID=
EXPECTED_TMPDIR_BASENAME_PREFIX=claude-implement-test_
NO_LOGS_COMMIT=false
IMPLEMENT_TMPDIR=$TMPROOT
CI_FIX_REBASE_PENDING=false
EOF
}

bump_state="$TMPROOT/ship-pr-bump-state.sh"
write_bump_state "$bump_state"

set +e
legacy_out=$(
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
        "$SHIP_PR" \
        --state-file "$bump_state" \
        --implement-tmpdir "$TMPROOT" \
        --merge true \
        --draft false \
        --forked false \
        --repo owner/repo \
        --no-admin-fallback true \
        --no-logs-commit true \
        --resume-phase step8b_rebase \
        2>&1
)
legacy_rc=$?
set -e

grep -Fq 'unknown --resume-phase' <<<"$legacy_out" \
    && fail "(F) legacy --resume-phase step8b_rebase must not die_usage (got rc=$legacy_rc)"

echo "PASS: test-ship-pr-rebase.sh — CI-fix rebase structural pins, fork postbump guard, legacy resume, and resume guard hold (A-F, D2)"
