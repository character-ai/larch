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

want='DEFECT script=skills/design/scripts/fixtures/validate-plan-commands/demo-stdout-help.sh kind=unknown-flag flag=unknown-flag'

log=$(mktemp)
tsv=$(mktemp)
trap 'rm -f "$log" "$tsv"' EXIT

"$SCRIPT_DIR/parse-plan-commands.sh" --plan-file "$DEMO" --output "$tsv" --repo-root "$REPO_ROOT"
"$SCRIPT_DIR/validate-plan-commands.sh" --tsv-file "$tsv" --log-file "$log" --source-kind plan >/dev/null

grep -Fq "$want" "$log" || fail "missing exact DEFECT line in log"

tail -n1 "$log" | grep -q '^VALIDATE_STATUS=defects-found' || fail "summary line"

out=$(LARCH_QUIET_DISABLE=1 DESIGN_TMPDIR='' "$SCRIPT_DIR/validate-plan.sh" --plan-file "$DEMO" --repo-root "$REPO_ROOT")
printf '%s\n' "$out" | grep -q '^VALIDATE_STATUS=defects-found$' || fail "validate-plan.sh wrapper status"
printf '%s\n' "$out" | grep -q '^VALIDATE_DEFECT_COUNT=1$' || fail "validate-plan defect count"

comp_dir=$(mktemp -d "${TMPDIR:-/tmp}/larch-composed-plan-test.XXXXXX")
trap 'rm -rf "$comp_dir"; rm -f "$log" "$tsv"' EXIT
cp "$DEMO" "$comp_dir/composed-plan.md"
out2=$(LARCH_QUIET_DISABLE=1 DESIGN_TMPDIR='' "$SCRIPT_DIR/validate-plan.sh" --plan-file "$comp_dir/composed-plan.md" --repo-root "$REPO_ROOT")
printf '%s\n' "$out2" | grep -q '^VALIDATE_STATUS=defects-found$' || fail "composed-plan.md basename still tier2"
rm -rf "$comp_dir"
trap 'rm -f "$log" "$tsv"' EXIT

# Missing repo script → missing-script defect
missing_plan=$(mktemp "${TMPDIR:-/tmp}/larch-missing-plan.XXXXXX.md")
trap 'rm -f "$log" "$tsv" "$missing_plan"' EXIT
cat >"$missing_plan" <<'EOF'
## Plan

```bash
scripts/does-not-exist-zzzz-validate-fixture.sh
```

diff_lines: 1
EOF
"$SCRIPT_DIR/parse-plan-commands.sh" --plan-file "$missing_plan" --output "$tsv" --repo-root "$REPO_ROOT"
"$SCRIPT_DIR/validate-plan-commands.sh" --tsv-file "$tsv" --log-file "$log" --source-kind plan >/dev/null
grep -Fq 'DEFECT script=scripts/does-not-exist-zzzz-validate-fixture.sh kind=missing-script' "$log" || fail "missing-script defect"
rm -f "$missing_plan"

# Parse rejects .. in script token (parse_note); validator has no invocations to check
dots_plan=$(mktemp "${TMPDIR:-/tmp}/larch-dots-plan.XXXXXX.md")
trap 'rm -f "$log" "$tsv" "$dots_plan"' EXIT
cat >"$dots_plan" <<'EOF'
## Plan

```bash
scripts/../scripts/redact-secrets.sh
```

diff_lines: 1
EOF
"$SCRIPT_DIR/parse-plan-commands.sh" --plan-file "$dots_plan" --output "$tsv" --repo-root "$REPO_ROOT"
grep -Fq $'parse_note\t' "$tsv" || fail "expected parse_note for non-canonical path"
"$SCRIPT_DIR/validate-plan-commands.sh" --tsv-file "$tsv" --log-file "$log" --source-kind plan >/dev/null
tail -n1 "$log" | grep -q '^VALIDATE_STATUS=ok' || fail "dots plan should validate ok after parse skip"
rm -f "$dots_plan"

# Allow-listed flag from plan UPDATED section → no unknown-flag for that flag
allow_plan=$(mktemp "${TMPDIR:-/tmp}/larch-allow-plan.XXXXXX.md")
trap 'rm -f "$log" "$tsv" "$allow_plan"' EXIT
cat >"$allow_plan" <<'EOF'
## Plan

### Files to update

- **UPDATED**: skills/design/scripts/fixtures/validate-plan-commands/demo-stdout-help.sh
  - Adds flag: known-flag

```bash
skills/design/scripts/fixtures/validate-plan-commands/demo-stdout-help.sh --known-flag x
```

diff_lines: 1
EOF
"$SCRIPT_DIR/parse-plan-commands.sh" --plan-file "$allow_plan" --output "$tsv" --repo-root "$REPO_ROOT"
"$SCRIPT_DIR/validate-plan-commands.sh" --tsv-file "$tsv" --log-file "$log" --source-kind plan >/dev/null
if grep -Fq 'kind=unknown-flag flag=known-flag' "$log"; then
    fail "allow-listed flag should not defect"
fi
tail -n1 "$log" | grep -q '^VALIDATE_STATUS=ok' || fail "allow-flag plan should be ok"
rm -f "$allow_plan"

trap 'rm -f "$log" "$tsv"' EXIT

echo "PASS: test-validate-plan-commands.sh"
