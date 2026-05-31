#!/usr/bin/env bash
# test-no-grouped-reuse-guard.sh — post-condition guard: grouped reuse fully removed.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"

fail() {
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

hits=$(grep -rn 'fallback_group' "$REPO_ROOT/skills" "$REPO_ROOT/scripts" 2>/dev/null \
    | grep -vE '\.md:' | grep -vE '/test-[^/]*\.sh:' || true)
[[ -z "$hits" ]] || fail "fallback_group still present:\n$hits"

for sym in reuse_slot_result find_group_ok_for_tool append_group_ledger_ok GROUP_LEDGER REUSED_INDICES idx_was_reused has_fallback_groups waterfall-group-results DEDUPE_REUSED slot_fallback_groups REUSED_INDICES_FILE phase2_grouped; do
    grep -q "$sym" "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
        && fail "dispatch-with-waterfall.sh still references $sym"
done

wf_hits=$(grep -rn 'waterfall-group-results\|\.dedup' "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" 2>/dev/null || true)
[[ -z "$wf_hits" ]] || fail "dispatch-with-waterfall.sh still references grouped-reuse artifacts:\n$wf_hits"

printf 'PASS: test-no-grouped-reuse-guard\n'
