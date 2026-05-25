#!/usr/bin/env bash
# Regression harness for scripts/lib-title-eligibility.sh (no gh calls).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
LIB="$ROOT/scripts/lib-title-eligibility.sh"

fail() {
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

assert_match() {
    local fn=$1 title=$2
    if "$fn" "$title"; then
        :
    else
        fail "$fn should match: $title"
    fi
}

assert_no_match() {
    local fn=$1 title=$2
    if "$fn" "$title"; then
        fail "$fn should not match: $title"
    fi
}

# --- Source from repo scripts/ (default harness CWD) ---
# shellcheck source=scripts/lib-title-eligibility.sh
# shellcheck disable=SC1091
source "$LIB"

# --- Source from skills/issue/scripts/ layout (list-issues.sh PWD) ---
(
    cd "$ROOT/skills/issue/scripts" || exit 1
    unset CLAUDE_PLUGIN_ROOT || true
    # shellcheck source=scripts/lib-title-eligibility.sh
    # shellcheck disable=SC1091
    source "$ROOT/scripts/lib-title-eligibility.sh"
    title_has_archival_report_prefix '[Report] foo' || exit 1
) || fail 'source from skills/issue/scripts/ failed'

# Lifecycle-reject hits
for t in \
    '[IMPLEMENTING] foo' '[DONE] bar' '[DESIGNING] baz' '[DESIGNED] qux' \
    '[implementing] x' '[Done]Y'
do
    assert_match title_has_lifecycle_reject_prefix "$t"
done

# Lifecycle-reject misses
for t in \
    '[STALLED] z' '[PLANNED] z' '[IN PROGRESS] z' \
    'foo [DESIGNING] bar' 'IMPLEMENTING foo' ''
do
    assert_no_match title_has_lifecycle_reject_prefix "$t"
done

token=$(title_has_lifecycle_reject_prefix '[IMPLEMENTING] foo' 2>/dev/null || true)
[[ "$token" == '[IMPLEMENTING]' ]] || fail "lifecycle token stdout: got [$token]"

# Report-prefix hits (Report immediately followed by "] ")
for t in '[Analysis Report] foo' '[Research Report] bar' '[Report] foo'
do
    assert_match title_has_archival_report_prefix "$t"
done

# Report in bracket block but not immediately before "] " — no match (same as list-issues jq)
assert_no_match title_has_archival_report_prefix '[Run Logs Audit Report 2026-05-25T12:00:00Z] baz'

# Report-prefix misses
for t in '[Reporting] foo' 'Report foo' '[X Report]foo'
do
    assert_no_match title_has_archival_report_prefix "$t"
done

# Brainstorm hits
for t in \
    'Brainstorm: foo' 'Brainstorm foo' 'BRAINSTORM bar' 'brainstorm' \
    'Brainstorm-mode' 'Brainstorm:'
do
    assert_match title_starts_with_brainstorm "$t"
done

# Brainstorm misses
for t in 'Brainstorming a feature' 'Pre-brainstorm session' 'foo Brainstorm bar'
do
    assert_no_match title_starts_with_brainstorm "$t"
done

# jq/bash equivalence (12 fixtures): skip-set must match
title_skipped_by_jq() {
    local title=$1 jq_filter
    # shellcheck disable=SC2031
    jq_filter=$LARCH_TITLE_ARCHIVAL_PREFIX_JQ_FILTER
    if printf '%s\n' "{\"title\":$(jq -Rn --arg t "$title" '$t')}" \
        | jq -e "$jq_filter" >/dev/null 2>&1; then
        return 1
    fi
    return 0
}

title_skipped_by_bash_mirror() {
    local title=$1 lower
    [ -n "$title" ] || return 1
    title=$(larch_title_trim_leading_ws "$title")
    lower=$(printf '%s' "$title" | tr '[:upper:]' '[:lower:]')
    case "$lower" in
        research\ *) return 0 ;;
        "[research] "*) return 0 ;;
        investigate\ *) return 0 ;;
        "[investigate] "*) return 0 ;;
    esac
    if title_has_archival_report_prefix "$title"; then
        return 0
    fi
    return 1
}

EQUIV_FIXTURES=(
    '[Analysis Report] foo'
    '[Research Report] bar'
    'research backlog item'
    '[research] old title'
    'investigate flaky test'
    '[investigate] scope'
    '[Reporting] foo'
    'Normal feature title'
    '  [Report] spaced'
    '[IMPLEMENTING] mixed'
    'Brainstorm: foo'
    '[X Report]foo'
)

for t in "${EQUIV_FIXTURES[@]}"; do
    jq_skip=false bash_skip=false
    if title_skipped_by_jq "$t"; then jq_skip=true; fi
    if title_skipped_by_bash_mirror "$t"; then bash_skip=true; fi
    if [[ "$jq_skip" != "$bash_skip" ]]; then
        fail "jq/bash mismatch for [$t]: jq_skip=$jq_skip bash_skip=$bash_skip"
    fi
done

printf 'PASS: test-lib-title-eligibility.sh\n'
