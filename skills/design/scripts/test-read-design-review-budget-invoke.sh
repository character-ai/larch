#!/usr/bin/env bash
# Offline harness: read-design-review-budget.sh + invoke-plan-validator-if-not-quick.sh
set -euo pipefail

export LARCH_QUIET_DISABLE=1

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
REPO_ROOT=$(git -C "$SCRIPT_DIR/../../.." rev-parse --show-toplevel)
READ_BUDGET="$SCRIPT_DIR/read-design-review-budget.sh"
INVOKE="$SCRIPT_DIR/invoke-plan-validator-if-not-quick.sh"

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

tmp=$(mktemp "${TMPDIR:-/tmp}/larch-rdb.XXXXXX")
trap 'rm -f "$tmp"' EXIT

printf '%s\n' '{"review_budget":"full"}' >"$tmp"
[[ "$("$READ_BUDGET" "$tmp")" == full ]] || fail "explicit full"

printf '%s\n' '{"review_budget":"quick"}' >"$tmp"
[[ "$("$READ_BUDGET" "$tmp")" == quick ]] || fail "explicit quick"

printf '%s\n' '{"sketch_budget":0}' >"$tmp"
[[ "$("$READ_BUDGET" "$tmp")" == quick ]] || fail "sketch_budget 0 implies quick"

fakebin=$(mktemp -d "${TMPDIR:-/tmp}/larch-fakebin.XXXXXX")
trap 'rm -rf "$fakebin"; rm -f "$tmp"' EXIT
printf '%s\n' '#!/bin/sh' 'exit 1' >"$fakebin/python3"
printf '%s\n' '#!/bin/sh' 'exit 1' >"$fakebin/jq"
chmod +x "$fakebin/python3" "$fakebin/jq"

printf '%s\n' '{"review_budget":"quick"}' >"$tmp"
_rdb_out=$(PATH="$fakebin:/usr/bin:/bin:/usr/sbin:/sbin" "$READ_BUDGET" "$tmp")
[[ "$_rdb_out" == quick ]] || fail "grep fallback quick"

printf '%s\n' '{"sketch_budget": 0}' >"$tmp"
_rdb_out=$(PATH="$fakebin:/usr/bin:/bin:/usr/sbin:/sbin" "$READ_BUDGET" "$tmp")
[[ "$_rdb_out" == quick ]] || fail "grep fallback sketch_budget 0"

dt=$(mktemp -d "${TMPDIR:-/tmp}/larch-invoke-test.XXXXXX")
full_dt=$(mktemp -d "${TMPDIR:-/tmp}/larch-invoke-full.XXXXXX")
trap 'rm -rf "$fakebin" "$dt" "$full_dt"; rm -f "$tmp"' EXIT
printf '%s\n' '{"review_budget":"quick"}' >"$dt/run-params.json"
if out=$(
    DESIGN_TMPDIR="$dt" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" PATH="$fakebin:/usr/bin:/bin" \
        "$INVOKE" "$REPO_ROOT/README.md"
); then
    [[ -z "$out" ]] || fail "quick tier must print nothing (got: $out)"
else
    fail "invoke quick should exit 0"
fi

printf '%s\n' '{"review_budget":"full"}' >"$full_dt/run-params.json"
cp "$REPO_ROOT/skills/design/scripts/fixtures/parse-plan-commands/basic-plan.md" "$full_dt/plan.md"
out=$(DESIGN_TMPDIR="$full_dt" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$INVOKE" "$full_dt/plan.md")
printf '%s\n' "$out" | grep -q '^VALIDATE_STATUS=ok$' || fail "full tier must emit VALIDATE_STATUS=ok"
printf '%s\n' "$out" | grep -q '^STEP_COMPLETED=VALIDATE_PLAN_COMMANDS$' || fail "full tier validate step must complete"

echo "PASS: test-read-design-review-budget-invoke.sh"
