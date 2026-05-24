#!/usr/bin/env bash
# Offline harness: validate-plan-commands + validate-plan integration.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
REPO_ROOT=$(git -C "$SCRIPT_DIR/../../.." rev-parse --show-toplevel)
DEMO="$SCRIPT_DIR/fixtures/validate-plan-commands/demo-plan.md"

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

want='DEFECT script=scripts/launch-claude-review.sh kind=unknown-flag flag=context-files'

log=$(mktemp)
tsv=$(mktemp)
trap 'rm -f "$log" "$tsv"' EXIT

"$SCRIPT_DIR/parse-plan-commands.sh" --plan-file "$DEMO" --output "$tsv" --repo-root "$REPO_ROOT"
"$SCRIPT_DIR/validate-plan-commands.sh" --tsv-file "$tsv" --log-file "$log" --source-kind plan

grep -Fq "$want" "$log" || fail "missing exact DEFECT line in log"

tail -n1 "$log" | grep -q '^VALIDATE_STATUS=defects-found' || fail "summary line"

out=$(LARCH_QUIET_DISABLE=1 DESIGN_TMPDIR='' "$SCRIPT_DIR/validate-plan.sh" --plan-file "$DEMO" --repo-root "$REPO_ROOT")
printf '%s\n' "$out" | grep -q '^VALIDATE_STATUS=defects-found$' || fail "validate-plan.sh wrapper status"
printf '%s\n' "$out" | grep -q '^VALIDATE_DEFECT_COUNT=1$' || fail "validate-plan defect count"

comp=$(mktemp "${TMPDIR:-/tmp}/composed-plan.md.XXXXXX")
trap 'rm -f "$log" "$tsv" "$comp"' EXIT
cp "$DEMO" "$comp"
out2=$(LARCH_QUIET_DISABLE=1 DESIGN_TMPDIR='' "$SCRIPT_DIR/validate-plan.sh" --plan-file "$comp" --repo-root "$REPO_ROOT")
printf '%s\n' "$out2" | grep -q '^VALIDATE_STATUS=defects-found$' || fail "composed basename still tier2"
rm -f "$comp"
trap 'rm -f "$log" "$tsv"' EXIT

echo "PASS: test-validate-plan-commands.sh"
