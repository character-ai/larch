#!/usr/bin/env bash
# audit-map-runs.sh — Map each PR to its run-log directory.
#
# For each PR in --pr-list:
#   1. Primary: gh pr view → closing keyword lines (see extract_closing_issue_from_pr_body) → parent-issue.md with ISSUE_NUMBER=N
#   2. Fallback: newest manifest.json whose pr_number matches N (number or string; legacy runs)
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

# Split comma-separated list (no shell expansion — PR_LIST is untrusted data)
IFS=',' read -r -a PR_ARRAY <<<"$PR_LIST"

# Keyword priority: Closes, then Fixes, then Resolves (GitHub treats them equivalently for
# auto-close; order in the body is not semantic). Within one keyword class, multiple distinct
# issue numbers → refuse mapping (stderr MAP_PR_BODY_CLOSING_AMBIGUOUS) instead of picking an
# arbitrary first grep match.
extract_closing_issue_from_pr_body() {
    local body="$1"
    local kw nums uniq n
    for kw in Closes Fixes Resolves; do
        nums=$(printf '%s' "$body" | grep -oiE "${kw}[[:space:]]+#[0-9]+" | grep -oE '[0-9]+$' || true)
        [ -z "$nums" ] && continue
        uniq=$(printf '%s\n' "$nums" | sort -u | sed '/^$/d')
        [ -z "$uniq" ] && continue
        n=$(printf '%s\n' "$uniq" | wc -l | tr -d '[:space:]')
        if [ "$n" -gt 1 ]; then
            printf 'audit-map-runs.sh: MAP_PR_BODY_CLOSING_AMBIGUOUS=true KEYWORD=%s\n' "$kw" >&2
            return 0
        fi
        printf '%s' "$uniq"
        return 0
    done
    return 0
}

manifest_started_epoch() {
    local mf="$1"
    jq -r '(.started_at // "") | (try fromdateiso8601 catch empty)' "$mf" 2>/dev/null || true
}

pick_newest_manifest_among_pr() {
    # Sets global: MANIFEST_FILE
    MANIFEST_FILE=""
    local best_epoch="" cur_epoch mf
    best_epoch=-9223372036854775808
    for mf in "$LOG_ROOT"/*/manifest.json; do
        [ -f "$mf" ] || continue
        if ! jq -e --argjson pn "$PR_NUM" '
            (.pr_number | type) as $t
            | ($t == "number" and .pr_number == $pn)
              or ($t == "string" and ((.pr_number | tonumber) == $pn))
          ' "$mf" >/dev/null 2>&1; then
            continue
        fi
        cur_epoch=$(manifest_started_epoch "$mf")
        if [ -z "$cur_epoch" ]; then
            cur_epoch=-9223372036854775808
        fi
        if [ -z "$MANIFEST_FILE" ] || [ "$cur_epoch" -gt "$best_epoch" ]; then
            MANIFEST_FILE="$mf"
            best_epoch="$cur_epoch"
        fi
    done
}

for PR_NUM in "${PR_ARRAY[@]}"; do
    PR_NUM=$(printf '%s' "$PR_NUM" | tr -d '[:space:]')
    [ -z "$PR_NUM" ] && continue
    if ! printf '%s' "$PR_NUM" | grep -qE '^[1-9][0-9]*$|^0$'; then
        printf 'audit-map-runs.sh: skipping invalid PR token in --pr-list (non-integer): %s\n' "$PR_NUM" >&2
        continue
    fi

    RUN_ID=""
    STARTED_AT=""
    LARCH_VERSION=""
    CLOSES_ISSUE=""

    gh_stderr=$(mktemp "${TMPDIR:-/tmp}/audit-map-gh.XXXXXX")
    PR_BODY=""
    gh_ok=false
    if PR_BODY=$(gh pr view "$PR_NUM" --repo "$REPO" --json body --jq '.body // empty' 2>"$gh_stderr"); then
        gh_ok=true
        rm -f "$gh_stderr"
    else
        printf 'audit-map-runs.sh: MAP_GH_PR_VIEW_FAILED=true REASON=%s\n' "$(tr '\n' ' ' <"$gh_stderr" | sed 's/[[:space:]]\+/ /g')" >&2
        rm -f "$gh_stderr"
    fi

    if [ "$gh_ok" = true ]; then
        CLOSES_ISSUE=$(extract_closing_issue_from_pr_body "$PR_BODY")

        if [ -n "$CLOSES_ISSUE" ]; then
            matches=()
            for mf in "$LOG_ROOT"/*/parent-issue.md; do
                [ -f "$mf" ] || continue
                FILE_ISSUE=$(grep -oE 'ISSUE_NUMBER=[0-9]+' "$mf" 2>/dev/null | grep -oE '[0-9]+$' || true)
                if [ "$FILE_ISSUE" = "$CLOSES_ISSUE" ]; then
                    matches+=("$(dirname "$mf")")
                fi
            done

            if [ "${#matches[@]}" -eq 1 ]; then
                RUN_DIR="${matches[0]}"
                RUN_ID=$(basename "$RUN_DIR")
                MANIFEST_FILE="$RUN_DIR/manifest.json"
                if [ -f "$MANIFEST_FILE" ]; then
                    STARTED_AT=$(jq -r '.started_at // empty' "$MANIFEST_FILE" 2>/dev/null || true)
                    LARCH_VERSION=$(jq -r '.larch_version // empty' "$MANIFEST_FILE" 2>/dev/null || true)
                fi
            elif [ "${#matches[@]}" -gt 1 ]; then
                best_epoch=-9223372036854775808
                for rd in "${matches[@]}"; do
                    mf="$rd/manifest.json"
                    e=-9223372036854775808
                    if [ -f "$mf" ]; then
                        ee=$(manifest_started_epoch "$mf")
                        [ -n "$ee" ] && e="$ee"
                    fi
                    if [ "$e" -gt "$best_epoch" ]; then
                        best_epoch="$e"
                    fi
                done
                winners=()
                for rd in "${matches[@]}"; do
                    mf="$rd/manifest.json"
                    e=-9223372036854775808
                    if [ -f "$mf" ]; then
                        ee=$(manifest_started_epoch "$mf")
                        [ -n "$ee" ] && e="$ee"
                    fi
                    if [ "$e" -eq "$best_epoch" ]; then
                        winners+=("$rd")
                    fi
                done
                if [ "${#winners[@]}" -ne 1 ]; then
                    printf 'audit-map-runs.sh: MAP_PARENT_ISSUE_AMBIGUOUS=true ISSUE=%s MATCHES=%s WINNERS_AT_NEWEST=%s\n' \
                        "$CLOSES_ISSUE" "${#matches[@]}" "${#winners[@]}" >&2
                else
                    RUN_DIR="${winners[0]}"
                    RUN_ID=$(basename "$RUN_DIR")
                    MANIFEST_FILE="$RUN_DIR/manifest.json"
                    if [ -f "$MANIFEST_FILE" ]; then
                        STARTED_AT=$(jq -r '.started_at // empty' "$MANIFEST_FILE" 2>/dev/null || true)
                        LARCH_VERSION=$(jq -r '.larch_version // empty' "$MANIFEST_FILE" 2>/dev/null || true)
                    fi
                fi
            fi
        fi
    fi

    if [ "$gh_ok" = true ] && [ -z "$RUN_ID" ]; then
        MANIFEST_FILE=""
        pick_newest_manifest_among_pr
        if [ -n "$MANIFEST_FILE" ]; then
            RUN_DIR=$(dirname "$MANIFEST_FILE")
            RUN_ID=$(basename "$RUN_DIR")
            STARTED_AT=$(jq -r '.started_at // empty' "$MANIFEST_FILE" 2>/dev/null || true)
            LARCH_VERSION=$(jq -r '.larch_version // empty' "$MANIFEST_FILE" 2>/dev/null || true)
            CLOSES_ISSUE=$(jq -r '.closes_issue // empty' "$MANIFEST_FILE" 2>/dev/null || true)
        fi
    fi

    printf '%s\t%s\t%s\t%s\t%s\n' \
        "$PR_NUM" \
        "${RUN_ID:-}" \
        "${STARTED_AT:-}" \
        "${LARCH_VERSION:-}" \
        "${CLOSES_ISSUE:-}"
done
