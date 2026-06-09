#!/usr/bin/env bash
# Offline harness for scripts/lib-prune-decision.sh prune-status matrix.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
# shellcheck source=scripts/lib-prune-decision.sh
source "$ROOT/scripts/lib-prune-decision.sh"

fail() { printf '%s\n' "$1" >&2; exit 1; }

assert_eq() {
    local got="$1" want="$2" label="$3"
    [[ "$got" == "$want" ]] || fail "$label (got=$got want=$want)"
}

assert_eq "$(derive_prune_status false 0 false 0 false false)" "skipped" "out-of-window skipped"
assert_eq "$(derive_prune_status true 0 false 0 false true)" "active-kept-all" "active kept all"
assert_eq "$(derive_prune_status true 0 false 2 false true)" "active-dropped" "active dropped"
assert_eq "$(derive_prune_status true 0 false 0 true true)" "pruned-empty" "pruned empty"
assert_eq "$(derive_prune_status true 1 false 0 false true)" "failed" "filter rc fail-open"
assert_eq "$(derive_prune_status true 0 true 0 false true)" "failed" "advisory fail-open"

ledger_tmp=$(mktemp "${TMPDIR:-/tmp}/test-prune-ledger.XXXXXX")
trap 'rm -f "$ledger_tmp"' EXIT
ensure_reviewer_prune_ledger "$ledger_tmp"
[[ -s "$ledger_tmp" ]] || fail "ensure creates ledger"
assert_eq "$(head -n 1 "$ledger_tmp")" "$REVIEWER_PRUNE_LEDGER_HEADER" "ensure header"
: > "$ledger_tmp"
ensure_reviewer_prune_ledger "$ledger_tmp"
[[ -s "$ledger_tmp" ]] || fail "ensure repairs empty ledger"
printf 'bad\theader\n2\tcodex\tsecurity\tcodex-specialist-security-output.txt\t0\n' > "$ledger_tmp"
ensure_reviewer_prune_ledger "$ledger_tmp"
assert_eq "$(head -n 1 "$ledger_tmp")" "$REVIEWER_PRUNE_LEDGER_HEADER" "ensure repairs invalid header"
grep -Fq $'2\tcodex\tsecurity\tcodex-specialist-security-output.txt\t0' "$ledger_tmp" || fail "ensure preserves data rows"

printf '%s\n' 'test-lib-prune-decision: ok'
