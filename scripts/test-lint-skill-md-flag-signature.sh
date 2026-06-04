#!/usr/bin/env bash
# Offline regression harness for lint-skill-md-flag-signature.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
LINT="$SCRIPT_DIR/lint-skill-md-flag-signature.sh"

fail() {
    printf '%s\n' "FAIL: $1" >&2
    exit 1
}

TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/larch-skill-flag-lint-test.XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

make_skill() {
    local root="$1"
    local skill="$2"
    mkdir -p "$root/skills/$skill" "$root/scripts"
}

write_script() {
    local path="$1"
    shift
    mkdir -p "$(dirname "$path")"
    {
        printf '%s\n' '#!/usr/bin/env bash'
        printf '%s\n' 'set -euo pipefail'
        printf '%s\n' 'while [ "$#" -gt 0 ]; do'
        # shellcheck disable=SC2016 # literal generated fixture content.
        printf '%s\n' '  case "$1" in'
        local flag
        for flag in "$@"; do
            printf '    --%s)\n' "$flag"
            printf '%s\n' '      shift 2'
            printf '%s\n' '      ;;'
        done
        printf '%s\n' '    *) exit 2 ;;'
        printf '%s\n' '  esac'
        printf '%s\n' 'done'
    } > "$path"
}

assert_lint_ok() {
    local label="$1"
    local root="$2"
    local out="$TMPROOT/${label}.out"
    local err="$TMPROOT/${label}.err"
    bash "$LINT" --root "$root" >"$out" 2>"$err" || fail "$label: expected lint success: $(cat "$err")"
    [ ! -s "$err" ] || fail "$label: expected empty stderr"
}

assert_lint_fails_for() {
    local label="$1"
    local root="$2"
    local expected="$3"
    local out="$TMPROOT/${label}.out"
    local err="$TMPROOT/${label}.err"
    local rc

    set +e
    bash "$LINT" --root "$root" >"$out" 2>"$err"
    rc=$?
    set -e

    [ "$rc" -ne 0 ] || fail "$label: expected lint failure"
    grep -Fq -- "$expected" "$err" || fail "$label: stderr missing '$expected': $(cat "$err")"
}

pass_known="$TMPROOT/pass-known"
make_skill "$pass_known" design
write_script "$pass_known/scripts/example.sh" known-flag
cat > "$pass_known/skills/design/SKILL.md" <<'EOF'
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/example.sh --known-flag value
```
EOF
assert_lint_ok pass-known "$pass_known"

fail_missing="$TMPROOT/fail-missing"
make_skill "$fail_missing" design
write_script "$fail_missing/scripts/example.sh" known-flag
cat > "$fail_missing/skills/design/SKILL.md" <<'EOF'
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/example.sh --unknown-flag value
```
EOF
assert_lint_fails_for fail-missing "$fail_missing" 'skills/design/SKILL.md:2: invocation uses --unknown-flag but scripts/example.sh does not declare it'

multiple="$TMPROOT/multiple"
make_skill "$multiple" design
make_skill "$multiple" review
write_script "$multiple/scripts/example.sh" known-flag
cat > "$multiple/skills/design/SKILL.md" <<'EOF'
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/example.sh --missing-one value --missing-two value
```
EOF
cat > "$multiple/skills/review/SKILL.md" <<'EOF'
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/example.sh --missing-three value
```
EOF
assert_lint_fails_for multiple-one "$multiple" 'skills/design/SKILL.md:2: invocation uses --missing-one but scripts/example.sh does not declare it'
assert_lint_fails_for multiple-two "$multiple" 'skills/design/SKILL.md:2: invocation uses --missing-two but scripts/example.sh does not declare it'
assert_lint_fails_for multiple-three "$multiple" 'skills/review/SKILL.md:2: invocation uses --missing-three but scripts/example.sh does not declare it'

waiver="$TMPROOT/waiver"
make_skill "$waiver" design
write_script "$waiver/scripts/example.sh" known-flag
cat > "$waiver/skills/design/SKILL.md" <<'EOF'
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/example.sh --unknown-flag value # lint-skill-md-flag-signature: ok dynamic parser fixture
```
EOF
assert_lint_ok waiver "$waiver"

multiline_bad="$TMPROOT/multiline-bad"
make_skill "$multiline_bad" design
write_script "$multiline_bad/scripts/write-run-params.sh" classification output source sketch-budget workflow-path partition-requested brainstorm-requested manual-gate-b
cat > "$multiline_bad/skills/design/SKILL.md" <<'EOF'
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/write-run-params.sh \
  --classification "$design_classification" \
  --reason "$design_classification_reason" \
  --source "$design_classification_source" \
  --sketch-budget "$sketch_budget" \
  --workflow-path "$workflow_path" \
  --partition-requested "$partition_requested" \
  --brainstorm-requested "$brainstorm_requested" \
  --manual-gate-b "$manual_requested" \
  --output "$DESIGN_TMPDIR/run-params.json"
```
EOF
assert_lint_fails_for multiline-bad "$multiline_bad" 'skills/design/SKILL.md:2: invocation uses --reason but scripts/write-run-params.sh does not declare it'

multiline_good="$TMPROOT/multiline-good"
make_skill "$multiline_good" design
write_script "$multiline_good/scripts/write-run-params.sh" classification reason source sketch-budget workflow-path partition-requested brainstorm-requested manual-gate-b output
cp "$multiline_bad/skills/design/SKILL.md" "$multiline_good/skills/design/SKILL.md"
assert_lint_ok multiline-good "$multiline_good"

regression_bad="$TMPROOT/regression-bad"
make_skill "$regression_bad" design
write_script "$regression_bad/scripts/write-run-params.sh" classification output partition-requested brainstorm-requested manual-gate-b
cp "$multiline_bad/skills/design/SKILL.md" "$regression_bad/skills/design/SKILL.md"
assert_lint_fails_for regression-bad "$regression_bad" 'skills/design/SKILL.md:2: invocation uses --reason but scripts/write-run-params.sh does not declare it'

regression_fixed="$TMPROOT/regression-fixed"
make_skill "$regression_fixed" design
write_script "$regression_fixed/scripts/write-run-params.sh" classification reason source sketch-budget workflow-path partition-requested brainstorm-requested manual-gate-b output
cp "$multiline_bad/skills/design/SKILL.md" "$regression_fixed/skills/design/SKILL.md"
assert_lint_ok regression-fixed "$regression_fixed"

printf '%s\n' "test-lint-skill-md-flag-signature: ok"
