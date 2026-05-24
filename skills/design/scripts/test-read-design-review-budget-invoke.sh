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

missing_rp="${TMPDIR:-/tmp}/larch-rdb-missing.${RANDOM}"
[[ "$("$READ_BUDGET" "$missing_rp")" == full ]] || fail "unreadable run-params defaults to full"

printf '%s\n' '{"sketch_budget": 2}' >"$tmp"
[[ "$("$READ_BUDGET" "$tmp")" == full ]] || fail "sketch_budget 2 implies full (python3 heuristic)"

printf '%s\n' '{"sketch_budget": 4}' >"$tmp"
[[ "$("$READ_BUDGET" "$tmp")" == full ]] || fail "sketch_budget 4 implies full (python3 heuristic)"

fakebin=$(mktemp -d "${TMPDIR:-/tmp}/larch-fakebin.XXXXXX")
fakebin_pyonly=$(mktemp -d "${TMPDIR:-/tmp}/larch-fakebin-pyonly.XXXXXX")
trap 'rm -rf "$fakebin" "$fakebin_pyonly"; rm -f "$tmp"' EXIT
printf '%s\n' '#!/bin/sh' 'exit 1' >"$fakebin/python3"
printf '%s\n' '#!/bin/sh' 'exit 1' >"$fakebin/jq"
chmod +x "$fakebin/python3" "$fakebin/jq"
printf '%s\n' '#!/bin/sh' 'exit 1' >"$fakebin_pyonly/python3"
chmod +x "$fakebin_pyonly/python3"

printf '%s\n' '{"review_budget":"quick"}' >"$tmp"
_rdb_out=$(PATH="$fakebin:/usr/bin:/bin:/usr/sbin:/sbin" "$READ_BUDGET" "$tmp")
[[ "$_rdb_out" == quick ]] || fail "grep fallback quick"

printf '%s\n' '{"sketch_budget": 0}' >"$tmp"
_rdb_out=$(PATH="$fakebin:/usr/bin:/bin:/usr/sbin:/sbin" "$READ_BUDGET" "$tmp")
[[ "$_rdb_out" == quick ]] || fail "grep fallback sketch_budget 0"

printf '%s\n' '{"review_budget":"full"}' >"$tmp"
_rdb_out=$(PATH="$fakebin:/usr/bin:/bin:/usr/sbin:/sbin" "$READ_BUDGET" "$tmp")
[[ "$_rdb_out" == full ]] || fail "grep fallback full"

printf '%s\n' '{}' >"$tmp"
_rdb_out=$(PATH="$fakebin:/usr/bin:/bin:/usr/sbin:/sbin" "$READ_BUDGET" "$tmp")
[[ "$_rdb_out" == full ]] || fail "all fallbacks exhausted default to full"

if command -v jq >/dev/null 2>&1; then
    _jq_dir=$(dirname "$(command -v jq)")
    printf '%s\n' '{"review_budget":"quick"}' >"$tmp"
    _rdb_out=$(PATH="$_jq_dir:$fakebin_pyonly:/usr/bin:/bin:/usr/sbin:/sbin" "$READ_BUDGET" "$tmp")
    [[ "$_rdb_out" == quick ]] || fail "jq path when python3 fails"
else
    echo "SKIP: jq not on PATH; skipping jq-path branch" >&2
fi

dt=$(mktemp -d "${TMPDIR:-/tmp}/larch-invoke-test.XXXXXX")
full_dt=$(mktemp -d "${TMPDIR:-/tmp}/larch-invoke-full.XXXXXX")
dt_norp=$(mktemp -d "${TMPDIR:-/tmp}/larch-invoke-norp.XXXXXX")
defects_dt=$(mktemp -d "${TMPDIR:-/tmp}/larch-invoke-defects.XXXXXX")
trap 'rm -rf "$fakebin" "$fakebin_pyonly" "$dt" "$full_dt" "$dt_norp" "$defects_dt"; rm -f "$tmp"' EXIT
printf '%s\n' '{"review_budget":"quick"}' >"$dt/run-params.json"
if out=$(
    DESIGN_TMPDIR="$dt" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" PATH="$fakebin:/usr/bin:/bin" \
        "$INVOKE" "$REPO_ROOT/README.md"
); then
    [[ -z "$out" ]] || fail "quick tier must print nothing (got: $out)"
else
    fail "invoke quick should exit 0"
fi

if out=$(
    DESIGN_TMPDIR="$dt_norp" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$INVOKE" "$REPO_ROOT/README.md"
); then
    [[ -z "$out" ]] || fail "missing run-params must print nothing (got: $out)"
else
    fail "invoke without readable run-params should exit 0"
fi

printf '%s\n' '{"review_budget":"full"}' >"$full_dt/run-params.json"
cp "$REPO_ROOT/skills/design/scripts/fixtures/parse-plan-commands/basic-plan.md" "$full_dt/plan.md"
out=$(DESIGN_TMPDIR="$full_dt" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$INVOKE" "$full_dt/plan.md")
printf '%s\n' "$out" | grep -q '^VALIDATE_STATUS=ok$' || fail "full tier must emit VALIDATE_STATUS=ok"
printf '%s\n' "$out" | grep -q '^STEP_COMPLETED=VALIDATE_PLAN_COMMANDS$' || fail "full tier validate step must complete"

printf '%s\n' '{"review_budget":"full"}' >"$defects_dt/run-params.json"
cp "$REPO_ROOT/skills/design/scripts/fixtures/validate-plan-commands/demo-plan.md" "$defects_dt/plan.md"
out=$(DESIGN_TMPDIR="$defects_dt" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$INVOKE" "$defects_dt/plan.md")
printf '%s\n' "$out" | grep -q '^VALIDATE_STATUS=defects-found$' || fail "demo-plan must emit VALIDATE_STATUS=defects-found"
printf '%s\n' "$out" | grep -q '^VALIDATE_DEFECT_COUNT=1$' || fail "demo-plan must emit VALIDATE_DEFECT_COUNT=1"
printf '%s\n' "$out" | grep -q '^STEP_COMPLETED=VALIDATE_PLAN_COMMANDS$' || fail "defects path must complete validate step"

set +e
"$INVOKE" >/dev/null 2>&1
ec_noarg=$?
set -e
[[ "$ec_noarg" -ne 0 ]] || fail "invoke without PLAN_FILE must exit non-zero"

set +e
DESIGN_TMPDIR="" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$INVOKE" "$REPO_ROOT/README.md" >/dev/null 2>&1
ec_nodt=$?
set -e
[[ "$ec_nodt" -ne 0 ]] || fail "invoke without DESIGN_TMPDIR must exit non-zero"

set +e
DESIGN_TMPDIR="$dt_norp" CLAUDE_PLUGIN_ROOT="" "$INVOKE" "$REPO_ROOT/README.md" >/dev/null 2>&1
ec_noroot=$?
set -e
[[ "$ec_noroot" -ne 0 ]] || fail "invoke without CLAUDE_PLUGIN_ROOT must exit non-zero"

echo "PASS: test-read-design-review-budget-invoke.sh"
