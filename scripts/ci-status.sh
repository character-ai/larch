#!/usr/bin/env bash
# ci-status.sh — Check CI status and main branch advancement for a PR.
#
# Fetches the configured base ref, checks PR CI status via `gh pr checks --json`,
# and counts commits behind the configured base ref.
#
# Usage:
#   ci-status.sh --pr NUMBER --repo OWNER/REPO [--base-remote NAME] [--base-ref BRANCH] [--empty-checks-grace SECONDS]
#
# Outputs (always all four lines, in order):
#   CI_STATUS=pass|fail|pending|merged|NO_CHECKS
#   BEHIND_COUNT=<N>
#   FAILED_RUN_ID=<id>    (empty string if no failure)
#   CONFLICTED=<true|false>
#
# Exit codes:
#   0 — always (status is communicated via output lines)

set -uo pipefail
# Note: not using set -e — we need to guarantee output on all paths

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

# Defaults — these will always be emitted even on unexpected errors
CI_STATUS="pending"
BEHIND_COUNT="0"
FAILED_RUN_ID=""
CONFLICTED="false"
MERGE_STATE_STATUS=""

# Ensure output is always emitted, even on unexpected errors
trap 'emit_kv CI_STATUS "$CI_STATUS"; emit_kv BEHIND_COUNT "$BEHIND_COUNT"; emit_kv FAILED_RUN_ID "$FAILED_RUN_ID"; emit_kv CONFLICTED "$CONFLICTED"' EXIT

usage() { larch_err "Usage: ci-status.sh --pr NUMBER --repo OWNER/REPO"; }

PR_NUMBER=""
REPO=""
BASE_REMOTE="origin"
BASE_REF="main"
EMPTY_CHECKS_GRACE=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --pr) PR_NUMBER="${2:?--pr requires a value}"; shift 2 ;;
        --repo) REPO="${2:?--repo requires a value}"; shift 2 ;;
        --base-remote) BASE_REMOTE="${2:?--base-remote requires a value}"; shift 2 ;;
        --base-ref) BASE_REF="${2:?--base-ref requires a value}"; shift 2 ;;
        --empty-checks-grace) EMPTY_CHECKS_GRACE="${2:?--empty-checks-grace requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "Unknown option: $1"; usage; CI_STATUS="error"; exit 0 ;;
    esac
done

if [[ -z "$PR_NUMBER" ]] || [[ -z "$REPO" ]]; then
    larch_err "ERROR: --pr and --repo are required"
    usage; CI_STATUS="error"; exit 0
fi

if ! [[ "$EMPTY_CHECKS_GRACE" =~ ^[0-9]+$ ]]; then
    larch_err "ERROR: --empty-checks-grace must be a non-negative integer"
    CI_STATUS="error"
    exit 0
fi

if [[ ! "$BASE_REMOTE" =~ ^[A-Za-z0-9._/-]+$ ]] || [[ ! "$BASE_REF" =~ ^[A-Za-z0-9._/-]+$ ]]; then
    larch_err "ERROR: --base-remote/--base-ref contain unsupported characters"
    CI_STATUS="error"
    exit 0
fi

BASE_TARGET="${BASE_REMOTE}/${BASE_REF}"

# --- Check if PR has been force-merged (mergeStateStatus on same gh pr view call) ---
PR_JSON=$(gh pr view "$PR_NUMBER" --repo "$REPO" --json state,mergeStateStatus 2>/dev/null || echo "")
PR_STATE=$(echo "$PR_JSON" | jq -r '.state // ""' 2>/dev/null || echo "")
MERGE_STATE_STATUS=$(echo "$PR_JSON" | jq -r '.mergeStateStatus // ""' 2>/dev/null || echo "")
if [[ "$PR_STATE" == "MERGED" ]]; then
    CI_STATUS="merged"
    exit 0
fi

# --- Fetch base ref for staleness check ---
if ! git fetch "$BASE_REMOTE" "$BASE_REF" --quiet 2>/dev/null; then
    # Fetch failed — cannot reliably compute BEHIND_COUNT.
    # Force pending status so the caller retries instead of trusting stale refs.
    larch_err "⚠ git fetch $BASE_REMOTE $BASE_REF failed — reporting pending to force retry"
    CI_STATUS="pending"
    BEHIND_COUNT="0"
    exit 0
fi

# --- Check CI status ---
# Try JSON output first (gh CLI v2.x)
# Use 'bucket' field which is reliably available (pass/fail/pending)
CHECKS_JSON=$(gh pr checks "$PR_NUMBER" --repo "$REPO" --json name,state,bucket,link 2>/dev/null || echo "")

if [[ -n "$CHECKS_JSON" ]] && [[ "$CHECKS_JSON" != "null" ]] \
    && echo "$CHECKS_JSON" | jq -e 'type == "array"' >/dev/null 2>&1; then
    # Parse JSON output
    TOTAL=$(echo "$CHECKS_JSON" | jq 'length' 2>/dev/null || echo "0")

    if [[ "$TOTAL" -eq 0 ]]; then
        if [[ "$EMPTY_CHECKS_GRACE" -gt 0 ]]; then
            sleep "$EMPTY_CHECKS_GRACE"
            CHECKS_JSON=$(gh pr checks "$PR_NUMBER" --repo "$REPO" --json name,state,bucket,link 2>/dev/null || echo "")
            TOTAL=$(echo "$CHECKS_JSON" | jq 'if type == "array" then length else 0 end' 2>/dev/null || echo "0")
        fi
        if [[ "$TOTAL" -eq 0 ]]; then
            if [[ "$EMPTY_CHECKS_GRACE" -gt 0 ]]; then
                CI_STATUS="NO_CHECKS"
            else
                CI_STATUS="pending"
            fi
        else
            FAILED=$(echo "$CHECKS_JSON" | jq '[.[] | select(.bucket == "fail")] | length' 2>/dev/null || echo "0")
            PENDING=$(echo "$CHECKS_JSON" | jq '[.[] | select(.bucket == "pending")] | length' 2>/dev/null || echo "0")

            if [[ "$FAILED" -gt 0 ]]; then
                CI_STATUS="fail"
                FAILED_LINK=$(echo "$CHECKS_JSON" | jq -r '[.[] | select(.bucket == "fail")][0].link // empty' 2>/dev/null || echo "")
                if [[ -n "$FAILED_LINK" ]]; then
                    FAILED_RUN_ID=$(echo "$FAILED_LINK" | grep -oE 'runs/[0-9]+' | head -1 | sed 's/runs\///' || echo "")
                fi
            elif [[ "$PENDING" -gt 0 ]]; then
                CI_STATUS="pending"
            else
                CI_STATUS="pass"
            fi
        fi
    else
        FAILED=$(echo "$CHECKS_JSON" | jq '[.[] | select(.bucket == "fail")] | length' 2>/dev/null || echo "0")
        PENDING=$(echo "$CHECKS_JSON" | jq '[.[] | select(.bucket == "pending")] | length' 2>/dev/null || echo "0")

        if [[ "$FAILED" -gt 0 ]]; then
            CI_STATUS="fail"
            # Extract the run ID from the first failed check's link URL
            # Link format: https://github.com/<owner>/<repo>/actions/runs/<run-id>/job/<job-id>
            FAILED_LINK=$(echo "$CHECKS_JSON" | jq -r '[.[] | select(.bucket == "fail")][0].link // empty' 2>/dev/null || echo "")
            if [[ -n "$FAILED_LINK" ]]; then
                FAILED_RUN_ID=$(echo "$FAILED_LINK" | grep -oE 'runs/[0-9]+' | head -1 | sed 's/runs\///' || echo "")
            fi
        elif [[ "$PENDING" -gt 0 ]]; then
            CI_STATUS="pending"
        else
            CI_STATUS="pass"
        fi
    fi
else
    # Fallback: parse text output
    CHECKS_TEXT=$(gh pr checks "$PR_NUMBER" --repo "$REPO" 2>/dev/null || echo "")

    if [[ -z "$CHECKS_TEXT" ]]; then
        if [[ "$EMPTY_CHECKS_GRACE" -gt 0 ]]; then
            sleep "$EMPTY_CHECKS_GRACE"
            CHECKS_TEXT=$(gh pr checks "$PR_NUMBER" --repo "$REPO" 2>/dev/null || echo "")
        fi
    fi

    if [[ -z "$CHECKS_TEXT" ]]; then
        if [[ "$EMPTY_CHECKS_GRACE" -gt 0 ]]; then
            CI_STATUS="NO_CHECKS"
        else
            CI_STATUS="pending"
        fi
    elif echo "$CHECKS_TEXT" | grep -qiE '\bfail'; then
        CI_STATUS="fail"
        # Try to extract run ID from the URL column
        FAILED_LINK=$(echo "$CHECKS_TEXT" | grep -iE '\bfail' | head -1 | grep -oE 'https://[^ ]+' | head -1 || echo "")
        if [[ -n "$FAILED_LINK" ]]; then
            FAILED_RUN_ID=$(echo "$FAILED_LINK" | grep -oE 'runs/[0-9]+' | head -1 | sed 's/runs\///' || echo "")
        fi
    elif echo "$CHECKS_TEXT" | grep -qiE 'pending|in_progress|queued'; then
        CI_STATUS="pending"
    else
        CI_STATUS="pass"
    fi
fi

# --- Check behind count ---
_behind_out=$("$SCRIPT_DIR/ci-behind-count.sh" --base-remote "$BASE_REMOTE" --base-ref "$BASE_REF" --no-fetch 2>/dev/null || echo "")
BEHIND_COUNT=$(printf '%s\n' "$_behind_out" | awk -F= '/^BEHIND_COUNT=/ { print substr($0, index($0,"=")+1); exit }')
case "$BEHIND_COUNT" in
    ''|*[!0-9]*) BEHIND_COUNT="0" ;;
esac

# --- Git-based merge detection (catches race where git refs update before GitHub API) ---
# If main advanced, check if this PR's squash-merge commit landed.
# Uses fixed-string match for "(#N)" — GitHub's squash-merge subject format.
# Note: only works for squash merges (this project uses --squash exclusively).
# False positive would trigger premature cleanup; remote branch preserved for recovery.
if [[ "$BEHIND_COUNT" -gt 0 ]]; then
    if git log "HEAD..$BASE_TARGET" --oneline 2>/dev/null | grep -Fq "(#${PR_NUMBER})"; then
        CI_STATUS="merged"
        BEHIND_COUNT="0"
        FAILED_RUN_ID=""
    fi
fi

# --- Derive CONFLICTED from mergeStateStatus (conservative for UNKNOWN/empty) ---
case "$MERGE_STATE_STATUS" in
    DIRTY) CONFLICTED="true" ;;
    CLEAN|BEHIND|BLOCKED|UNSTABLE|HAS_HOOKS) CONFLICTED="false" ;;
    *) CONFLICTED="true" ;;
esac
