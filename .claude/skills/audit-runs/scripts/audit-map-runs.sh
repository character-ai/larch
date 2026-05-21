#!/usr/bin/env bash
# audit-map-runs.sh — Map each PR to its run-log directory.
#
# For each PR in --pr-list:
#   1. grep larch-logs/implement/*/manifest.json for "pr_number": N
#   2. Fallback: read parent-issue.md for ISSUE_NUMBER, cross-ref PR body Closes #N
#
# Output: TSV to stdout (no header), one row per PR:
#   pr_number<TAB>run_id<TAB>started_at<TAB>larch_version<TAB>closes_issue
# Empty fields when a PR cannot be mapped.
#
# Usage:
#   audit-map-runs.sh --pr-list N,M,... --repo OWNER/NAME [--log-root PATH]

set -euo pipefail

PR_LIST=""
REPO="character-ai/larch"
LOG_ROOT="larch-logs/implement"

while [ $# -gt 0 ]; do
    case "$1" in
        --pr-list) PR_LIST="$2"; shift 2 ;;
        --repo) REPO="$2"; shift 2 ;;
        --log-root) LOG_ROOT="$2"; shift 2 ;;
        *)
            printf 'audit-map-runs.sh: unknown argument: %s\n' "$1" >&2
            exit 1
            ;;
    esac
done

if [ -z "$PR_LIST" ]; then
    printf 'audit-map-runs.sh: --pr-list is required\n' >&2
    exit 1
fi

if [ ! -d "$LOG_ROOT" ]; then
    printf 'audit-map-runs.sh: log root not found: %s\n' "$LOG_ROOT" >&2
    exit 1
fi

# Split comma-separated list
IFS=',' read -r -a PR_ARRAY <<EOF
$PR_LIST
EOF

for PR_NUM in "${PR_ARRAY[@]}"; do
    PR_NUM=$(printf '%s' "$PR_NUM" | tr -d '[:space:]')
    [ -z "$PR_NUM" ] && continue

    RUN_ID=""
    STARTED_AT=""
    LARCH_VERSION=""
    CLOSES_ISSUE=""

    # Primary: newest manifest.json (by started_at) whose pr_number matches
    MANIFEST_FILE=""
    best_started=""
    for mf in "$LOG_ROOT"/*/manifest.json; do
        [ -f "$mf" ] || continue
        if ! jq -e --argjson pn "$PR_NUM" '(.pr_number | type == "number") and .pr_number == $pn' "$mf" >/dev/null 2>&1; then
            continue
        fi
        st=$(jq -r '.started_at // ""' "$mf" 2>/dev/null || true)
        if [ -z "$MANIFEST_FILE" ] || { [ -n "$st" ] && { [ -z "$best_started" ] || [[ "$st" > "$best_started" ]]; }; }; then
            MANIFEST_FILE="$mf"
            best_started="$st"
        fi
    done

    if [ -n "$MANIFEST_FILE" ]; then
        RUN_DIR=$(dirname "$MANIFEST_FILE")
        RUN_ID=$(basename "$RUN_DIR")
        STARTED_AT=$(jq -r '.started_at // empty' "$MANIFEST_FILE" 2>/dev/null || true)
        LARCH_VERSION=$(jq -r '.larch_version // empty' "$MANIFEST_FILE" 2>/dev/null || true)
        CLOSES_ISSUE=$(jq -r '.closes_issue // empty' "$MANIFEST_FILE" 2>/dev/null || true)
    else
        # Fallback: find via parent-issue.md cross-referenced with PR body Closes #N
        PR_BODY=$(gh pr view "$PR_NUM" --repo "$REPO" --json body --jq '.body // empty' 2>/dev/null || true)
        CLOSES_ISSUE=$(printf '%s' "$PR_BODY" | grep -oiE 'Closes[[:space:]]+#[0-9]+' | grep -oE '[0-9]+$' | head -1 || true)

        if [ -n "$CLOSES_ISSUE" ]; then
            for mf in "$LOG_ROOT"/*/parent-issue.md; do
                [ -f "$mf" ] || continue
                FILE_ISSUE=$(grep -oE 'ISSUE_NUMBER=[0-9]+' "$mf" 2>/dev/null | grep -oE '[0-9]+$' || true)
                if [ "$FILE_ISSUE" = "$CLOSES_ISSUE" ]; then
                    RUN_DIR=$(dirname "$mf")
                    RUN_ID=$(basename "$RUN_DIR")
                    MANIFEST_FILE="$RUN_DIR/manifest.json"
                    if [ -f "$MANIFEST_FILE" ]; then
                        STARTED_AT=$(jq -r '.started_at // empty' "$MANIFEST_FILE" 2>/dev/null || true)
                        LARCH_VERSION=$(jq -r '.larch_version // empty' "$MANIFEST_FILE" 2>/dev/null || true)
                    fi
                    break
                fi
            done
        fi
    fi

    printf '%s\t%s\t%s\t%s\t%s\n' \
        "$PR_NUM" \
        "${RUN_ID:-}" \
        "${STARTED_AT:-}" \
        "${LARCH_VERSION:-}" \
        "${CLOSES_ISSUE:-}"
done
