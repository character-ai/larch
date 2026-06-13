#!/usr/bin/env bash
# Focused timing regressions for review-implement-step5-loop.sh helpers.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
export CLAUDE_PLUGIN_ROOT="$REPO_ROOT"
export PLUGIN_ROOT="$REPO_ROOT"
export LARCH_QUIET_DISABLE=1
TMP_BASE=$(mktemp -d "${TMPDIR:-/tmp}/larch-step5-loop-timing-test.XXXXXX")
trap 'rm -rf "$TMP_BASE"' EXIT

flush_review_batches() { return 0; }

# shellcheck source=skills/review-and-fix/scripts/review-implement-step5-loop.sh
. "$REPO_ROOT/skills/review-and-fix/scripts/review-implement-step5-loop.sh"

IMPLEMENT_TMPDIR="$TMP_BASE/complete"
mkdir -p "$IMPLEMENT_TMPDIR"
export IMPLEMENT_TMPDIR
LARCH_TIMING_LEDGER="$TMP_BASE/stale-ledger.tsv" _emit_implement_round_timing_row 1 10 15 2 1
awk -F '\t' '$2 == "round" && $4 == "implement" && $5 == "Step 5 — code review" && $6 == 1 && $9 == 5 && $10 == 2 && $11 == 1 { found=1 } END { exit found ? 0 : 1 }' "$IMPLEMENT_TMPDIR/timing-ledger.tsv"
[[ ! -e "$TMP_BASE/stale-ledger.tsv" ]] || { echo "stale LARCH_TIMING_LEDGER received in-loop timing row" >&2; exit 1; }

IMPLEMENT_TMPDIR="$TMP_BASE/lint-handoff"
mkdir -p "$IMPLEMENT_TMPDIR"
export IMPLEMENT_TMPDIR
step5_persist_round_start 2 20
printf '### FINDING_1: accepted\n\n### FINDING_2: accepted\n' >"$IMPLEMENT_TMPDIR/round-2/accepted-findings.md"
printf '1:FINDING_3_OUTCOME=rejected\n' >"$IMPLEMENT_TMPDIR/round-2/rejected-findings.md"
[[ "$(cat "$IMPLEMENT_TMPDIR/round-2/round-start-s")" == "20" ]] || { echo "round-start-s not persisted" >&2; exit 1; }
[[ ! -e "$IMPLEMENT_TMPDIR/timing-ledger.tsv" ]] || { echo "lint handoff fixture should not emit in-loop timing row" >&2; exit 1; }
"$REPO_ROOT/skills/review-and-fix/scripts/record-implement-review-round-timing.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR" --round 2 --start-s 20 --end-s 25
awk -F '\t' '$2 == "round" && $4 == "implement" && $5 == "Step 5 — code review" && $6 == 2 && $9 == 5 && $10 == 2 && $11 == 1 { found=1 } END { exit found ? 0 : 1 }' "$IMPLEMENT_TMPDIR/timing-ledger.tsv"

IMPLEMENT_TMPDIR="$TMP_BASE/terminal-stall"
mkdir -p "$IMPLEMENT_TMPDIR"
export IMPLEMENT_TMPDIR
step5_persist_round_start 3 30
mkdir -p "$IMPLEMENT_TMPDIR/round-3"
printf 'ACCEPTED_COUNT=4\nREJECTED_COUNT=2\n' >"$IMPLEMENT_TMPDIR/round-3/review-tally.env"
"$REPO_ROOT/skills/review-and-fix/scripts/record-implement-review-round-timing.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR" --round 3 --start-s 30 --end-s 39
awk -F '\t' '$2 == "round" && $4 == "implement" && $5 == "Step 5 — code review" && $6 == 3 && $9 == 9 && $10 == 4 && $11 == 2 { found=1 } END { exit found ? 0 : 1 }' "$IMPLEMENT_TMPDIR/timing-ledger.tsv"

IMPLEMENT_TMPDIR="$TMP_BASE/run-loop-complete"
mkdir -p "$IMPLEMENT_TMPDIR/round-1"
export IMPLEMENT_TMPDIR
(
    unset STEP5_ROUND_1_TIMING_EMITTED
    _implement_round_body() {
        IRF_LAST_ROUND_STATUS=complete
        IRF_LAST_CODER_STATUS=applied
        IRF_LAST_SKIPPED=0
        IRF_LAST_FIX_COUNT=0
        IRF_LAST_ROUND_DIR="$IMPLEMENT_TMPDIR/round-1"
        IRF_LAST_ACCEPTED_FILE="$IMPLEMENT_TMPDIR/round-1/accepted-findings.md"
        IRF_LAST_ACCEPTED_COUNT=5
        IRF_LAST_REJECTED_COUNT=6
        IRF_LAST_FILES_HINT=files
        return 0
    }
    ROUND_CAP=1 STARTING_ROUND=1 RUN_ID=RUN-LOOP run_implement_loop >/dev/null
)
awk -F '\t' '$2 == "round" && $4 == "implement" && $5 == "Step 5 — code review" && $6 == 1 && $10 == 5 && $11 == 6 { found=1 } END { exit found ? 0 : 1 }' "$IMPLEMENT_TMPDIR/timing-ledger.tsv"

IMPLEMENT_TMPDIR="$TMP_BASE/run-loop-coder-main-agent-required"
mkdir -p "$IMPLEMENT_TMPDIR/round-1"
export IMPLEMENT_TMPDIR
(
    unset STEP5_ROUND_1_TIMING_EMITTED
    _implement_round_body() {
        IRF_LAST_ROUND_STATUS=coder-main-agent-required
        IRF_LAST_CODER_STATUS=claude-required
        IRF_LAST_SKIPPED=0
        IRF_LAST_FIX_COUNT=0
        IRF_LAST_ROUND_DIR="$IMPLEMENT_TMPDIR/round-1"
        IRF_LAST_ACCEPTED_FILE="$IMPLEMENT_TMPDIR/round-1/accepted-findings.md"
        IRF_LAST_ACCEPTED_COUNT=2
        IRF_LAST_REJECTED_COUNT=1
        IRF_LAST_FILES_HINT=files
        printf '### FINDING_1:\n\n### FINDING_2:\n' >"$IMPLEMENT_TMPDIR/round-1/accepted-findings.md"
        printf 'FINDING_3_OUTCOME=rejected\n' >"$IMPLEMENT_TMPDIR/round-1/rejected-findings.md"
        return 0
    }
    ROUND_CAP=1 STARTING_ROUND=1 RUN_ID=RUN-CODER-MAIN run_implement_loop >/dev/null
)
round_start_s=$(cat "$IMPLEMENT_TMPDIR/round-1/round-start-s")
[[ "$round_start_s" =~ ^[0-9]+$ ]] || { echo "coder-main-agent-required did not persist numeric round-start-s" >&2; exit 1; }
[[ ! -e "$IMPLEMENT_TMPDIR/timing-ledger.tsv" ]] || { echo "coder-main-agent-required fixture should defer in-loop timing row" >&2; exit 1; }
"$REPO_ROOT/skills/review-and-fix/scripts/record-implement-review-round-timing.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR" --round 1 --start-s "$round_start_s" --end-s "$((round_start_s + 7))"
awk -F '\t' '$2 == "round" && $4 == "implement" && $5 == "Step 5 — code review" && $6 == 1 && $9 == 7 && $10 == 2 && $11 == 1 { found=1 } END { exit found ? 0 : 1 }' "$IMPLEMENT_TMPDIR/timing-ledger.tsv"

IMPLEMENT_TMPDIR="$TMP_BASE/run-loop-lint-main-agent-required"
mkdir -p "$IMPLEMENT_TMPDIR/round-1"
export IMPLEMENT_TMPDIR
lint_redacted_log="$IMPLEMENT_TMPDIR/checks.redacted.log"
printf 'checks failed\n' >"$lint_redacted_log"
cat >"$IMPLEMENT_TMPDIR/stub-checks.sh" <<STUB
#!/usr/bin/env bash
printf 'STATUS=fail\n'
printf 'REDACTED_LOG_FILE=$lint_redacted_log\n'
STUB
cat >"$IMPLEMENT_TMPDIR/stub-lint.sh" <<'STUB'
#!/usr/bin/env bash
printf 'LINT_FIX_STATUS=main-agent-required\n'
STUB
chmod +x "$IMPLEMENT_TMPDIR/stub-checks.sh" "$IMPLEMENT_TMPDIR/stub-lint.sh"
set +e
(
    unset STEP5_ROUND_1_TIMING_EMITTED
    step5_now_s() {
        if [[ "${STEP5_TEST_NOW_COUNT:-0}" == "0" ]]; then
            STEP5_TEST_NOW_COUNT=1
            printf '100\n'
        else
            printf '105\n'
        fi
    }
    _implement_round_body() {
        IRF_LAST_ROUND_STATUS=fix-applied
        IRF_LAST_CODER_STATUS=applied
        IRF_LAST_SKIPPED=0
        IRF_LAST_FIX_COUNT=1
        IRF_LAST_ROUND_DIR="$IMPLEMENT_TMPDIR/round-1"
        IRF_LAST_ACCEPTED_FILE="$IMPLEMENT_TMPDIR/round-1/accepted-findings.md"
        IRF_LAST_ACCEPTED_COUNT=7
        IRF_LAST_REJECTED_COUNT=8
        IRF_LAST_FILES_HINT=files
        return 0
    }
    ROUND_CAP=1 STARTING_ROUND=1 RUN_ID=RUN-LINT-MAIN \
        REVIEW_AND_FIX_RUN_RELEVANT_CHECKS_SH="$IMPLEMENT_TMPDIR/stub-checks.sh" \
        REVIEW_AND_FIX_LINT_FIX_LOOP_SH="$IMPLEMENT_TMPDIR/stub-lint.sh" \
        run_implement_loop >/dev/null 2>"$IMPLEMENT_TMPDIR/loop.err"
)
lint_main_rc=$?
set -e
[[ "$lint_main_rc" -eq 2 ]] || { echo "lint main-agent-required expected exit 2, got $lint_main_rc" >&2; exit 1; }
[[ ! -e "$IMPLEMENT_TMPDIR/round-1/round-start-s" ]] || { echo "lint main-agent-required persisted round-start-s" >&2; exit 1; }
round_rows=$(awk -F '\t' '$2 == "round" && $4 == "implement" && $5 == "Step 5 — code review" && $6 == 1 && $7 == 100 { count++ } END { print count + 0 }' "$IMPLEMENT_TMPDIR/timing-ledger.tsv")
[[ "$round_rows" == "1" ]] || { echo "lint main-agent-required expected one in-loop timing row, saw $round_rows" >&2; exit 1; }
awk -F '\t' '$2 == "round" && $4 == "implement" && $5 == "Step 5 — code review" && $6 == 1 && $7 == 100 && $10 == 7 && $11 == 8 { found=1 } END { exit found ? 0 : 1 }' "$IMPLEMENT_TMPDIR/timing-ledger.tsv"
CLAUDE_PLUGIN_ROOT="$REPO_ROOT" IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR" \
    "$REPO_ROOT/skills/implement/scripts/step-5-resume.sh" --final-round-num 1 --record-only >/dev/null
round_rows_after=$(awk -F '\t' '$2 == "round" && $4 == "implement" && $5 == "Step 5 — code review" && $6 == 1 && $7 == 100 { count++ } END { print count + 0 }' "$IMPLEMENT_TMPDIR/timing-ledger.tsv")
[[ "$round_rows_after" == "1" ]] || { echo "lint main-agent-required record-only added duplicate timing row" >&2; exit 1; }

echo "PASS: test-review-implement-step5-loop-timing.sh"
