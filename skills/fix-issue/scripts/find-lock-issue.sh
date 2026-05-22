#!/usr/bin/env bash
# find-lock-issue.sh — Verify an explicit issue, lock it, and rename it to [IN PROGRESS].
#
# Explicit-target-only pipeline invoked by /fix-issue Step 0. Requires a
# positional issue number or URL argument. Runs four operations in sequence:
#   1. Verify the explicit issue (open, not managed-prefix, not blocked).
#   2. Probe the local working tree with scripts/check-clean-tree.sh
#      --fail-closed. Dirty or unknown cleanliness aborts before any GitHub
#      mutation so the original title remains intact.
#   3. Acquire the comment-based concurrency lock by delegating to
#      issue-lifecycle.sh comment --lock (posts "IN PROGRESS", post-checks
#      for duplicate races). The comment lock is the correctness invariant.
#   4. Rename the issue title to "[IN PROGRESS] <title>" by delegating to
#      tracking-issue-write.sh rename --state in-progress. Best-effort: a
#      rename failure does NOT undo the lock — the script still exits 0
#      with LOCK_ACQUIRED=true RENAMED=false. /implement Step 0.5 Branch 2
#      is the safety net (idempotent re-attempt on the next run-segment).
#
# Targets a specific issue (by number or GitHub URL), verifies it is open,
# runs umbrella detection FIRST (issue #819 DECISION_1 — if the issue is an
# umbrella, the umbrella branch is taken and managed-prefix rejection is
# bypassed so umbrellas with `[IN PROGRESS]` / `[DONE]` / `[STALLED]`
# titles remain explicitly targetable), then for non-umbrellas verifies the
# title does not carry a managed lifecycle title prefix or a [... Report]
# pattern, and has no currently-open blocking dependencies.
#
# Two orthogonal mechanisms coexist:
#   1) Comment-based "IN PROGRESS" lock — concurrency control on the
#      fix-issue subject issue. Acquired here at /fix-issue Step 0 (last
#      comment = exactly "IN PROGRESS"); cleared when work completes.
#      Prevents two concurrent /fix-issue runners from colliding on the same
#      subject.
#   2) Title-based "[IN PROGRESS]" / "[DONE]" / "[STALLED]" lifecycle —
#      machine-owned tracking-issue state. Applied here at lock time so
#      the title reflects active work immediately, instead of the
#      multi-minute delay incurred when only /implement Step 0.5 Branch 2
#      did the rename. /implement still re-attempts the rename idempotently
#      so /implement remains standalone-correct when invoked with --issue
#      against a non-pre-marked issue.
#
# Usage:
#   find-lock-issue.sh <number-or-url>
#
# Output (KEY=value lines on stdout):
#   ELIGIBLE=true|false
#   ISSUE_NUMBER=<N>          (when ELIGIBLE=true; on the umbrella-dispatch
#                              path, this is the CHOSEN CHILD's number)
#   ISSUE_TITLE=<title>       (when ELIGIBLE=true; the chosen child's title
#                              on the umbrella-dispatch path)
#   LOCK_ACQUIRED=true|false  (true on exit 0; false on exit 3 — lock-fail —
#                              and false on exit 4 — umbrella complete, no
#                              lock attempted)
#   RENAMED=true|false        (when LOCK_ACQUIRED=true; false = idempotent
#                              no-op OR rename API failure; rename errors
#                              additionally surfaced on stderr)
#   ERROR=<message>           (when ELIGIBLE=false and exit 2, or when exit 3,
#                              or when exit 5 — no eligible umbrella child)
#
#   Umbrella-only keys (FINDING_1 from the umbrella-PR plan review — emitted
#   ONLY when the umbrella detector returned IS_UMBRELLA=true):
#   IS_UMBRELLA=true          (only on umbrella paths — exit 0 dispatch,
#                              exit 3 child-lock-fail, exit 4 complete,
#                              exit 5 no-eligible-child)
#   UMBRELLA_NUMBER=<U>       (the umbrella issue number)
#   UMBRELLA_TITLE=<title>    (umbrella's title, when IS_UMBRELLA=true)
#   UMBRELLA_ACTION           (one of: dispatched | complete | no-eligible-
#                              child — describes the umbrella outcome)
#
# Exit codes:
#   0 — eligible issue found, comment lock acquired. On umbrella paths,
#       UMBRELLA_ACTION=dispatched and ISSUE_NUMBER refers to the chosen
#       child (rename may have failed best-effort — RENAMED=false signals).
#   2 — error: missing argument, gh CLI failure, explicit issue not eligible,
#       umbrella blocked by open dependencies, or umbrella-handler.sh detect
#       failure (closes #891). Also used for pre-lock dirty-tree aborts
#       before any GitHub mutation: ordinary paths emit ELIGIBLE=false
#       ERROR=Working tree is not clean..., while umbrella child paths also
#       emit IS_UMBRELLA=true UMBRELLA_NUMBER, UMBRELLA_TITLE, ISSUE_NUMBER,
#       ISSUE_TITLE, and LOCK_ACQUIRED=false.
#   3 — eligible issue found but comment lock could not be acquired
#       (concurrent runner won the race; on umbrella paths, the failure is
#       on the chosen child and ERROR carries umbrella context)
#   4 — umbrella complete: all parsed children are CLOSED. SKILL.md Step 0
#       invokes finalize-umbrella.sh on this path. ELIGIBLE=true with
#       LOCK_ACQUIRED=false (no lock; finalization is a different state
#       transition).
#   5 — umbrella detected but has no eligible child (some children open but
#       all blocked / locked / managed-prefixed, OR zero parseable children
#       found in the umbrella body — FINDING_3). ELIGIBLE=false, ERROR
#       carries the blocking reason.
#
# Stdout contract policy: delegate stdout (issue-lifecycle.sh, tracking-
# issue-write.sh) is captured into local shell variables and parsed
# key-by-key; never streamed. find-lock-issue.sh emits ONLY the keys
# declared above. Auxiliary delegate keys (COMMENTED, FAILED, NEW_TITLE,
# etc.) are filtered out so the SKILL.md parser sees a clean unified
# contract.
#
# Umbrella support (explicit-issue path only):
#   When the explicit issue is detected as an umbrella (title-only post-#846
#   — case-sensitive, after stripping zero or more leading bracket-blocks of
#   the form `[...]` and/or `(...)` per #819, the remainder begins with
#   `Umbrella: ` or `Umbrella — `; body content is NOT consulted), delegate
#   to umbrella-handler.sh to either:
#     - dispatch to the next-eligible child (pick-child returns CHILD_NUMBER),
#       lock the CHILD using --lock, rename the CHILD to [IN PROGRESS]. Emit
#       IS_UMBRELLA=true UMBRELLA_NUMBER=<U> UMBRELLA_TITLE=<T>
#       UMBRELLA_ACTION=dispatched alongside the existing ISSUE_NUMBER
#       (= child) keys. Exit 0.
#     - finalize the umbrella when all parsed children are CLOSED
#       (pick-child returns ALL_CLOSED=true). Emit IS_UMBRELLA=true
#       UMBRELLA_NUMBER=<U> UMBRELLA_TITLE=<T> UMBRELLA_ACTION=complete.
#       Exit 4. SKILL.md Step 0 invokes finalize-umbrella.sh.
#     - report no-eligible-child (pick-child returns NO_ELIGIBLE_CHILD).
#       Emit IS_UMBRELLA=true UMBRELLA_NUMBER=<U> UMBRELLA_ACTION=
#       no-eligible-child + ERROR=<reason>. Exit 5.
#   On child lock failure, emit exit 3 with ERROR carrying the umbrella
#   context ("Failed to lock chosen child #C of umbrella #U: <reason>").
#   UMBRELLA_NUMBER is emitted ONLY when an umbrella was detected — absent
#   on the normal (non-umbrella) explicit-issue exit-0 path, per FINDING_1
#   from the umbrella-PR plan review.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/../../../scripts/lib-quiet.sh"
larch_quiet_init

# Returns 0 if the title starts with a managed lifecycle prefix
# ("[IN PROGRESS] ", "[DONE] ", "[STALLED] "), 1 otherwise. Anchored at
# the start; trailing-space-sensitive (matches the helper exactly — no
# fuzzy match, so user titles containing the literal substring "[IN
# PROGRESS]" mid-text are NOT excluded). The optional "[ROUND-TRIP] "
# marker is intentionally NOT a managed-prefix gate here: it is a signal,
# not a lock, so a title with only that marker remains pickable.
has_managed_prefix() {
    local t="$1"
    case "$t" in
        '[IN PROGRESS] '*) return 0 ;;
        '[DONE] '*)        return 0 ;;
        '[STALLED] '*)     return 0 ;;
        *)                 return 1 ;;
    esac
}

# Returns 0 if the title matches the [... Report] pattern — a bracket-enclosed
# phrase ending with " Report" (case-insensitive) at the start of the title
# (e.g. "[Weekly Report]", "[AUDIT REPORT] Q3", "[analysis report]"). These
# are report/analytics issues not meant for automated fixing.
has_report_prefix() {
    printf '%s' "$1" | grep -qiE '^\[[^]]*[[:space:]]+report\]'
}

# Returns 0 when the title uses the stable run-logs audit-report prefix
# (`[Run Logs Audit Report …]`), which is not matched by has_report_prefix
# because the closing `]` follows the ISO timestamp, not immediately after
# the word "Report". Used as a secondary guard when the audit-report label is
# missing or unreadable.
has_run_logs_audit_report_title() {
    local t="$1"
    case "$t" in
        '[Run Logs Audit Report '*) return 0 ;;
        *)                         return 1 ;;
    esac
}

ISSUE_ARG=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        -*)
            emit_kv ELIGIBLE false
            emit_kv ERROR "Unknown option: $1"
            exit 2
            ;;
        *)
            # Positional argument: issue number or URL
            if [[ -n "$ISSUE_ARG" ]]; then
                emit_kv ELIGIBLE false
                emit_kv ERROR "Unexpected extra argument: $1 (issue already set to $ISSUE_ARG)"
                exit 2
            fi
            ISSUE_ARG="$1"; shift
            ;;
    esac
done

if [[ -z "$ISSUE_ARG" ]]; then
    emit_kv ELIGIBLE false
    emit_kv ERROR "Usage: find-lock-issue.sh <issue-number-or-url>"
    exit 2
fi

# ---------------------------------------------------------------------------
# Resolve repo identity
# ---------------------------------------------------------------------------
RESOLVE_REPO="${SCRIPT_DIR}/../../../scripts/resolve-repo.sh"
REPO=$("$RESOLVE_REPO" 2>/dev/null) || {
    emit_kv ELIGIBLE false
    emit_kv ERROR "Failed to resolve repository name"
    exit 2
}

# ---------------------------------------------------------------------------
# Source the shared blocker-resolution helpers. Defines:
#   - native_open_blockers <issue-number>
#   - prose_open_blockers  <issue-number>
#   - all_open_blockers    <issue-number>  (native ∪ prose, native-first short-circuit)
#
# See skills/fix-issue/scripts/blocker-helpers.{sh,md} for the canonical
# definitions and contract. The library reads $REPO at call time, so we
# source AFTER the REPO assignment above.
#
# Guarded source: an unguarded `source` failure under `set -euo pipefail`
# would abort this script before emitting the documented stdout contract,
# breaking callers (e.g., /fix-issue Step 0) that parse KEY=VALUE output.
# ---------------------------------------------------------------------------
BLOCKER_HELPERS="$(dirname "${BASH_SOURCE[0]}")/blocker-helpers.sh"
# shellcheck source=skills/fix-issue/scripts/blocker-helpers.sh
source "$BLOCKER_HELPERS" || {
    emit_kv ELIGIBLE false
    emit_kv ERROR "Failed to source blocker-helpers.sh: $BLOCKER_HELPERS"
    exit 2
}

# ---------------------------------------------------------------------------
# _emit_dirty_tree_pre_lock_abort <issue-num> <issue-title>
#                                 [<umbrella-num> <umbrella-title>]
#
# Runs the local working-tree cleanliness probe immediately before lock
# acquisition. The predicate itself lives in scripts/check-clean-tree.sh so
# this pre-lock guard and preflight.sh share one git-status contract.
# find-lock-issue.sh uses --fail-closed because it must not post
# IN PROGRESS, or rename an issue when local cleanliness cannot be determined.
# preflight.sh intentionally calls the same helper in default fail-open mode
# to preserve its historical setup behavior.
# ---------------------------------------------------------------------------
_emit_dirty_tree_pre_lock_abort() {
    local issue_num="$1"
    local issue_title="$2"
    local umbrella_num="${3:-}"
    local umbrella_title="${4:-}"
    local check_script="${SCRIPT_DIR}/../../../scripts/check-clean-tree.sh"

    local probe_out probe_exit=0
    probe_out=$("$check_script" --fail-closed 2>&1) || probe_exit=$?

    local clean_line
    clean_line=$(printf '%s\n' "$probe_out" | awk -F= '/^CLEAN=/ { v=$2 } END { print v }')

    if [ "$probe_exit" -eq 0 ] && [ "$clean_line" = "true" ]; then
        # Working tree is clean. Also check for committed-but-unpushed
        # larch-log flush commits on main. No fetch: we use the locally-cached
        # origin/main ref — see check-main-sync.md for the rationale.
        local sync_script="${SCRIPT_DIR}/../../../scripts/check-main-sync.sh"
        if [ ! -f "$sync_script" ]; then
            emit_kv ELIGIBLE false
            emit_kv ERROR "check-main-sync.sh missing at $sync_script; cannot verify main sync before lock."
            exit 2
        fi
        local sync_out sync_exit=0
        sync_out=$(bash "$sync_script" 2>&1) || sync_exit=$?
        local sync_status
        sync_status=$(printf '%s\n' "$sync_out" | awk -F= '/^SYNC_STATUS=/ { v=$2 } END { print v }')
        if [ "$sync_exit" -eq 1 ] || [ "$sync_status" = "blocked" ]; then
            local sync_error
            sync_error=$(printf '%s\n' "$sync_out" | awk -F= '/^ERROR=/ { sub(/^ERROR=/, "", $0); v=$0 } END { print v }')
            emit_kv ELIGIBLE false
            if [ -n "$umbrella_num" ]; then
                emit_kv IS_UMBRELLA true
                emit_kv UMBRELLA_NUMBER "$umbrella_num"
                emit_kv UMBRELLA_TITLE "$umbrella_title"
                emit_kv ISSUE_NUMBER "$issue_num"
                emit_kv ISSUE_TITLE "$issue_title"
                emit_kv LOCK_ACQUIRED false
            fi
            emit_kv ERROR "${sync_error:-local main is ahead of origin/main with non-log commits; push or reconcile before re-running /fix-issue. No issue was locked.}"
            exit 2
        fi
        # Exit 2 with SYNC_STATUS=probe-error only: fail-open (same rationale as
        # preflight); other non-zero exits fail closed before lock.
        if [ "$sync_exit" -eq 2 ] && [ "$sync_status" = "probe-error" ]; then
            :
        elif [ "$sync_exit" -ne 0 ]; then
            emit_kv ELIGIBLE false
            if [ -n "$umbrella_num" ]; then
                emit_kv IS_UMBRELLA true
                emit_kv UMBRELLA_NUMBER "$umbrella_num"
                emit_kv UMBRELLA_TITLE "$umbrella_title"
                emit_kv ISSUE_NUMBER "$issue_num"
                emit_kv ISSUE_TITLE "$issue_title"
                emit_kv LOCK_ACQUIRED false
            fi
            emit_kv ERROR "check-main-sync.sh exited unexpectedly (exit $sync_exit). No issue was locked."
            exit 2
        fi
        # SYNC_STATUS=reset means flush commits were auto-cleared; ok or
        # not-main also mean the run can proceed.
        return 0
    fi

    emit_kv ELIGIBLE false
    if [ -n "$umbrella_num" ]; then
        emit_kv IS_UMBRELLA true
        emit_kv UMBRELLA_NUMBER "$umbrella_num"
        emit_kv UMBRELLA_TITLE "$umbrella_title"
        emit_kv ISSUE_NUMBER "$issue_num"
        emit_kv ISSUE_TITLE "$issue_title"
        emit_kv LOCK_ACQUIRED false
    fi

    if [ "$probe_exit" -eq 0 ] && [ "$clean_line" = "false" ]; then
        emit_kv ERROR "Working tree is not clean. Commit or stash changes, then re-run /fix-issue. No issue was locked."
    else
        local summary
        summary=$(printf '%s\n' "$probe_out" | awk '/^PROBE_ERROR=/ { sub(/^PROBE_ERROR=/, "", $0); v=$0 } END { print v }')
        [ -n "$summary" ] || summary="probe exited $probe_exit"
        emit_kv ERROR "Cannot determine working-tree cleanliness: $summary"
    fi
    exit 2
}

# ---------------------------------------------------------------------------
# lock_and_rename_then_emit <issue-num> <issue-title>
#
# Acquires the comment lock by delegating to issue-lifecycle.sh comment --lock,
# then attempts a best-effort title rename via tracking-issue-write.sh rename
# --state in-progress. Emits the unified stdout contract and exits.
#
# Stdout filtering: delegate stdout is captured into local variables and parsed
# key-by-key. Only the unified contract keys (ELIGIBLE, ISSUE_NUMBER,
# ISSUE_TITLE, LOCK_ACQUIRED, RENAMED, ERROR) are echoed. Auxiliary delegate
# keys (COMMENTED, FAILED, NEW_TITLE, etc.) are filtered out so the SKILL.md
# parser sees a clean contract.
#
# set -e guards: the lock and rename calls are wrapped with `|| <var>=$?` so
# a non-zero exit from the delegate does not prematurely abort find-lock-
# issue.sh under `set -euo pipefail` — the script must still emit its own
# unified contract before exiting.
#
# Exit codes (terminal — does not return):
#   0  — lock acquired (rename may have succeeded or failed best-effort)
#   3  — eligibility passed but lock acquisition failed
# ---------------------------------------------------------------------------
lock_and_rename_then_emit() {
    local issue_num="$1"
    local issue_title="$2"
    local lock_script rename_script
    lock_script="${SCRIPT_DIR}/issue-lifecycle.sh"
    rename_script="${SCRIPT_DIR}/../../../scripts/tracking-issue-write.sh"

    _emit_dirty_tree_pre_lock_abort "$issue_num" "$issue_title" "" ""

    # ---- Acquire comment lock (correctness invariant) ----
    local lock_out lock_exit=0
    lock_out=$("$lock_script" comment --issue "$issue_num" --body "IN PROGRESS" --lock 2>&1) || lock_exit=$?

    # Parse LOCK_ACQUIRED and ERROR from delegate stdout. Use awk's last-line-
    # wins for each key so the same key appearing multiple times resolves to
    # the final value. Auxiliary keys (COMMENTED, etc.) are not extracted.
    local lock_acquired lock_error
    lock_acquired=$(echo "$lock_out" | awk -F= '/^LOCK_ACQUIRED=/ { v=$2 } END { print v }')
    lock_error=$(echo "$lock_out" | awk -F= '/^ERROR=/ { sub(/^ERROR=/, "", $0); v=$0 } END { print v }')

    if [ "$lock_acquired" != "true" ] || [ "$lock_exit" -ne 0 ]; then
        # Lock failed. Surface the unified contract; preserve eligibility
        # signal (ELIGIBLE=true) so callers can distinguish eligibility-pass
        # from successful lock acquisition.
        emit_kv ELIGIBLE true
        emit_kv ISSUE_NUMBER "$issue_num"
        emit_kv ISSUE_TITLE "$issue_title"
        emit_kv LOCK_ACQUIRED false
        if [ -n "$lock_error" ]; then
            emit_kv ERROR "$lock_error"
        else
            emit_kv ERROR "Lock acquisition failed (issue-lifecycle.sh exit $lock_exit)"
        fi
        exit 3
    fi

    # ---- Rename title (best-effort) ----
    local rename_out rename_exit=0 renamed=false rename_error=""
    rename_out=$("$rename_script" rename --issue "$issue_num" --state in-progress --repo "$REPO" 2>&1) || rename_exit=$?

    # Parse RENAMED (true/false). RENAMED=false is BOTH the idempotent no-op
    # path AND the failure path; distinguish via FAILED= or non-zero exit.
    local rename_failed
    renamed=$(echo "$rename_out" | awk -F= '/^RENAMED=/ { v=$2 } END { print v }')
    rename_failed=$(echo "$rename_out" | awk -F= '/^FAILED=/ { v=$2 } END { print v }')
    rename_error=$(echo "$rename_out" | awk -F= '/^ERROR=/ { sub(/^ERROR=/, "", $0); v=$0 } END { print v }')

    if [ "$rename_exit" -ne 0 ] || [ "$rename_failed" = "true" ]; then
        # Rename failed. Best-effort: lock is the correctness boundary; do
        # not undo it. Surface the failure on stderr; emit RENAMED=false on
        # stdout. /implement Step 0.5 Branch 2's idempotent rename is the
        # safety net.
        if [ -n "$rename_error" ]; then
            larch_err "WARNING: title rename failed for issue #$issue_num: $rename_error"
        else
            larch_err "WARNING: title rename failed for issue #$issue_num (tracking-issue-write.sh exit $rename_exit)"
        fi
        renamed="false"
    fi

    # Normalize: empty (older script versions or unexpected output) → false.
    if [ -z "$renamed" ]; then
        renamed="false"
    fi

    # ---- Emit unified contract ----
    emit_kv ELIGIBLE true
    emit_kv ISSUE_NUMBER "$issue_num"
    emit_kv ISSUE_TITLE "$issue_title"
    emit_kv LOCK_ACQUIRED true
    emit_kv RENAMED "$renamed"
    exit 0
}

# ---------------------------------------------------------------------------
# lock_and_rename_then_emit_for_child <child-num> <child-title>
#                                     <umbrella-num> <umbrella-title>
#
# Umbrella child-dispatch lock path. Same shape as
# lock_and_rename_then_emit (above), but emits the unified contract WITH
# umbrella-context keys (IS_UMBRELLA, UMBRELLA_NUMBER, UMBRELLA_TITLE,
# UMBRELLA_ACTION=dispatched).
#
# On child lock failure, exits 3 with an ERROR string that names BOTH the
# child and the umbrella so SKILL.md Step 0's exit-3 branch can present a
# clear error to the operator.
# ---------------------------------------------------------------------------
lock_and_rename_then_emit_for_child() {
    local child_num="$1"
    local child_title="$2"
    local umbrella_num="$3"
    local umbrella_title="$4"
    local lock_script rename_script
    lock_script="${SCRIPT_DIR}/issue-lifecycle.sh"
    rename_script="${SCRIPT_DIR}/../../../scripts/tracking-issue-write.sh"

    _emit_dirty_tree_pre_lock_abort "$child_num" "$child_title" "$umbrella_num" "$umbrella_title"

    # ---- Acquire comment lock ----
    local lock_out lock_exit=0
    lock_out=$("$lock_script" comment --issue "$child_num" --body "IN PROGRESS" --lock 2>&1) || lock_exit=$?

    local lock_acquired lock_error
    lock_acquired=$(echo "$lock_out" | awk -F= '/^LOCK_ACQUIRED=/ { v=$2 } END { print v }')
    lock_error=$(echo "$lock_out" | awk -F= '/^ERROR=/ { sub(/^ERROR=/, "", $0); v=$0 } END { print v }')

    if [ "$lock_acquired" != "true" ] || [ "$lock_exit" -ne 0 ]; then
        emit_kv ELIGIBLE true
        emit_kv IS_UMBRELLA true
        emit_kv UMBRELLA_NUMBER "$umbrella_num"
        emit_kv UMBRELLA_TITLE "$umbrella_title"
        emit_kv ISSUE_NUMBER "$child_num"
        emit_kv ISSUE_TITLE "$child_title"
        emit_kv LOCK_ACQUIRED false
        if [ -n "$lock_error" ]; then
            emit_kv ERROR "Failed to lock chosen child #$child_num of umbrella #$umbrella_num: $lock_error"
        else
            emit_kv ERROR "Failed to lock chosen child #$child_num of umbrella #$umbrella_num (issue-lifecycle.sh exit $lock_exit)"
        fi
        exit 3
    fi

    # ---- Rename the child to [IN PROGRESS] (best-effort) ----
    local rename_out rename_exit=0 renamed=false rename_error=""
    rename_out=$("$rename_script" rename --issue "$child_num" --state in-progress --repo "$REPO" 2>&1) || rename_exit=$?
    local rename_failed
    renamed=$(echo "$rename_out" | awk -F= '/^RENAMED=/ { v=$2 } END { print v }')
    rename_failed=$(echo "$rename_out" | awk -F= '/^FAILED=/ { v=$2 } END { print v }')
    rename_error=$(echo "$rename_out" | awk -F= '/^ERROR=/ { sub(/^ERROR=/, "", $0); v=$0 } END { print v }')
    if [ "$rename_exit" -ne 0 ] || [ "$rename_failed" = "true" ]; then
        if [ -n "$rename_error" ]; then
            larch_err "WARNING: title rename failed for child #$child_num (umbrella #$umbrella_num): $rename_error"
        else
            larch_err "WARNING: title rename failed for child #$child_num (umbrella #$umbrella_num) (tracking-issue-write.sh exit $rename_exit)"
        fi
        renamed="false"
    fi
    if [ -z "$renamed" ]; then
        renamed="false"
    fi

    # ---- Emit unified contract ----
    emit_kv ELIGIBLE true
    emit_kv IS_UMBRELLA true
    emit_kv UMBRELLA_NUMBER "$umbrella_num"
    emit_kv UMBRELLA_TITLE "$umbrella_title"
    emit_kv UMBRELLA_ACTION dispatched
    emit_kv ISSUE_NUMBER "$child_num"
    emit_kv ISSUE_TITLE "$child_title"
    emit_kv LOCK_ACQUIRED true
    emit_kv RENAMED "$renamed"
    exit 0
}

# ---------------------------------------------------------------------------
# handle_umbrella <umbrella-num> <umbrella-title>
#
# Invoked from the explicit-issue path AFTER the umbrella detector has
# returned IS_UMBRELLA=true. Calls umbrella-handler.sh pick-child and
# branches on the outcome:
#   - CHILD_NUMBER → lock_and_rename_then_emit_for_child (terminal)
#   - ALL_CLOSED   → emit exit-4 contract (SKILL.md finalizes umbrella)
#   - NO_ELIGIBLE_CHILD → emit exit-5 contract
# ---------------------------------------------------------------------------
handle_umbrella() {
    local umbrella_num="$1"
    local umbrella_title="$2"
    local handler_script
    handler_script="${SCRIPT_DIR}/umbrella-handler.sh"

    local pick_out pick_exit=0
    pick_out=$("$handler_script" pick-child --issue "$umbrella_num" 2>&1) || pick_exit=$?
    if [ "$pick_exit" -ne 0 ]; then
        local err
        err=$(echo "$pick_out" | awk -F= '/^ERROR=/ { sub(/^ERROR=/, "", $0); v=$0 } END { print v }')
        emit_kv ELIGIBLE false
        emit_kv IS_UMBRELLA true
        emit_kv UMBRELLA_NUMBER "$umbrella_num"
        emit_kv ERROR "Failed to pick child for umbrella #$umbrella_num: ${err:-pick-child failed}"
        exit 2
    fi
    local child_number child_title all_closed no_eligible blocking_reason
    child_number=$(echo "$pick_out" | awk -F= '/^CHILD_NUMBER=/ { v=$2 } END { print v }')
    child_title=$(echo "$pick_out" | awk -F= '/^CHILD_TITLE=/ { sub(/^CHILD_TITLE=/, "", $0); v=$0 } END { print v }')
    all_closed=$(echo "$pick_out" | awk -F= '/^ALL_CLOSED=/ { v=$2 } END { print v }')
    no_eligible=$(echo "$pick_out" | awk -F= '/^NO_ELIGIBLE_CHILD=/ { v=$2 } END { print v }')
    blocking_reason=$(echo "$pick_out" | awk -F= '/^BLOCKING_REASON=/ { sub(/^BLOCKING_REASON=/, "", $0); v=$0 } END { print v }')

    if [ -n "$child_number" ]; then
        # Before locking the child, run the same blocker check we would for
        # any explicit issue. all_open_blockers is fail-open on API errors
        # (see its docstring above), so a blocker check that returns empty
        # could mean either "no blockers" or "API blip" — same posture as
        # the existing explicit-issue path uses for non-umbrella issues.
        local child_blockers
        child_blockers=$(all_open_blockers "$child_number")
        if [ -n "$child_blockers" ]; then
            local formatted
            formatted=$(echo "$child_blockers" | tr ' ' '\n' | sed 's/^/#/' | paste -sd ',' -)
            emit_kv ELIGIBLE false
            emit_kv IS_UMBRELLA true
            emit_kv UMBRELLA_NUMBER "$umbrella_num"
            emit_kv UMBRELLA_ACTION no-eligible-child
            emit_kv ERROR "Umbrella #$umbrella_num child #$child_number is blocked by open dependencies: $formatted"
            exit 5
        fi
        lock_and_rename_then_emit_for_child "$child_number" "$child_title" "$umbrella_num" "$umbrella_title"
        # terminal — exits 0 or 3
    fi
    if [ "$all_closed" = "true" ]; then
        emit_kv ELIGIBLE true
        emit_kv IS_UMBRELLA true
        emit_kv UMBRELLA_NUMBER "$umbrella_num"
        emit_kv UMBRELLA_TITLE "$umbrella_title"
        emit_kv UMBRELLA_ACTION complete
        emit_kv LOCK_ACQUIRED false
        exit 4
    fi
    if [ "$no_eligible" = "true" ]; then
        emit_kv ELIGIBLE false
        emit_kv IS_UMBRELLA true
        emit_kv UMBRELLA_NUMBER "$umbrella_num"
        emit_kv UMBRELLA_ACTION no-eligible-child
        emit_kv ERROR "Umbrella #$umbrella_num has no eligible child: ${blocking_reason:-no blocking reason given}"
        exit 5
    fi
    # Defensive: pick-child should always emit one of the three outcomes.
    emit_kv ELIGIBLE false
    emit_kv IS_UMBRELLA true
    emit_kv UMBRELLA_NUMBER "$umbrella_num"
    emit_kv ERROR "umbrella-handler.sh pick-child returned no recognized outcome"
    exit 2
}

# ---------------------------------------------------------------------------
# Explicit issue path (positional issue number or URL)
# ---------------------------------------------------------------------------
if [[ -n "$ISSUE_ARG" ]]; then
    # gh issue view accepts both bare numbers and full GitHub URLs natively.
    # For URLs, it resolves the repo from the URL — we must verify it matches
    # the current repo to prevent cross-repo misoperation.
    ISSUE_QUERY="$ISSUE_ARG"
    case "$ISSUE_ARG" in
        https://*/issues/*)
            ISSUE_REPO_FROM_ARG=$(printf '%s\n' "$ISSUE_ARG" | sed -n 's|https://[^/]*/\([^/]*/[^/]*\)/issues/[0-9][0-9]*.*|\1|p')
            ISSUE_NUM_FROM_ARG=$(printf '%s\n' "$ISSUE_ARG" | sed -n 's|https://[^/]*/[^/]*/[^/]*/issues/\([0-9][0-9]*\).*|\1|p')
            if [[ -z "$ISSUE_REPO_FROM_ARG" || -z "$ISSUE_NUM_FROM_ARG" ]]; then
                emit_kv ELIGIBLE false
                emit_kv ERROR "Cannot parse issue URL: $ISSUE_ARG"
                exit 2
            fi
            if [[ "$ISSUE_REPO_FROM_ARG" != "$REPO" ]]; then
                emit_kv ELIGIBLE false
                emit_kv ERROR "Issue belongs to $ISSUE_REPO_FROM_ARG, not the current repo ($REPO)"
                exit 2
            fi
            ISSUE_QUERY="$ISSUE_NUM_FROM_ARG"
            ;;
    esac
    ISSUE_JSON=$(gh issue view "$ISSUE_QUERY" --repo "$REPO" --json number,state,title,url,labels 2>/dev/null) || {
        emit_kv ELIGIBLE false
        emit_kv ERROR "Failed to fetch issue (invalid number, URL, or inaccessible): $ISSUE_ARG"
        exit 2
    }

    ISSUE_NUM=$(echo "$ISSUE_JSON" | jq -r '.number')
    ISSUE_STATE=$(echo "$ISSUE_JSON" | jq -r '.state')
    ISSUE_TITLE=$(echo "$ISSUE_JSON" | jq -r '.title')
    ISSUE_URL=$(echo "$ISSUE_JSON" | jq -r '.url // empty')

    # Verify issue belongs to the current repo by parsing owner/repo from the
    # issue URL. Host is intentionally not pinned to github.com so the parser
    # works for GitHub Enterprise / self-hosted GHE deployments too — the
    # cross-repo guard below (ISSUE_REPO != REPO) is the actual safety net,
    # since $REPO already comes from `gh repo view` in the current repo. The
    # `gh` CLI always emits `https://` URLs (no plain `http://`), so a literal
    # `https://` keeps the regex BRE-compatible across BSD sed / GNU sed.
    if [[ -z "$ISSUE_URL" ]]; then
        emit_kv ELIGIBLE false
        emit_kv ERROR "Cannot verify repository ownership for issue: $ISSUE_ARG"
        exit 2
    fi
    ISSUE_REPO=$(echo "$ISSUE_URL" | sed -n 's|https://[^/]*/\([^/]*/[^/]*\)/issues/.*|\1|p')
    if [[ -z "$ISSUE_REPO" ]]; then
        emit_kv ELIGIBLE false
        emit_kv ERROR "Cannot parse repository from issue URL: $ISSUE_URL"
        exit 2
    fi
    if [[ "$ISSUE_REPO" != "$REPO" ]]; then
        emit_kv ELIGIBLE false
        emit_kv ERROR "Issue belongs to $ISSUE_REPO, not the current repo ($REPO)"
        exit 2
    fi

    # Verify issue is open
    if [ "$ISSUE_STATE" != "OPEN" ]; then
        emit_kv ELIGIBLE false
        emit_kv ERROR "Issue #$ISSUE_NUM is not open (state: $ISSUE_STATE)"
        exit 2
    fi

    # Exclude issues labeled 'audit-report' — these are /audit-runs chain-of-
    # history issues, not fix-issue candidates. Labels must be a JSON array;
    # jq failures are fail-closed (do not treat as "not labeled").
    set +e
    echo "$ISSUE_JSON" | jq -e '.labels | type == "array"' >/dev/null 2>&1
    labels_type_rc=$?
    set -e
    if [ "$labels_type_rc" -ne 0 ]; then
        if [ "$labels_type_rc" -eq 1 ]; then
            emit_kv ELIGIBLE false
            emit_kv ERROR "Cannot verify issue #$ISSUE_NUM labels (labels field is not a JSON array); refusing eligibility"
            exit 2
        fi
        emit_kv ELIGIBLE false
        emit_kv ERROR "Cannot verify issue #$ISSUE_NUM labels (jq failed verifying labels array, exit $labels_type_rc); refusing eligibility"
        exit 2
    fi
    set +e
    echo "$ISSUE_JSON" | jq -e '[.labels[]?.name] | index("audit-report") != null' >/dev/null 2>&1
    audit_label_rc=$?
    set -e
    case "$audit_label_rc" in
        0)
            emit_kv ELIGIBLE false
            emit_kv ERROR "Issue #$ISSUE_NUM has label 'audit-report'; audit-report issues are excluded from /fix-issue"
            exit 2
            ;;
        1) ;;
        *)
            emit_kv ELIGIBLE false
            emit_kv ERROR "Cannot verify audit-report label for issue #$ISSUE_NUM (jq failed, exit $audit_label_rc); refusing eligibility"
            exit 2
            ;;
    esac

    if has_run_logs_audit_report_title "$ISSUE_TITLE"; then
        emit_kv ELIGIBLE false
        emit_kv ERROR "Issue #$ISSUE_NUM has a run-logs audit report title; not a fix-issue candidate"
        exit 2
    fi

    # Umbrella detection (explicit-issue path only): runs BEFORE both the
    # managed-prefix early-reject AND the last-comment `IN PROGRESS` lock
    # guard so umbrella titles carrying a managed lifecycle prefix (e.g.
    # `[IN PROGRESS] Umbrella: foo`, `[DONE] Umbrella: foo`,
    # `[STALLED] Umbrella: foo`) reach the umbrella dispatcher. Without this
    # ordering, `is_umbrella_title`'s post-#819 bracket-prefix peel would be
    # unreachable for hand-authored umbrellas — see issue #819 design
    # DECISION_1 (voted, 2-1) for the rationale. Detection is title-only
    # post-#846 (the prior body-literal substring match caused false
    # positives like #753); the umbrella's existence is the approval signal
    # — children inherit approval from the umbrella's existence.
    UMBRELLA_HANDLER="${SCRIPT_DIR}/umbrella-handler.sh"
    if [[ -x "$UMBRELLA_HANDLER" ]]; then
        UMBRELLA_DETECT_OUT=""
        if UMBRELLA_DETECT_OUT=$("$UMBRELLA_HANDLER" detect --issue "$ISSUE_NUM" 2>&1); then
            IS_UMBRELLA_DETECT=$(echo "$UMBRELLA_DETECT_OUT" | awk -F= '/^IS_UMBRELLA=/ { v=$2 } END { print v }')
            if [ "$IS_UMBRELLA_DETECT" = "true" ]; then
                # Apply the umbrella's own blocker check (parallel to non-
                # umbrella behavior — an umbrella that is itself blocked by
                # an open issue should not dispatch). The umbrella's parsed
                # children are filtered out of the blocker set: per #716,
                # /umbrella now wires native child→umbrella edges so each
                # open child appears in the umbrella's blocked_by, but the
                # umbrella is meant to be GATED on its children (and
                # handle_umbrella dispatches them) — not deadlocked. Only
                # blockers that are NOT parsed children of this umbrella
                # count as umbrella-blockers.
                #
                # Bypass `all_open_blockers` here: it short-circuits on
                # any native blocker without ever consulting prose blockers
                # (see all_open_blockers comment block above), which would
                # let an umbrella with native child-blockers + a separate
                # prose blocker pass our filter and dispatch incorrectly.
                # Fetch native and prose independently, filter children
                # only from native, then union before deciding eligibility.
                NATIVE_BLOCKERS=$(native_open_blockers "$ISSUE_NUM")
                if [ -n "$NATIVE_BLOCKERS" ]; then
                    set +e
                    LIST_CHILDREN_OUT=$("$UMBRELLA_HANDLER" list-children --issue "$ISSUE_NUM" 2>/dev/null)
                    LIST_CHILDREN_EXIT=$?
                    set -e
                    if [ "$LIST_CHILDREN_EXIT" -ne 0 ]; then
                        larch_err "WARNING: list-children failed for umbrella #$ISSUE_NUM (exit $LIST_CHILDREN_EXIT) — children-filter degraded; native blockers not filtered"
                    fi
                    UMBRELLA_CHILDREN=$(echo "$LIST_CHILDREN_OUT" | awk -F= '/^CHILDREN=/ { v=$2 } END { print v }')
                    FILTERED_NATIVE=""
                    for b in $NATIVE_BLOCKERS; do
                        is_child="false"
                        for c in $UMBRELLA_CHILDREN; do
                            if [ "$b" = "$c" ]; then
                                is_child="true"
                                break
                            fi
                        done
                        if [ "$is_child" = "false" ]; then
                            FILTERED_NATIVE="$FILTERED_NATIVE $b"
                        fi
                    done
                    NATIVE_BLOCKERS=$(echo "$FILTERED_NATIVE" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                fi
                PROSE_BLOCKERS=$(prose_open_blockers "$ISSUE_NUM")
                # Union + dedupe (sort -u tolerates leading/trailing space and
                # an empty-line input from concatenated empty sets). The
                # `grep -v '^$'` filter exits 1 when given all-empty input
                # (zero matches), which under `set -euo pipefail` would abort
                # the script and silently swallow the umbrella with no
                # blockers — `|| true` brackets the filter so empty unions
                # propagate as empty strings instead of fatal exits.
                BLOCKERS=$(printf '%s %s' "$NATIVE_BLOCKERS" "$PROSE_BLOCKERS" \
                    | tr ' ' '\n' | { grep -v '^$' || true; } | sort -u -n \
                    | tr '\n' ' ' | sed 's/[[:space:]]*$//')
                if [ -n "$BLOCKERS" ]; then
                    FORMATTED=$(echo "$BLOCKERS" | tr ' ' '\n' | sed 's/^/#/' | paste -sd ',' -)
                    emit_kv ELIGIBLE false
                    emit_kv IS_UMBRELLA true
                    emit_kv UMBRELLA_NUMBER "$ISSUE_NUM"
                    emit_kv ERROR "Umbrella #$ISSUE_NUM is blocked by open dependencies: $FORMATTED"
                    exit 2
                fi
                handle_umbrella "$ISSUE_NUM" "$ISSUE_TITLE"
                # terminal — exits 0/3/4/5
            fi
        else
            DETECT_ERROR=$(echo "$UMBRELLA_DETECT_OUT" | awk -F= '/^ERROR=/ { v=substr($0,index($0,"=")+1) } END { print v }')
            emit_kv ELIGIBLE false
            emit_kv ERROR "umbrella-handler.sh detect failed for issue #$ISSUE_NUM: ${DETECT_ERROR:-unknown error}"
            exit 2
        fi
    fi

    # Exclude issues with a managed lifecycle title prefix
    # ([IN PROGRESS] / [DONE] / [STALLED]). These are machine-owned
    # tracking issues (/implement),
    # not candidates for /fix-issue automated work. Runs AFTER umbrella
    # detection (per #819 DECISION_1) so an umbrella whose title carries
    # a managed-prefix (e.g. `[IN PROGRESS] Umbrella: foo`) reaches
    # `handle_umbrella` above and never falls through here.
    if has_managed_prefix "$ISSUE_TITLE"; then
        emit_kv ELIGIBLE false
        emit_kv ERROR "Issue #$ISSUE_NUM has a managed lifecycle title prefix ([IN PROGRESS] / [DONE] / [STALLED]); not a fix-issue candidate"
        exit 2
    fi

    # Exclude report issues (titles matching "[... Report]"). These are
    # analytics/reporting issues not meant for automated fixing.
    if has_report_prefix "$ISSUE_TITLE"; then
        emit_kv ELIGIBLE false
        emit_kv ERROR "Issue #$ISSUE_NUM has a report title prefix ([... Report]); not a fix-issue candidate"
        exit 2
    fi

    # Fetch the last comment to detect concurrent locks. Using --slurp so
    # `jq` sees a single array-of-arrays and can select the globally-last
    # comment via `add // [] | .[-1]`. The older `--jq '.[-1].body'` pattern
    # ran the filter per page and was only accidentally correct because the
    # last page contains the globally-last comment. See `prose_open_blockers`
    # in `blocker-helpers.sh` for the canonical reference use of this `add // []`
    # slurp pattern.
    LAST_COMMENT=$(gh api --paginate --slurp "repos/${REPO}/issues/${ISSUE_NUM}/comments" 2>/dev/null \
        | jq -r 'add // [] | .[-1].body // empty') || {
        emit_kv ELIGIBLE false
        emit_kv ERROR "Failed to fetch comments for issue #$ISSUE_NUM"
        exit 2
    }

    TRIMMED=$(echo "$LAST_COMMENT" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

    # Reject when the issue is locked by a concurrent /fix-issue run.
    if [ "$TRIMMED" = "IN PROGRESS" ]; then
        emit_kv ELIGIBLE false
        emit_kv ERROR "Issue #$ISSUE_NUM is locked by another /fix-issue run (last comment: IN PROGRESS)"
        exit 2
    fi

    BLOCKERS=$(all_open_blockers "$ISSUE_NUM")
    if [ -n "$BLOCKERS" ]; then
        # Format as comma-separated #N list for the error message
        FORMATTED=$(echo "$BLOCKERS" | tr ' ' '\n' | sed 's/^/#/' | paste -sd ',' -)
        emit_kv ELIGIBLE false
        emit_kv ERROR "Issue #$ISSUE_NUM is blocked by open dependencies: $FORMATTED"
        exit 2
    fi

    # Eligibility confirmed — acquire lock + best-effort title rename, emit
    # unified contract, exit (terminal).
    lock_and_rename_then_emit "$ISSUE_NUM" "$ISSUE_TITLE"
fi

