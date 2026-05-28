#!/usr/bin/env bash
# audit-resolve-prs.sh — Resolve verbal description to a concrete PR list.
#
# Handles all supported forms:
#   empty / omitted  → since last audit (implicit)
#   since last audit → read most-recent audit-report, parse frontmatter, list PRs after
#   last N PRs       → N most-recently-merged PRs
#   since <ISO>      → PRs merged after that instant
#   #N / PR #N       → exactly one PR
#
# Output KV (stdout):
#   IMPLICIT_SINCE_LAST_AUDIT=true|false
#   PRIOR_REPORT_NUMBER=<N or empty>
#   PR_LIST=N,M,...      (comma-separated, empty on error)
#   PR_COUNT=<N>
#   RESOLVED_ECHO=<human-readable line>
#   ERROR=<empty when ok; human-readable error when PR_LIST is empty>
#
# Exit codes: normal resolution exits 0 (caller reads PR_LIST / ERROR from stdout).
# Unknown argv exits 1 with stderr only — no KV lines on stdout.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=.claude/skills/audit-runs/scripts/audit-title-matcher.sh
. "$SCRIPT_DIR/audit-title-matcher.sh"

REPO="character-ai/larch"
VERBAL=""
SKILL=""

audit_resolve_validate_skill() {
    case "${1:-}" in
        design|implement) return 0 ;;
        "")
            printf 'audit-resolve-prs.sh: --skill is required (allowed: design, implement)\n' >&2
            return 1
            ;;
        *)
            printf 'audit-resolve-prs.sh: --skill must be design or implement (got: %s)\n' "$1" >&2
            return 1
            ;;
    esac
}

while [ $# -gt 0 ]; do
    case "$1" in
        --repo) REPO="$2"; shift 2 ;;
        --verbal-description) VERBAL="$2"; shift 2 ;;
        --skill) SKILL="$2"; shift 2 ;;
        *)
            printf 'audit-resolve-prs.sh: unknown argument: %s\n' "$1" >&2
            exit 1
            ;;
    esac
done

if ! audit_resolve_validate_skill "$SKILL"; then
    exit 1
fi

# Trim whitespace
VERBAL=$(printf '%s' "$VERBAL" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

# Machine-safe single-line KV values (no controls / DEL)
kv_sanitize() {
    printf '%s' "$1" | LC_ALL=C tr -d '\000-\037\177'
}

emit_error() {
    local msg
    msg=$(kv_sanitize "$1")
    printf 'IMPLICIT_SINCE_LAST_AUDIT=false\nPRIOR_REPORT_NUMBER=\nPR_LIST=\nPR_COUNT=0\nRESOLVED_ECHO=\nERROR=%s\n' "$msg"
    exit 0
}

emit_ok() {
    local implicit="$1" prior="$2" pr_list="$3" pr_count="$4" echo_line="$5"
    echo_line=$(kv_sanitize "$echo_line")
    printf 'IMPLICIT_SINCE_LAST_AUDIT=%s\nPRIOR_REPORT_NUMBER=%s\nPR_LIST=%s\nPR_COUNT=%s\nRESOLVED_ECHO=%s\nERROR=\n' \
        "$implicit" "$prior" "$pr_list" "$pr_count" "$echo_line"
    exit 0
}

# Filter merged PR JSON array to skill-appropriate rows (jq filter on .title)
filter_prs_for_skill() {
    local json="$1"
    case "$SKILL" in
        design)
            printf '%s' "$json" | jq '[.[] | select(.title | test("^chore\\(larch-logs\\): design run [0-9A-F-]+$"))]' 2>/dev/null || printf '%s\n' '[]'
            ;;
        implement)
            printf '%s' "$json"
            ;;
    esac
}

# List merged PRs targeting main (paginated REST; mergedAt ISO for jq filters)
fetch_merged_main_prs_json() {
    local owner="${REPO%%/*}"
    local repo="${REPO#*/}"
    local page=1
    local acc='[]'
    local max_page=10000
    while [ "$page" -le "$max_page" ]; do
        local batch
        if ! batch=$(gh api "repos/$owner/$repo/pulls?state=closed&per_page=100&page=$page" \
            --jq '[.[] | select(.merged_at != null and .base.ref == "main") | {number: .number, mergedAt: .merged_at, title: .title}]' 2>/dev/null); then
            printf 'audit-resolve-prs: gh api pulls page %s failed\n' "$page" >&2
            return 1
        fi
        local n
        n=$(printf '%s' "$batch" | jq 'length' 2>/dev/null || echo 0)
        if [ "${n:-0}" -eq 0 ]; then
            break
        fi
        acc=$(jq -n --argjson a "$acc" --argjson b "$batch" '$a + $b' 2>/dev/null || printf '%s\n' "$acc")
        if [ "${n:-0}" -lt 100 ]; then
            break
        fi
        page=$((page + 1))
    done
    if [ "$page" -gt "$max_page" ]; then
        printf 'audit-resolve-prs: merged-PR pagination exceeded safety cap (%s pages)\n' "$max_page" >&2
        return 1
    fi
  filter_prs_for_skill "$(printf '%s' "$acc" | jq 'unique_by(.number) | sort_by(.mergedAt)' 2>/dev/null || printf '%s\n' '[]')"
}

# ---- "since last audit" helper ----
resolve_since_last_audit() {
    local implicit="$1"

    # Read audit-report issues; pick most recent whose title matches this skill
    PRIOR_BODY=$(gh issue list --state all --label audit-report --repo "$REPO" \
        --json number,title,body,createdAt \
        --jq '[.[] | select(.title != null)] | sort_by(.createdAt) | reverse' 2>/dev/null || true)

    if [ -z "$PRIOR_BODY" ] || [ "$PRIOR_BODY" = "null" ] || [ "$PRIOR_BODY" = "[]" ]; then
        emit_error "no prior audit-report issue found for --skill=${SKILL}"
    fi

    PRIOR_NUM=""
    PRIOR_ISSUE_BODY=""
    while IFS= read -r row; do
        [ -z "$row" ] && continue
        t=$(printf '%s' "$row" | jq -r '.title // empty' 2>/dev/null || true)
        if match_audit_report_title --skill "$SKILL" --title "$t"; then
            PRIOR_NUM=$(printf '%s' "$row" | jq -r '.number // empty' 2>/dev/null || true)
            PRIOR_ISSUE_BODY=$(printf '%s' "$row" | jq -r '.body // empty' 2>/dev/null || true)
            break
        fi
    done < <(printf '%s' "$PRIOR_BODY" | jq -c '.[]' 2>/dev/null || true)

    if [ -z "$PRIOR_NUM" ]; then
        emit_error "no prior audit-report issue found for --skill=${SKILL}"
    fi

    # Parse audited_pr_range.last from YAML frontmatter (between --- markers)
    LAST_PR=$(printf '%s' "$PRIOR_ISSUE_BODY" \
        | awk '/^---$/{f=!f;next} f && /audited_pr_range:/{in_range=1} in_range && /[[:space:]]last:/{gsub(/.*last:[[:space:]]*/,""); print; exit}')
    # Strip YAML quoting / whitespace; require a numeric PR id
    LAST_PR=$(printf '%s' "$LAST_PR" | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | sed 's/^"\([0-9][0-9]*\)"$/\1/;s/^'"'"'\([0-9][0-9]*\)'"'"'$/\1/')
    if ! printf '%s' "$LAST_PR" | grep -qE '^[0-9]+$'; then
        emit_error "prior audit-report #${PRIOR_NUM} has malformed or missing frontmatter (audited_pr_range.last)"
    fi

    # Get mergedAt for LAST_PR
    MERGED_AT=$(gh pr view "$LAST_PR" --repo "$REPO" --json mergedAt --jq '.mergedAt // empty' 2>/dev/null || true)
    if [ -z "$MERGED_AT" ]; then
        emit_error "could not get mergedAt for prior PR #${LAST_PR}"
    fi

    # List PRs merged after MERGED_AT
    if ! ALL_MERGED=$(fetch_merged_main_prs_json); then
        emit_error "gh api failed listing merged PRs (network or auth)"
    fi

    PR_JSON=$(printf '%s' "$ALL_MERGED" | jq --arg m "$MERGED_AT" '[.[] | select(.mergedAt > $m)] | sort_by(.mergedAt) | [.[].number]' 2>/dev/null || true)

    if [ -z "$PR_JSON" ] || [ "$PR_JSON" = "[]" ]; then
        emit_error "no new PRs merged after prior audit (last PR: #${LAST_PR}, skill=${SKILL})"
    fi

    PR_LIST=$(printf '%s' "$PR_JSON" | jq -r 'join(",")' 2>/dev/null || true)
    PR_COUNT=$(printf '%s' "$PR_JSON" | jq 'length' 2>/dev/null || echo 0)

    if [ -z "$PR_LIST" ] || [ "${PR_COUNT:-0}" -eq 0 ]; then
        emit_error "no new PRs merged after prior audit (last PR: #${LAST_PR}, skill=${SKILL})"
    fi

    if [ "$implicit" = "true" ]; then
        ECHO_LINE="Resolved since last audit (--skill=${SKILL}, implicit default: empty/omitted positional) to: [$(printf '%s' "$PR_JSON" | jq -r '[.[] | "#\(.)"] | join(", ")')]. Proceeding."
    else
        ECHO_LINE="Resolved since last audit (--skill=${SKILL}) to: [$(printf '%s' "$PR_JSON" | jq -r '[.[] | "#\(.)"] | join(", ")')]. Proceeding."
    fi

    emit_ok "$implicit" "$PRIOR_NUM" "$PR_LIST" "$PR_COUNT" "$ECHO_LINE"
}

# ---- Dispatch on form ----
if [ -z "$VERBAL" ]; then
    resolve_since_last_audit "true"
fi

if [ "$VERBAL" = "since last audit" ]; then
    resolve_since_last_audit "false"
fi

# "last N PRs"
if printf '%s' "$VERBAL" | grep -qE '^last[[:space:]]+[0-9]+[[:space:]]+PRs?$'; then
    N=$(printf '%s' "$VERBAL" | grep -oE '[0-9]+')
    if ! ALL_MERGED=$(fetch_merged_main_prs_json); then
        emit_error "gh api failed listing merged PRs (network or auth)"
    fi
    PR_JSON=$(printf '%s' "$ALL_MERGED" | jq --argjson n "$N" \
        'sort_by(.mergedAt) | if ($n <= 0) then [] else .[-($n):] end | [.[].number]' 2>/dev/null || true)
    if [ -z "$PR_JSON" ] || [ "$PR_JSON" = "[]" ]; then
        emit_error "empty PR list after merge-time sort (last ${N} PRs, skill=${SKILL})"
    fi
    PR_LIST=$(printf '%s' "$PR_JSON" | jq -r 'join(",")' 2>/dev/null || true)
    PR_COUNT=$(printf '%s' "$PR_JSON" | jq 'length' 2>/dev/null || echo 0)
    if [ -z "$PR_LIST" ] || [ "${PR_COUNT:-0}" -eq 0 ]; then
        emit_error "empty PR list after merge-time sort (last ${N} PRs, skill=${SKILL})"
    fi
    ECHO_LINE="Resolved last $N PRs (--skill=${SKILL}) to: [$(printf '%s' "$PR_JSON" | jq -r '[.[] | "#\(.)"] | join(", ")')]. Proceeding."
    emit_ok "false" "" "$PR_LIST" "$PR_COUNT" "$ECHO_LINE"
fi

# "since <ISO8601 instant>" — require full date+time (+ optional fractional sec) + Z or ±HH:MM (reject date-only prefixes)
if printf '%s' "$VERBAL" | grep -qE '^since[[:space:]]+'; then
    TS=$(printf '%s' "$VERBAL" | sed 's/^since[[:space:]]*//')
    if ! printf '%s' "$TS" | grep -qE '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}(:[0-9]{2})?(\.[0-9]+)?(Z|[+-][0-9]{2}:[0-9]{2})$'; then
        emit_error "since <ISO> must be a full instant (YYYY-MM-DDThh:mm[:ss][.frac][Z|±hh:mm]); got: $TS"
    fi
    if ! ALL_MERGED=$(fetch_merged_main_prs_json); then
        emit_error "gh api failed listing merged PRs (network or auth)"
    fi
    PR_JSON=$(printf '%s' "$ALL_MERGED" | jq --arg t "$TS" '[.[] | select(.mergedAt > $t)] | sort_by(.mergedAt) | [.[].number]' 2>/dev/null || true)
    if [ -z "$PR_JSON" ] || [ "$PR_JSON" = "[]" ]; then
        emit_error "no PRs merged after $TS (or empty gh result, skill=${SKILL})"
    fi
    PR_LIST=$(printf '%s' "$PR_JSON" | jq -r 'join(",")' 2>/dev/null || true)
    PR_COUNT=$(printf '%s' "$PR_JSON" | jq 'length' 2>/dev/null || echo 0)
    if [ -z "$PR_LIST" ] || [ "${PR_COUNT:-0}" -eq 0 ]; then
        emit_error "no PRs merged after $TS (or empty gh result, skill=${SKILL})"
    fi
    ECHO_LINE="Resolved since $TS (--skill=${SKILL}) to: [$(printf '%s' "$PR_JSON" | jq -r '[.[] | "#\(.)"] | join(", ")')]. Proceeding."
    emit_ok "false" "" "$PR_LIST" "$PR_COUNT" "$ECHO_LINE"
fi

# "#N" or "PR #N"
if printf '%s' "$VERBAL" | grep -qE '^(PR[[:space:]]+)?#[0-9]+$'; then
    N=$(printf '%s' "$VERBAL" | grep -oE '[0-9]+$')
    ECHO_LINE="Resolved $VERBAL (--skill=${SKILL}) to: [#${N}]. Proceeding."
    emit_ok "false" "" "$N" "1" "$ECHO_LINE"
fi

emit_error "unrecognized verbal description: $VERBAL"
