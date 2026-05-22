#!/usr/bin/env bash
# implement-admission.sh — mechanical /implement Preflight admission gate.
#
# Validates issue state, managed-title prefixes, report-title shape, audit
# label, and open blockers before /implement allocates heavy session state.
#
# Usage:
#   implement-admission.sh --issue N [--repo OWNER/REPO]
#
# Environment:
#   IMPLEMENT_TMPDIR — optional; when set and `parent-issue.md` matches `--issue`,
#     may short-circuit to pass with `RESUME=true` (crash-resume sentinel). When
#     `parent-issue.md` contains `RUN_ID=`, export the same `RUN_ID` or admission
#     re-runs the full gate (see `scripts/implement-admission.md`).
#
# Exit codes:
#   0 — ADMISSION_RESULT=pass (optional RESUME=true)
#   2 — gh/json failure (ADMISSION_ERROR=...) or closed issue
#   4 — open blockers (ADMISSION_RESULT=has-blockers BLOCKERS=...)
#   5 — managed lifecycle title prefix
#   6 — audit-report label
#   7 — [... Report] title pattern
#
# Caller MUST export REPO before sourcing blocker-helpers.sh; this script
# assigns REPO when --repo is omitted (via gh repo view) before sourcing.

set -euo pipefail

# Machine-readable gh JSON must reach stdout for command substitution; disable
# lib-quiet FD redirection for this entrypoint (mirrors parse-prose-blockers.sh).
LARCH_QUIET_DISABLE=1
export LARCH_QUIET_DISABLE

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
# shellcheck source=lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

usage() {
    larch_err "Usage: implement-admission.sh --issue N [--repo OWNER/REPO]"
}

# Single-line values for emit_kv stdout contract (GitHub titles / argv may embed newlines).
admission_kv_value() {
    printf '%s' "$1" | tr '\r\n' '  ' | sed 's/  */ /g;s/^[[:space:]]*//;s/[[:space:]]*$//'
}

ISSUE=""
REPO_ARG=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --issue)
            [[ $# -ge 2 ]] || { usage; emit_kv ADMISSION_ERROR "--issue requires a value"; exit 2; }
            ISSUE="${2:-}"
            shift 2
            ;;
        --repo)
            [[ $# -ge 2 ]] || { usage; emit_kv ADMISSION_ERROR "--repo requires a value"; exit 2; }
            REPO_ARG="${2:-}"
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            if [[ "$1" == *[[:cntrl:]]* ]]; then
                emit_kv ADMISSION_ERROR "unknown option (control characters not allowed in argv tokens)"
            else
                emit_kv ADMISSION_ERROR "unknown option: $(admission_kv_value "$1")"
            fi
            exit 2
            ;;
    esac
done

if [[ -z "$ISSUE" || "$ISSUE" == *[!0-9]* ]]; then
    emit_kv ADMISSION_ERROR "--issue must be a positive integer"
    exit 2
fi

if [[ -n "$REPO_ARG" ]]; then
    REPO="$REPO_ARG"
else
    if ! REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null); then
        emit_kv ADMISSION_ERROR "could not resolve repo (gh repo view failed)"
        exit 2
    fi
fi
export REPO

gh_issue_view_json() {
    gh issue view "$ISSUE" --repo "$REPO" --json title,state,labels 2>/dev/null
}

JSON=""
view_exit=0
JSON=$(gh_issue_view_json) || view_exit=$?
if [[ "$view_exit" -ne 0 ]]; then
    view_exit=0
    JSON=$(gh_issue_view_json) || view_exit=$?
fi
if [[ "$view_exit" -ne 0 ]]; then
    SAFE=$(printf '%s' "$JSON" | tr '\n' ' ' | sed 's/  */ /g')
    emit_kv ADMISSION_ERROR "gh issue view failed: $SAFE"
    exit 2
fi

if ! printf '%s' "$JSON" | jq -e . >/dev/null 2>&1; then
    emit_kv ADMISSION_ERROR "issue json parse failed (malformed gh issue view response)"
    exit 2
fi

STATE=$(printf '%s' "$JSON" | jq -r '.state // empty')
TITLE=$(printf '%s' "$JSON" | jq -r '.title // empty')

if [[ "$STATE" == "CLOSED" ]]; then
    emit_kv ADMISSION_ERROR "issue #$ISSUE is CLOSED"
    exit 2
fi

# Resume sentinel: same session re-run after crash before parent-issue write
# is irrelevant — sentinel matches only when file lists this issue. When
# parent-issue.md records RUN_ID=, require the same RUN_ID in the environment
# so a stale IMPLEMENT_TMPDIR from another session cannot bypass the gate.
if [[ -n "${IMPLEMENT_TMPDIR:-}" && -f "${IMPLEMENT_TMPDIR}/parent-issue.md" ]]; then
    parent_num=$(awk -F= '/^ISSUE_NUMBER=/{print $2; exit}' "${IMPLEMENT_TMPDIR}/parent-issue.md" 2>/dev/null || true)
    parent_num=$(printf '%s' "$parent_num" | tr -d '\r\n')
    parent_run_id=$(awk -F= '/^RUN_ID=/{print $2; exit}' "${IMPLEMENT_TMPDIR}/parent-issue.md" 2>/dev/null || true)
    parent_run_id=$(printf '%s' "$parent_run_id" | tr -d '\r\n')
    if [[ -n "$parent_num" && "$parent_num" == "$ISSUE" ]]; then
        resume_ok=1
        if [[ -n "$parent_run_id" ]]; then
            if [[ -z "${RUN_ID:-}" || "$parent_run_id" != "$RUN_ID" ]]; then
                resume_ok=0
            fi
        fi
        if [[ "$resume_ok" == 1 ]]; then
            emit_kv ADMISSION_RESULT pass
            emit_kv RESUME true
            exit 0
        fi
    fi
fi

has_managed_prefix() {
    local t="$1"
    case "$t" in
        '[IN PROGRESS] '*) return 0 ;;
        '[DONE] '*)        return 0 ;;
        '[STALLED] '*)     return 0 ;;
        *)                 return 1 ;;
    esac
}

has_report_prefix() {
    printf '%s' "$1" | grep -qiE '^\[[^]]*[[:space:]]+report\]'
}

if has_managed_prefix "$TITLE"; then
    emit_kv ADMISSION_RESULT managed-prefix
    emit_kv TITLE "$(admission_kv_value "$TITLE")"
    exit 5
fi

if has_report_prefix "$TITLE"; then
    emit_kv ADMISSION_RESULT report-title
    emit_kv TITLE "$(admission_kv_value "$TITLE")"
    exit 7
fi

if printf '%s' "$JSON" | jq -e '.labels // [] | map(.name) | index("audit-report") != null' >/dev/null 2>&1; then
    emit_kv ADMISSION_RESULT audit-report-label
    exit 6
fi

# shellcheck disable=SC1091
# shellcheck source=blocker-helpers.sh
if ! source "$SCRIPT_DIR/blocker-helpers.sh" 2>/dev/null; then
    emit_kv ADMISSION_ERROR "failed to source blocker-helpers.sh"
    exit 2
fi

BLOCKERS=$(all_open_blockers "$ISSUE" || true)
BLOCKERS=$(printf '%s' "$BLOCKERS" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
if [[ -n "$BLOCKERS" ]]; then
    emit_kv ADMISSION_RESULT has-blockers
    emit_kv BLOCKERS "$BLOCKERS"
    exit 4
fi

emit_kv ADMISSION_RESULT pass
exit 0
