#!/usr/bin/env bash
# Offline harness: parse-plan-commands.sh golden fixtures.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
SUBJECT="$SCRIPT_DIR/parse-plan-commands.sh"
FIX="$SCRIPT_DIR/fixtures/parse-plan-commands"
REPO_ROOT=$(git -C "$SCRIPT_DIR/../../.." rev-parse --show-toplevel)

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

run_case() {
    local name="$1" plan="$2" want="$3"
    local out
    out=$(mktemp)
    "$SUBJECT" --plan-file "$plan" --output "$out" --repo-root "$REPO_ROOT"
    if ! cmp -s "$out" "$want"; then
        echo "---- got ----" >&2
        cat "$out" >&2
        echo "---- want ----" >&2
        cat "$want" >&2
        fail "case $name: TSV mismatch"
    fi
    rm -f "$out"
}

[[ -d "$FIX" ]] || fail "fixtures dir missing: $FIX"

run_case basic "$FIX/basic-plan.md" "$FIX/basic.tsv"
run_case prefixes "$FIX/prefix-plan.md" "$FIX/prefix.tsv"
run_case newskip "$FIX/newskip-plan.md" "$FIX/newskip.tsv"
run_case heredoc "$FIX/heredoc-plan.md" "$FIX/heredoc.tsv"

echo "PASS: test-parse-plan-commands.sh"
