#!/usr/bin/env bash
# merge-pr.sh - Squash-merge a PR, trying --admin first after safety gates.
#
# Checks whether the branch is behind main and whether CI is ready before
# any merge attempt. If CI is confirmed passing and the branch is
# up-to-date, tries `gh pr merge --squash --admin` first, then falls back
# to a plain squash merge if the privileged attempt fails. When
# --no-admin-fallback is set, skips the privileged attempt and tries only
# the plain squash merge; if that fails, returns MERGE_RESULT=policy_denied.
#
# CRITICAL: The --admin flag overrides ALL branch protection rules
# including review requirements. It is ONLY used after confirming:
#   1. All CI checks are passing (bucket == "pass" for every check)
#   2. The branch is up-to-date with main and in an admin-eligible state
# This is the canonical --admin implementation.
# See skills/implement/SKILL.md Step 12b for usage documentation.
#
# Usage:
#   merge-pr.sh --pr NUMBER --repo OWNER/REPO [--no-admin-fallback]
#
# --no-admin-fallback: opts out of the --admin-first attempt. When set,
#   the script reaches the same admin-eligible gate (CI good + branch
#   fresh) but invokes only `gh pr merge --squash`; if that plain merge
#   fails, it emits MERGE_RESULT=policy_denied. This applies to ALL
#   admin-eligible mergeStateStatus values (CLEAN, UNSTABLE, HAS_HOOKS,
#   BLOCKED, BEHIND) — not just review-required denials.
#
# Outputs (key=value to stdout, always emitted via EXIT trap):
#   MERGE_RESULT=merged|admin_merged|main_advanced|ci_not_ready|version_already_published|admin_failed|policy_denied|error
#   ERROR=<message>    (empty string when no error)
#
# version_already_published fires only after the PR-head-OID precondition
# succeeds, the branch range contains a literal "Bump version to X.Y.Z" commit,
# and origin/main's published plugin.json version matches that local bump.
#
# Exit codes:
#   0 — always (result communicated via MERGE_RESULT)
#   1 — usage/argument error (no output emitted)

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
# shellcheck source=scripts/lib-net.sh
source "$SCRIPT_DIR/lib-net.sh"
REDACT_HELPER="$REPO_ROOT/scripts/redact-secrets.sh"
REDACT_TMPDIR_HELPER="$REPO_ROOT/scripts/redact-tmpdir-paths.sh"

usage() { larch_err "Usage: merge-pr.sh --pr NUMBER --repo OWNER/REPO [--no-admin-fallback]"; }

redact_merge_diagnostic() {
    local err_text="$1"
    local redacted
    local status=0
    if [[ ! -x "$REDACT_HELPER" ]] || [[ ! -x "$REDACT_TMPDIR_HELPER" ]]; then
        printf '%s' 'merge diagnostic redaction unavailable'
        return 0
    fi
    redacted=$(printf '%s' "$err_text" | "$REDACT_TMPDIR_HELPER" | "$REDACT_HELPER") || status=$?
    if [ "$status" -ne 0 ]; then
        printf '%s' 'merge diagnostic redaction unavailable'
        return 0
    fi
    case "$redacted" in
        *'[content truncated'*)
            printf '%s' 'merge diagnostic redaction unavailable'
            return 0
            ;;
    esac
    printf '%s' "$redacted" | tr '\n' ' ' | head -c 500
}

# --- Parse arguments (before installing EXIT trap) ---
PR_NUMBER=""
REPO=""
NO_ADMIN_FALLBACK=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --pr) PR_NUMBER="${2:?--pr requires a value}"; shift 2 ;;
        --repo) REPO="${2:?--repo requires a value}"; shift 2 ;;
        --no-admin-fallback) NO_ADMIN_FALLBACK=true; shift ;;
        --help) usage; exit 0 ;;
        *) larch_err "Unknown option: $1"; usage; exit 1 ;;
    esac
done

if [[ -z "$PR_NUMBER" ]] || [[ -z "$REPO" ]]; then
    larch_err "ERROR: --pr and --repo are required"
    usage; exit 1
fi

# --- Output defaults (emitted via trap on any exit after validation) ---
MERGE_RESULT="error"
ERROR="merge-pr.sh exited unexpectedly"

# shellcheck disable=SC2329,SC2317  # invoked via EXIT trap
emit_output() {
    emit_kv MERGE_RESULT "$MERGE_RESULT"
    emit_kv ERROR "$ERROR"
}
trap 'emit_output' EXIT

# UNKNOWN/empty-state retry budgets for mergeStateStatus. Asymmetric on purpose:
# the initial probe runs against a cold cache and needs more propagation tolerance,
# while post-force-push runs immediately after a known recent write so 3 retries
# suffice for transient propagation delay (#2342). Update call sites together.
MERGE_PR_INITIAL_UNKNOWN_RETRIES=4
MERGE_PR_POST_PUSH_UNKNOWN_RETRIES=3

refresh_pr_info() {
    local view_fail_file
    view_fail_file=$(mktemp "${TMPDIR:-/tmp}/merge-pr-view.XXXXXX")
    if with_transient_retry transient_envelope_predicate_none "$view_fail_file" \
        gh pr view "$PR_NUMBER" --repo "$REPO" --json mergeStateStatus,headRefOid; then
        PR_INFO=$_WTR_OUT
    else
        PR_INFO=""
    fi
    rm -f "$view_fail_file"
    MERGE_STATE=$(echo "$PR_INFO" | jq -r '.mergeStateStatus // ""' 2>/dev/null || echo "")
    PR_HEAD_OID=$(echo "$PR_INFO" | jq -r '.headRefOid // ""' 2>/dev/null || echo "")
}

# Callers must re-check MERGE_STATE, not $?, after this helper returns.
retry_pr_info_unknown_recovery() {
    local max_retries="$1"
    local attempt=0
    while [ "$attempt" -lt "$max_retries" ]; do
        sleep 5
        refresh_pr_info
        if [ -n "$MERGE_STATE" ] && [ "$MERGE_STATE" != "UNKNOWN" ]; then
            return 0
        fi
        attempt=$((attempt + 1))
    done
}

refresh_ci_state() {
    local json_fail_file text_fail_file fail_content checks_json_transient_exhausted=false

    # Use gh pr checks --json with bucket field (consistent with ci-status.sh)
    json_fail_file=$(mktemp "${TMPDIR:-/tmp}/merge-pr-checks-json.XXXXXX")
    if with_transient_retry transient_envelope_predicate_none "$json_fail_file" \
        gh pr checks "$PR_NUMBER" --repo "$REPO" --json name,state,bucket,link; then
        CHECKS_JSON=$_WTR_OUT
    else
        fail_content=$(cat "$json_fail_file" 2>/dev/null || true)
        if is_transient_net_signature "$fail_content"; then
            CHECKS_JSON=""
            checks_json_transient_exhausted=true
        else
            CHECKS_JSON=$_WTR_OUT
        fi
    fi
    rm -f "$json_fail_file"

    CI_GOOD=false
    if [[ -n "$CHECKS_JSON" ]] && [[ "$CHECKS_JSON" != "null" ]] \
        && echo "$CHECKS_JSON" | jq -e 'type == "array"' >/dev/null 2>&1; then
        TOTAL=$(echo "$CHECKS_JSON" | jq 'length' 2>/dev/null || echo "0")

        if [[ "$TOTAL" -eq 0 ]]; then
            # Zero checks — conservative: treat as not ready
            CI_GOOD=false
        else
            # Require every check to have bucket == "pass" (not just absence of fail/pending).
            # This rejects cancelled, skipping, or any other non-pass bucket.
            PASSED=$(echo "$CHECKS_JSON" | jq '[.[] | select(.bucket == "pass")] | length' 2>/dev/null || echo "0")

            if [[ "$PASSED" -eq "$TOTAL" ]]; then
                CI_GOOD=true
            fi
        fi
    elif [[ "$checks_json_transient_exhausted" == "true" ]]; then
        CHECKS_TEXT=""
        # Exhausted transient on JSON checks — skip text fallback; keep CI_GOOD=false.
    else
        # Fallback: parse text output — conservative: only accept if all lines show pass
        text_fail_file=$(mktemp "${TMPDIR:-/tmp}/merge-pr-checks-text.XXXXXX")
        if with_transient_retry transient_envelope_predicate_none "$text_fail_file" \
            gh pr checks "$PR_NUMBER" --repo "$REPO"; then
            CHECKS_TEXT=$_WTR_OUT
        else
            fail_content=$(cat "$text_fail_file" 2>/dev/null || true)
            if is_transient_net_signature "$fail_content"; then
                CHECKS_TEXT=""
            else
                CHECKS_TEXT=$_WTR_OUT
            fi
        fi
        rm -f "$text_fail_file"
        if [[ -n "$CHECKS_TEXT" ]]; then
            if ! echo "$CHECKS_TEXT" | grep -qiE '\bfail|pending|in_progress|queued|cancelled|skipping'; then
                CI_GOOD=true
            fi
        fi
        # Empty or unparseable — conservative: treat as not ready
    fi
}

# --- Fetch PR metadata (mergeStateStatus + headRefOid) in one compound call ---
refresh_pr_info

# Empty or UNKNOWN mergeStateStatus = could not determine merge state yet.
# Retry with the initial UNKNOWN/empty-state budget before failing closed as
# error; empty usually reflects gh API/network failure, UNKNOWN is GitHub uncertainty.
# Routing through the admin-eligible gate below would mis-emit main_advanced
# with a misleading "Branch mergeStateStatus is " (empty trailing) error and
# nudge callers toward a useless rebase. Treat as the existing `error` outcome
# so the orchestrator bails to its error-handling path.
if [[ -z "$MERGE_STATE" ]] || [[ "$MERGE_STATE" == "UNKNOWN" ]]; then
    retry_pr_info_unknown_recovery "$MERGE_PR_INITIAL_UNKNOWN_RETRIES"
fi

if [[ -z "$MERGE_STATE" ]] || [[ "$MERGE_STATE" == "UNKNOWN" ]]; then
    MERGE_RESULT="error"
    ERROR="could not read mergeStateStatus from gh pr view --json mergeStateStatus,headRefOid (state=\"$MERGE_STATE\") after ${MERGE_PR_INITIAL_UNKNOWN_RETRIES} retries"
    exit 0
fi

# --- Re-verify CI before attempting --admin ---
refresh_ci_state

if [[ "$CI_GOOD" != "true" ]]; then
    MERGE_RESULT="ci_not_ready"
    ERROR="CI checks are not all passing"
    exit 0
fi

# CLEAN = mergeable normally; UNSTABLE = CI passed but review not approved;
# BLOCKED = review/policy block (--admin handles this); HAS_HOOKS = has pre-receive hooks;
# BEHIND = branch behind base but conflict-free (admin-eligible after CI pass).
# empty/UNKNOWN are handled above; remaining non-admin-eligible states
# (e.g. DIRTY, DRAFT, or any future GitHub-added value) → main_advanced
# to retry after updating the branch.
if [[ "$MERGE_STATE" != "CLEAN" ]] && [[ "$MERGE_STATE" != "UNSTABLE" ]] && [[ "$MERGE_STATE" != "HAS_HOOKS" ]] && [[ "$MERGE_STATE" != "BLOCKED" ]] && [[ "$MERGE_STATE" != "BEHIND" ]]; then
    MERGE_RESULT="main_advanced"
    ERROR="Branch mergeStateStatus is $MERGE_STATE"
    exit 0
fi

# --- Same-version bump race gate ---
if [[ -z "$PR_HEAD_OID" ]]; then
    MERGE_RESULT="error"
    ERROR="could not resolve PR head OID via gh pr view"
    exit 0
fi

flush_recovery_is_logs_only() {
    local base_oid="$1"
    local diff_paths=""

    diff_paths=$(git diff --name-only "${base_oid}..HEAD" 2>/dev/null || echo "")
    [[ -n "$diff_paths" ]] || return 1
    ! printf '%s\n' "$diff_paths" | grep -qv '^larch-logs/' 2>/dev/null
}

LOCAL_HEAD=$(git rev-parse HEAD 2>/dev/null || echo "")
if [[ -z "$LOCAL_HEAD" ]] || [[ "$LOCAL_HEAD" != "$PR_HEAD_OID" ]]; then
    # Check whether local HEAD is ahead of the PR head exclusively by
    # larch-log flush commits. That pattern arises when larch-log-flush.sh
    # tail calls fire after gh pr create, advancing local HEAD beyond the
    # OID GitHub recorded for the PR.
    _flush_recoverable=false
    if [[ -n "$LOCAL_HEAD" ]]; then
        FLUSH_AHEAD=$(git log --format='%s' "${PR_HEAD_OID}..HEAD" 2>/dev/null || echo "")
        FLUSH_COUNT=$(printf '%s\n' "$FLUSH_AHEAD" | grep -c . 2>/dev/null || true)
        if [[ "$FLUSH_COUNT" -gt 0 ]] && [[ "$FLUSH_COUNT" -le 5 ]] \
            && ! printf '%s\n' "$FLUSH_AHEAD" | grep -qv '^chore(larch-logs): flush ' \
            && flush_recovery_is_logs_only "$PR_HEAD_OID" \
            && git merge-base --is-ancestor "$PR_HEAD_OID" HEAD 2>/dev/null; then
            _flush_recoverable=true
        fi
    fi
    if [[ "$_flush_recoverable" == "true" ]]; then
        FORCE_OUT=$("$SCRIPT_DIR/git-force-push.sh" --expected-remote-oid "$PR_HEAD_OID" 2>&1 || true)
        PUSHED=$(printf '%s\n' "$FORCE_OUT" | awk -F= '/^PUSHED=/ { print $2 }')
        FORCE_STATUS=$(printf '%s\n' "$FORCE_OUT" | awk -F= '/^STATUS=/ { print $2 }')
        if [[ "$PUSHED" != "true" ]]; then
            MERGE_RESULT="error"
            FORCE_OUT_ONE_LINE=$(printf '%s' "$FORCE_OUT" | tr '\n' ' ')
            ERROR="local HEAD ($LOCAL_HEAD) is ahead of PR head OID ($PR_HEAD_OID) by flush commits only; force-push failed (status=${FORCE_STATUS:-unknown}; output=${FORCE_OUT_ONE_LINE})"
            exit 0
        fi
        # Re-read PR metadata after the force-push advanced the remote HEAD.
        refresh_pr_info
        LOCAL_HEAD=$(git rev-parse HEAD 2>/dev/null || echo "")
        if [[ -z "$LOCAL_HEAD" ]] || [[ "$LOCAL_HEAD" != "$PR_HEAD_OID" ]]; then
            MERGE_RESULT="error"
            ERROR="local HEAD ($LOCAL_HEAD) does not match PR head OID ($PR_HEAD_OID) after force-push recovery"
            exit 0
        fi
        # GitHub's API often returns UNKNOWN immediately after a push due to
        # propagation delay (#2342). Retry briefly before treating as a hard
        # error so transient post-push UNKNOWN states don't stall the merge.
        if [[ -z "$MERGE_STATE" ]] || [[ "$MERGE_STATE" == "UNKNOWN" ]]; then
            retry_pr_info_unknown_recovery "$MERGE_PR_POST_PUSH_UNKNOWN_RETRIES"
        fi
        if [[ -z "$MERGE_STATE" ]] || [[ "$MERGE_STATE" == "UNKNOWN" ]]; then
            MERGE_RESULT="error"
            ERROR="mergeStateStatus still UNKNOWN after ${MERGE_PR_POST_PUSH_UNKNOWN_RETRIES} retries post-force-push (state=\"$MERGE_STATE\")"
            exit 0
        fi
        refresh_ci_state
        if [[ "$CI_GOOD" != "true" ]]; then
            MERGE_RESULT="ci_not_ready"
            ERROR="CI checks are not all passing after force-push recovery"
            exit 0
        fi
        if [[ "$MERGE_STATE" != "CLEAN" ]] && [[ "$MERGE_STATE" != "UNSTABLE" ]] && [[ "$MERGE_STATE" != "HAS_HOOKS" ]] && [[ "$MERGE_STATE" != "BLOCKED" ]] && [[ "$MERGE_STATE" != "BEHIND" ]]; then
            MERGE_RESULT="main_advanced"
            ERROR="Branch mergeStateStatus is $MERGE_STATE after force-push recovery"
            exit 0
        fi
    else
        MERGE_RESULT="error"
        ERROR="local HEAD ($LOCAL_HEAD) does not match PR head OID ($PR_HEAD_OID); refusing to evaluate same-version gate"
        exit 0
    fi
fi

fetch_fail_file=$(mktemp "${TMPDIR:-/tmp}/merge-pr-fetch.XXXXXX")
if with_transient_retry transient_envelope_predicate_none "$fetch_fail_file" \
    git fetch origin main --quiet; then
  FETCH_EXIT=0
else
  FETCH_EXIT=$_WTR_RC
fi
rm -f "$fetch_fail_file"
if [[ "$FETCH_EXIT" -ne 0 ]]; then
    MERGE_RESULT="error"
    ERROR="git fetch origin main failed; cannot verify same-version race"
    exit 0
fi

BUMP_SUBJECT=$(git log --format='%s' origin/main..HEAD 2>/dev/null | grep -E '^Bump version to [0-9]+\.[0-9]+\.[0-9]+$' | head -n1 || true)
if [[ -n "$BUMP_SUBJECT" ]]; then
    [[ "$BUMP_SUBJECT" =~ ^Bump\ version\ to\ ([0-9]+\.[0-9]+\.[0-9]+)$ ]]
    LOCAL_VERSION="${BASH_REMATCH[1]}"

    ORIGIN_VERSION=$(git show origin/main:.claude-plugin/plugin.json 2>/dev/null | jq -r -e '.version // empty' 2>/dev/null || echo "")
    # Validate as semver before composing the single-line ERROR string.
    if [[ ! "$ORIGIN_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        MERGE_RESULT="error"
        ERROR="could not parse origin/main published version (got: '${ORIGIN_VERSION//$'\n'/ }')"
        exit 0
    fi

    if [[ "$ORIGIN_VERSION" == "$LOCAL_VERSION" ]]; then
        MERGE_RESULT="version_already_published"
        ERROR="origin/main HEAD already bumped to $LOCAL_VERSION; rebase and re-bump"
        exit 0
    fi

    if ! git merge-base --is-ancestor origin/main HEAD 2>/dev/null; then
        MERGE_RESULT="main_advanced"
        ERROR="origin/main advanced to a different version; rebase needed"
        exit 0
    fi
fi

# --- Pre-merge re-fetch: tighten the TOCTOU window on the same-version race gate ---
# Between the version check above and the merge call below, a concurrent runner could
# land the same version on main. A second fetch immediately before the merge shrinks
# the race window to the network latency of the merge API call itself.
if [[ -n "$BUMP_SUBJECT" ]]; then
    premerge_fetch_fail_file=$(mktemp "${TMPDIR:-/tmp}/merge-pr-premerge-fetch.XXXXXX")
    if with_transient_retry transient_envelope_predicate_none "$premerge_fetch_fail_file" \
        git fetch origin main --quiet; then
        PREMERGE_FETCH_EXIT=0
    else
        PREMERGE_FETCH_EXIT=$_WTR_RC
    fi
    rm -f "$premerge_fetch_fail_file"
    if [[ "$PREMERGE_FETCH_EXIT" -ne 0 ]]; then
        MERGE_RESULT="error"
        ERROR="git fetch origin main failed (pre-merge re-fetch)"
        exit 0
    fi
    PREMERGE_ORIGIN_VERSION=$(git show origin/main:.claude-plugin/plugin.json 2>/dev/null | jq -r -e '.version // empty' 2>/dev/null || echo "")
    if [[ "$PREMERGE_ORIGIN_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] && [[ "$PREMERGE_ORIGIN_VERSION" == "$LOCAL_VERSION" ]]; then
        MERGE_RESULT="version_already_published"
        ERROR="origin/main HEAD already bumped to $LOCAL_VERSION (pre-merge re-fetch); rebase and re-bump"
        exit 0
    fi
fi

# --- All checks passed — merge with selected privilege path ---
if [[ "$NO_ADMIN_FALLBACK" == "true" ]]; then
    merge_fail_file=$(mktemp "${TMPDIR:-/tmp}/merge-pr-merge.XXXXXX")
    if with_transient_retry transient_envelope_predicate_none "$merge_fail_file" \
        gh pr merge "$PR_NUMBER" --repo "$REPO" --squash; then
        MERGE_EXIT=0
    else
        MERGE_EXIT=$_WTR_RC
    fi
    MERGE_OUTPUT=$_WTR_OUT
    MERGE_FAIL_OUTPUT=$(cat "$merge_fail_file" 2>/dev/null || true)
    rm -f "$merge_fail_file"

    if [[ $MERGE_EXIT -eq 0 ]]; then
        MERGE_RESULT="merged"
        ERROR=""
        exit 0
    fi

    MERGE_RESULT="policy_denied"
    MERGE_OUTPUT_ONE_LINE=$(redact_merge_diagnostic "${MERGE_FAIL_OUTPUT:-$MERGE_OUTPUT}")
    ERROR="branch protection denied merge; --no-admin-fallback set: $MERGE_OUTPUT_ONE_LINE"
    exit 0
fi

larch_err "ℹ CI is green and branch is fresh. Trying merge with --admin..."
admin_fail_file=$(mktemp "${TMPDIR:-/tmp}/merge-pr-admin.XXXXXX")
if with_transient_retry transient_envelope_predicate_none "$admin_fail_file" \
    gh pr merge "$PR_NUMBER" --repo "$REPO" --squash --admin; then
    ADMIN_EXIT=0
else
    ADMIN_EXIT=$_WTR_RC
fi
ADMIN_OUTPUT=$_WTR_OUT
ADMIN_FAIL_OUTPUT=$(cat "$admin_fail_file" 2>/dev/null || true)
rm -f "$admin_fail_file"

if [[ $ADMIN_EXIT -eq 0 ]]; then
    MERGE_RESULT="admin_merged"
    ERROR=""
    exit 0
fi

larch_err "ℹ Admin merge attempt failed: $(redact_merge_diagnostic "${ADMIN_FAIL_OUTPUT:-$ADMIN_OUTPUT}")"
larch_err "ℹ Retrying merge without --admin..."
merge_fallback_fail_file=$(mktemp "${TMPDIR:-/tmp}/merge-pr-merge-fallback.XXXXXX")
if with_transient_retry transient_envelope_predicate_none "$merge_fallback_fail_file" \
    gh pr merge "$PR_NUMBER" --repo "$REPO" --squash; then
    MERGE_EXIT=0
else
    MERGE_EXIT=$_WTR_RC
fi
MERGE_OUTPUT=$_WTR_OUT
MERGE_FAIL_OUTPUT=$(cat "$merge_fallback_fail_file" 2>/dev/null || true)
rm -f "$merge_fallback_fail_file"

if [[ $MERGE_EXIT -eq 0 ]]; then
    MERGE_RESULT="merged"
    ERROR=""
    exit 0
fi

# Collapse newlines in tool output so ERROR stays a single key=value line —
# emit_output() prints `ERROR=$ERROR` with `echo`, and an embedded newline
# would split it across multiple lines and break key-based parsers downstream.
ADMIN_OUTPUT_ONE_LINE=$(redact_merge_diagnostic "${ADMIN_FAIL_OUTPUT:-$ADMIN_OUTPUT}")
MERGE_OUTPUT_ONE_LINE=$(redact_merge_diagnostic "${MERGE_FAIL_OUTPUT:-$MERGE_OUTPUT}")
MERGE_RESULT="admin_failed"
ERROR="Admin merge failed: $ADMIN_OUTPUT_ONE_LINE; fallback merge failed: $MERGE_OUTPUT_ONE_LINE"
exit 0
