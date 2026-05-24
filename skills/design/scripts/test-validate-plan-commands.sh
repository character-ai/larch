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

launch_want='DEFECT script=scripts/launch-claude-review.sh kind=unknown-flag flag=context-files'
"$SCRIPT_DIR/parse-plan-commands.sh" --plan-file "$SCRIPT_DIR/fixtures/validate-plan-commands/launch-context-plan.md" --output "$tsv" --repo-root "$REPO_ROOT"
"$SCRIPT_DIR/validate-plan-commands.sh" --tsv-file "$tsv" --log-file "$log" --source-kind plan >/dev/null
grep -Fq "$launch_want" "$log" || fail "missing launch-claude-review --context-files DEFECT line"

# ./script prefix must not skip Tier 2 repo-prefix detection
dotslash_plan=$(mktemp "${TMPDIR:-/tmp}/larch-dotslash-validate.XXXXXX.md")
trap 'rm -f "$log" "$tsv" "$dotslash_plan"' EXIT
cat >"$dotslash_plan" <<'EOF'
## Plan

```bash
./scripts/redact-secrets.sh
```

diff_lines: 1
EOF
"$SCRIPT_DIR/parse-plan-commands.sh" --plan-file "$dotslash_plan" --output "$tsv" --repo-root "$REPO_ROOT"
"$SCRIPT_DIR/validate-plan-commands.sh" --tsv-file "$tsv" --log-file "$log" --source-kind plan >/dev/null
tail -n1 "$log" | grep -q '^VALIDATE_STATUS=ok' || fail "dot-slash plan should validate ok"
rm -f "$dotslash_plan"

# Tier 3 dry-run success + failure via temp registry
reg=$(mktemp "${TMPDIR:-/tmp}/larch-dry-reg.XXXXXX.tsv")
tier3_ok_plan=$(mktemp "${TMPDIR:-/tmp}/larch-tier3-ok.XXXXXX.md")
tier3_fail_plan=$(mktemp "${TMPDIR:-/tmp}/larch-tier3-fail.XXXXXX.md")
trap 'rm -f "$log" "$tsv" "$reg" "$tier3_ok_plan" "$tier3_fail_plan"' EXIT
cat >"$reg" <<'EOF'
script_path	hook	doc_anchor
skills/design/scripts/fixtures/validate-plan-commands/demo-tier3-dry.sh	dry-run	
skills/design/scripts/fixtures/validate-plan-commands/demo-tier3-fail.sh	dry-run	
EOF
cat >"$tier3_ok_plan" <<'EOF'
## Plan

```bash
skills/design/scripts/fixtures/validate-plan-commands/demo-tier3-dry.sh --dry-flag x
```

diff_lines: 1
EOF
"$SCRIPT_DIR/parse-plan-commands.sh" --plan-file "$tier3_ok_plan" --output "$tsv" --repo-root "$REPO_ROOT"
"$SCRIPT_DIR/validate-plan-commands.sh" --tsv-file "$tsv" --log-file "$log" --source-kind plan --dry-runnable-registry "$reg" >/dev/null
tail -n1 "$log" | grep -q '^VALIDATE_STATUS=ok' || fail "tier3 dry ok plan"
grep -Fq 'kind=dry-run-failed' "$log" && fail "unexpected dry-run failure on ok tier3 fixture"

cat >"$tier3_fail_plan" <<'EOF'
## Plan

```bash
skills/design/scripts/fixtures/validate-plan-commands/demo-tier3-fail.sh --dry-flag x
```

diff_lines: 1
EOF
"$SCRIPT_DIR/parse-plan-commands.sh" --plan-file "$tier3_fail_plan" --output "$tsv" --repo-root "$REPO_ROOT"
"$SCRIPT_DIR/validate-plan-commands.sh" --tsv-file "$tsv" --log-file "$log" --source-kind plan --dry-runnable-registry "$reg" >/dev/null
grep -Fq 'kind=dry-run-failed' "$log" || fail "expected dry-run-failed for tier3 fail fixture"

# Unsafe token blocks Tier 3 before dry-run
unsafe_plan=$(mktemp "${TMPDIR:-/tmp}/larch-unsafe.XXXXXX.md")
trap 'rm -f "$log" "$tsv" "$reg" "$tier3_ok_plan" "$tier3_fail_plan" "$unsafe_plan"' EXIT
cat >"$unsafe_plan" <<'EOF'
## Plan

```bash
skills/design/scripts/fixtures/validate-plan-commands/demo-tier3-dry.sh --dry-flag 'x;y'
```

diff_lines: 1
EOF
"$SCRIPT_DIR/parse-plan-commands.sh" --plan-file "$unsafe_plan" --output "$tsv" --repo-root "$REPO_ROOT"
"$SCRIPT_DIR/validate-plan-commands.sh" --tsv-file "$tsv" --log-file "$log" --source-kind plan --dry-runnable-registry "$reg" >/dev/null
grep -Fq 'kind=unsafe-token' "$log" || fail "expected unsafe-token defect"
rm -f "$unsafe_plan"

# Composed basename disables Tier 3 (no dry-run probe even with registry)
comp_tier3=$(mktemp -d "${TMPDIR:-/tmp}/larch-composed-tier3.XXXXXX")
trap 'rm -rf "$comp_tier3"; rm -f "$log" "$tsv" "$reg" "$tier3_ok_plan" "$tier3_fail_plan"' EXIT
cp "$tier3_ok_plan" "$comp_tier3/composed-plan.md"
"$SCRIPT_DIR/parse-plan-commands.sh" --plan-file "$comp_tier3/composed-plan.md" --output "$tsv" --repo-root "$REPO_ROOT"
"$SCRIPT_DIR/validate-plan-commands.sh" --tsv-file "$tsv" --log-file "$log" --source-kind composed --dry-runnable-registry "$reg" >/dev/null
if grep -Fq 'kind=dry-run-failed' "$log"; then
    fail "composed source-kind should not run tier3 dry-run"
fi
rm -rf "$comp_tier3"

rm -f "$reg" "$tier3_ok_plan" "$tier3_fail_plan"

trap 'rm -f "$log" "$tsv"' EXIT

echo "PASS: test-validate-plan-commands.sh"
