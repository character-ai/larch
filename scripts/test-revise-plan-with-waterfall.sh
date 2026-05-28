#!/usr/bin/env bash
# Regression harness for skills/design/scripts/revise-plan-with-waterfall.sh.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
SUBJECT="$REPO_ROOT/skills/design/scripts/revise-plan-with-waterfall.sh"

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

assert_line() {
    local expected="$1" output="$2"
    grep -Fxq "$expected" <<<"$output" || {
        echo "FAIL: missing $expected" >&2
        printf '%s\n' "$output" >&2
        exit 1
    }
}

assert_contains() {
    local needle="$1" path="$2"
    grep -Fq "$needle" "$path" || fail "missing '$needle' in $path"
}

assert_not_exists() {
    [[ ! -e "$1" ]] || fail "unexpected file exists: $1"
}

TMPROOT=$(mktemp -d "${TMPDIR:-/tmp}/larch-revise-plan-waterfall.XXXXXX")
trap 'rm -rf "$TMPROOT"' EXIT

STUB_DIR="$TMPROOT/stubs"
mkdir -p "$STUB_DIR"

cat >"$STUB_DIR/generic-launcher" <<'STUB'
#!/usr/bin/env bash
output=""
tool=""
prompt_count=0
description_count=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tool) tool="${2:-}"; shift 2 ;;
        --output) output="${2:-}"; shift 2 ;;
        --prompt-file) prompt_count=$((prompt_count + 1)); [[ -n "${2:-}" && -r "$2" ]] || exit 21; shift 2 ;;
        --description-text) description_count=$((description_count + 1)); shift 2 ;;
        --mode|--timeout|--plan-file|--feature-file|--scope-files) [[ -n "${2:-}" ]] || exit 22; shift 2 ;;
        *) shift ;;
    esac
done
if [[ -z "$tool" ]]; then
    case "$(basename "$0")" in
        *claude*) tool=claude ;;
        *) exit 23 ;;
    esac
fi
[[ "$prompt_count" -eq 1 ]] || exit 24
[[ "$description_count" -eq 0 ]] || exit 25
[[ -n "$output" ]] || exit 26
mkdir -p "$(dirname "$output")"
case "$tool" in
    codex) content_var=CODEX_STUB_CONTENT_FILE; rc_var=CODEX_STUB_RC ;;
    cursor) content_var=CURSOR_STUB_CONTENT_FILE; rc_var=CURSOR_STUB_RC ;;
    claude) content_var=CLAUDE_STUB_CONTENT_FILE; rc_var=CLAUDE_STUB_RC ;;
    *) exit 27 ;;
esac
content_file="${!content_var:-}"
rc="${!rc_var:-0}"
if [[ -n "$content_file" ]]; then
    cp "$content_file" "$output"
else
    : >"$output"
fi
exit "$rc"
STUB
chmod +x "$STUB_DIR/generic-launcher"
cp "$STUB_DIR/generic-launcher" "$STUB_DIR/codex-launcher"
cp "$STUB_DIR/generic-launcher" "$STUB_DIR/cursor-launcher"
cp "$STUB_DIR/generic-launcher" "$STUB_DIR/claude-launcher"
chmod +x "$STUB_DIR/codex-launcher" "$STUB_DIR/cursor-launcher" "$STUB_DIR/claude-launcher"

cat >"$STUB_DIR/design-driver" <<STUB
#!/usr/bin/env bash
design_tmpdir=""
while [[ \$# -gt 0 ]]; do
    case "\$1" in
        --design-tmpdir) design_tmpdir="\${2:-}"; shift 2 ;;
        *) shift ;;
    esac
done
[[ -n "\$design_tmpdir" ]] || exit 2
"$REPO_ROOT/skills/design/scripts/emit-plan.sh" --design-tmpdir "\$design_tmpdir"
STUB
chmod +x "$STUB_DIR/design-driver"

export LARCH_TEST_LAUNCH_CODEX_REVIEW="$STUB_DIR/codex-launcher"
export LARCH_TEST_LAUNCH_CURSOR_REVIEW="$STUB_DIR/cursor-launcher"
export LARCH_TEST_LAUNCH_CLAUDE_REVIEW="$STUB_DIR/claude-launcher"
export LARCH_TEST_DESIGN_DRIVER="$STUB_DIR/design-driver"

make_case() {
    local name case_dir
    name="$1"
    case_dir="$TMPROOT/$name"
    mkdir -p "$case_dir"
    cat >"$case_dir/plan.txt" <<'PLAN'
## Plan

### NEW: sample.txt

Write original text.

diff_lines: 12
PLAN
    printf 'Accepted finding.\n' >"$case_dir/findings.md"
    printf 'Feature context.\n' >"$case_dir/feature.txt"
    printf '%s\n' "$case_dir"
}

write_valid_diff() {
    local path="$1" text="$2" diff_lines="$3"
    cat >"$path" <<DIFF
--- a/plan.txt
+++ b/plan.txt
@@ -3,5 +3,5 @@
 ### NEW: sample.txt
 
-Write original text.
+$text
 
-diff_lines: 12
+diff_lines: $diff_lines
DIFF
}

write_wrong_path_diff() {
    local path="$1"
    cat >"$path" <<'DIFF'
--- a/wrong-file.txt
+++ b/wrong-file.txt
@@ -1 +1 @@
-old
+new
DIFF
}

write_bad_context_diff() {
    local path="$1"
    cat >"$path" <<'DIFF'
--- a/plan.txt
+++ b/plan.txt
@@ -3,5 +3,5 @@
 ### NEW: sample.txt
 
-This context does not exist.
+Write revised by codex.
 
-diff_lines: 12
+diff_lines: 14
DIFF
}

write_missing_trailer_diff() {
    local path="$1"
    cat >"$path" <<'DIFF'
--- a/plan.txt
+++ b/plan.txt
@@ -3,5 +3,4 @@
 ### NEW: sample.txt
 
-Write original text.
+Write revised without trailer.
 
-diff_lines: 12
DIFF
}

write_heading_loss_diff() {
    local path="$1"
    cat >"$path" <<'DIFF'
--- a/plan.txt
+++ b/plan.txt
@@ -1,6 +1,6 @@
 ## Plan
 
-### NEW: sample.txt
+Plan section without file heading.
 
-Write original text.
+Write revised text.
 
 diff_lines: 12
DIFF
}

write_replacement() {
    local path="$1" text="$2" diff_lines="$3"
    cat >"$path" <<PLAN
## Plan

### NEW: sample.txt

$text

diff_lines: $diff_lines
PLAN
}

write_heading_loss_replacement() {
    local path="$1" text="$2" diff_lines="$3"
    cat >"$path" <<PLAN
## Plan

$text

diff_lines: $diff_lines
PLAN
}

write_fenced_replacement() {
    local path="$1" text="$2" diff_lines="$3"
    {
        printf '%s\n\n' 'Preamble that should be ignored.'
        printf '%s\n' '```markdown'
        printf '%s\n\n' '## Plan'
        printf '%s\n\n' '### NEW: sample.txt'
        printf '%s\n\n' "$text"
        printf 'diff_lines: %s\n' "$diff_lines"
        printf '%s\n\n' '```'
        printf '%s\n' 'Trailing prose that should be ignored.'
    } >"$path"
}

write_fenced_diff_with_trailing_prose() {
    local path="$1" text="$2" diff_lines="$3"
    local tmp
    tmp=$(mktemp "$TMPROOT/fenced-diff.XXXXXX")
    write_valid_diff "$tmp" "$text" "$diff_lines"
    {
        printf '%s\n\n' 'Intro prose.'
        printf '%s\n' '```diff'
        cat "$tmp"
        printf '%s\n\n' '```'
        printf '%s\n' 'Trailing prose that should be ignored.'
    } >"$path"
    rm -f "$tmp"
}

write_multi_fence_diff() {
    local path="$1" text="$2" diff_lines="$3"
    local tmp_main tmp_extra
    tmp_main=$(mktemp "$TMPROOT/multi-main.XXXXXX")
    tmp_extra=$(mktemp "$TMPROOT/multi-extra.XXXXXX")
    write_valid_diff "$tmp_main" "$text" "$diff_lines"
    write_valid_diff "$tmp_extra" "Write revised from second fenced diff." 999
    {
        printf '%s\n\n' 'Prose.'
        printf '%s\n' '```diff'
        cat "$tmp_main"
        printf '%s\n\n' '```'
        printf '%s\n' '```diff'
        cat "$tmp_extra"
        printf '%s\n' '```'
    } >"$path"
    rm -f "$tmp_main" "$tmp_extra"
}

write_illustrative_then_real_diff() {
    local path="$1" text="$2" diff_lines="$3"
    local tmp_example tmp_real
    tmp_example=$(mktemp "$TMPROOT/example-diff.XXXXXX")
    tmp_real=$(mktemp "$TMPROOT/real-diff.XXXXXX")
    write_valid_diff "$tmp_example" "Write revised from illustrative example." 998
    write_valid_diff "$tmp_real" "$text" "$diff_lines"
    cat >"$path" <<DIFF
Example patch, do not apply:
$(cat "$tmp_example")

Actual patch:
$(cat "$tmp_real")
DIFF
    rm -f "$tmp_example" "$tmp_real"
}

clear_stubs() {
    unset CODEX_STUB_CONTENT_FILE CURSOR_STUB_CONTENT_FILE CLAUDE_STUB_CONTENT_FILE
    unset CODEX_STUB_RC CURSOR_STUB_RC CLAUDE_STUB_RC
}

run_subject() {
    local case_dir="$1" codex_present="$2" cursor_present="$3" patch_format="${4:-unified-diff}"
    "$SUBJECT" \
        --design-tmpdir "$case_dir" \
        --plan-file "$case_dir/plan.txt" \
        --findings-file "$case_dir/findings.md" \
        --feature-file "$case_dir/feature.txt" \
        --round-num 1 \
        --codex-present "$codex_present" \
        --cursor-present "$cursor_present" \
        --timeout 5 \
        --patch-format "$patch_format"
}

# 1. Codex wins.
clear_stubs
case_dir=$(make_case case1)
codex_patch="$TMPROOT/case1-codex.diff"
write_valid_diff "$codex_patch" "Write revised by codex." 14
export CODEX_STUB_CONTENT_FILE="$codex_patch"
out=$(run_subject "$case_dir" true true)
assert_line "REVISE_TIER_1_STATUS=ok" "$out"
assert_line "REVISE_TIER_2_STATUS=not-attempted" "$out"
assert_line "REVISE_TIER_3_STATUS=not-attempted" "$out"
assert_line "REVISE_STATUS=ok" "$out"
assert_line "REVISE_TIER=codex" "$out"
assert_contains "Write revised by codex." "$case_dir/plan.txt"
assert_contains "### NEW: sample.txt" "$case_dir/plan.txt"
assert_not_exists "$case_dir/plan.txt.before-revise"
echo "PASS: case 1"

# 2. Codex no-patch, Cursor wins.
clear_stubs
case_dir=$(make_case case2)
cursor_patch="$TMPROOT/case2-cursor.diff"
write_valid_diff "$cursor_patch" "Write revised by cursor." 15
export CURSOR_STUB_CONTENT_FILE="$cursor_patch"
out=$(run_subject "$case_dir" true true)
assert_line "REVISE_TIER_1_STATUS=no-patch" "$out"
assert_line "REVISE_TIER_2_STATUS=ok" "$out"
assert_line "REVISE_STATUS=ok" "$out"
assert_line "REVISE_TIER=cursor" "$out"
assert_contains "Write revised by cursor." "$case_dir/plan.txt"
echo "PASS: case 2"

# 3. Wrong-path unified diffs are ignored; file-replacement Claude fallback wins.
clear_stubs
case_dir=$(make_case case3a)
wrong_patch="$TMPROOT/case3-wrong.diff"
write_wrong_path_diff "$wrong_patch"
export CODEX_STUB_CONTENT_FILE="$wrong_patch"
export CURSOR_STUB_CONTENT_FILE="$wrong_patch"
out=$(run_subject "$case_dir" true true)
assert_line "REVISE_TIER_1_STATUS=no-patch" "$out"
assert_line "REVISE_TIER_2_STATUS=no-patch" "$out"
assert_line "REVISE_STATUS=failed-no-patch" "$out"
assert_contains "Write original text." "$case_dir/plan.txt"

clear_stubs
case_dir=$(make_case case3b)
bad_replacement="$TMPROOT/case3-bad.txt"
claude_replacement="$TMPROOT/case3-claude.txt"
printf 'not a complete replacement\n' >"$bad_replacement"
write_replacement "$claude_replacement" "Write revised by claude." 16
export CODEX_STUB_CONTENT_FILE="$bad_replacement"
export CURSOR_STUB_CONTENT_FILE="$bad_replacement"
export CLAUDE_STUB_CONTENT_FILE="$claude_replacement"
out=$(run_subject "$case_dir" true true file-replacement)
assert_line "REVISE_TIER_1_STATUS=no-patch" "$out"
assert_line "REVISE_TIER_2_STATUS=no-patch" "$out"
assert_line "REVISE_TIER_3_STATUS=ok" "$out"
assert_line "REVISE_STATUS=ok" "$out"
assert_line "REVISE_TIER=claude" "$out"
assert_contains "Write revised by claude." "$case_dir/plan.txt"
echo "PASS: case 3"

# 4. All tiers fail with no patch.
clear_stubs
case_dir=$(make_case case4)
before_hash=$(LC_ALL=C shasum -a 256 "$case_dir/plan.txt" | awk '{print $1}')
out=$(run_subject "$case_dir" true true)
after_hash=$(LC_ALL=C shasum -a 256 "$case_dir/plan.txt" | awk '{print $1}')
assert_line "REVISE_TIER_1_STATUS=no-patch" "$out"
assert_line "REVISE_TIER_2_STATUS=no-patch" "$out"
assert_line "REVISE_TIER_3_STATUS=no-patch" "$out"
assert_line "REVISE_STATUS=failed-no-patch" "$out"
assert_line "REVISE_TIER=" "$out"
assert_line "REVISE_PATCH_PATH=" "$out"
[[ "$before_hash" == "$after_hash" ]] || fail "all-fail changed plan"
[[ -f "$case_dir/plan.txt.before-revise" ]] || fail "all-fail did not preserve snapshot"
echo "PASS: case 4"

# 5. Apply check fails validation, then Cursor wins.
clear_stubs
case_dir=$(make_case case5)
bad_context="$TMPROOT/case5-bad-context.diff"
cursor_patch="$TMPROOT/case5-cursor.diff"
write_bad_context_diff "$bad_context"
write_valid_diff "$cursor_patch" "Write revised after apply failure." 17
export CODEX_STUB_CONTENT_FILE="$bad_context"
export CURSOR_STUB_CONTENT_FILE="$cursor_patch"
out=$(run_subject "$case_dir" true true)
assert_line "REVISE_TIER_1_STATUS=invalid-patch" "$out"
assert_line "REVISE_TIER_2_STATUS=ok" "$out"
assert_line "REVISE_TIER=cursor" "$out"
assert_contains "Write revised after apply failure." "$case_dir/plan.txt"
echo "PASS: case 5"

# 6. Emit-plan gate fails, then Cursor wins.
clear_stubs
case_dir=$(make_case case6)
missing_trailer="$TMPROOT/case6-missing-trailer.diff"
cursor_patch="$TMPROOT/case6-cursor.diff"
write_missing_trailer_diff "$missing_trailer"
write_valid_diff "$cursor_patch" "Write revised after emit failure." 18
export CODEX_STUB_CONTENT_FILE="$missing_trailer"
export CURSOR_STUB_CONTENT_FILE="$cursor_patch"
out=$(run_subject "$case_dir" true true)
assert_line "REVISE_TIER_1_STATUS=emit-plan-failed" "$out"
assert_line "REVISE_TIER_2_STATUS=ok" "$out"
assert_contains "Write revised after emit failure." "$case_dir/plan.txt"
echo "PASS: case 6"

# 7. Codex absent, Cursor wins.
clear_stubs
case_dir=$(make_case case7)
cursor_patch="$TMPROOT/case7-cursor.diff"
write_valid_diff "$cursor_patch" "Write revised with codex absent." 19
export CURSOR_STUB_CONTENT_FILE="$cursor_patch"
out=$(run_subject "$case_dir" false true)
assert_line "REVISE_TIER_1_STATUS=skipped-not-present" "$out"
assert_line "REVISE_TIER_2_STATUS=ok" "$out"
assert_line "REVISE_TIER=cursor" "$out"
echo "PASS: case 7"

# 8. Argv defect: missing --plan-file.
clear_stubs
case_dir=$(make_case case8)
set +e
"$SUBJECT" \
    --design-tmpdir "$case_dir" \
    --findings-file "$case_dir/findings.md" \
    --feature-file "$case_dir/feature.txt" \
    --round-num 1 \
    --codex-present true \
    --cursor-present true >"$TMPROOT/case8.out" 2>"$TMPROOT/case8.err"
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "missing --plan-file exit=$rc"
! grep -q '^REVISE_' "$TMPROOT/case8.out" || fail "argv defect emitted KVs"
echo "PASS: case 8"

# 9. Canonical-plan invariant violation also rejects a final-component symlink.
clear_stubs
case_dir=$(make_case case9)
printf '## Plan\n\ndiff_lines: 1\n' >"$TMPROOT/other-plan.txt"
set +e
"$SUBJECT" \
    --design-tmpdir "$case_dir" \
    --plan-file "$TMPROOT/other-plan.txt" \
    --findings-file "$case_dir/findings.md" \
    --feature-file "$case_dir/feature.txt" \
    --round-num 1 \
    --codex-present true \
    --cursor-present true >"$TMPROOT/case9.out" 2>"$TMPROOT/case9.err"
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "canonical invariant exit=$rc"
grep -Fq 'must resolve to DESIGN_TMPDIR/plan.txt' "$TMPROOT/case9.err" || fail "canonical invariant diagnostic missing"

case_dir=$(make_case case9b)
ln -s "$TMPROOT/other-plan.txt" "$case_dir/plan-link.txt"
set +e
"$SUBJECT" \
    --design-tmpdir "$case_dir" \
    --plan-file "$case_dir/plan-link.txt" \
    --findings-file "$case_dir/findings.md" \
    --feature-file "$case_dir/feature.txt" \
    --round-num 1 \
    --codex-present true \
    --cursor-present true >"$TMPROOT/case9b.out" 2>"$TMPROOT/case9b.err"
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "final-component symlink invariant exit=$rc"
grep -Fq 'must resolve to DESIGN_TMPDIR/plan.txt' "$TMPROOT/case9b.err" || fail "final-component symlink diagnostic missing"
echo "PASS: case 9"

# 10. Heading-loss revert, then Cursor wins.
clear_stubs
case_dir=$(make_case case10)
heading_loss="$TMPROOT/case10-heading-loss.diff"
cursor_patch="$TMPROOT/case10-cursor.diff"
write_heading_loss_diff "$heading_loss"
write_valid_diff "$cursor_patch" "Write revised after heading loss." 20
export CODEX_STUB_CONTENT_FILE="$heading_loss"
export CURSOR_STUB_CONTENT_FILE="$cursor_patch"
out=$(run_subject "$case_dir" true true)
assert_line "REVISE_TIER_1_STATUS=invalid-patch" "$out"
assert_line "REVISE_TIER_2_STATUS=ok" "$out"
assert_contains "### NEW: sample.txt" "$case_dir/plan.txt"
assert_contains "Write revised after heading loss." "$case_dir/plan.txt"
echo "PASS: case 10"

# 11. Prompt-source assertion also covers Claude-only fallback.
clear_stubs
case_dir=$(make_case case11)
claude_patch="$TMPROOT/case11-claude.diff"
write_valid_diff "$claude_patch" "Write revised by claude prompt assertion." 21
export CLAUDE_STUB_CONTENT_FILE="$claude_patch"
out=$(run_subject "$case_dir" false false)
assert_line "REVISE_TIER_1_STATUS=skipped-not-present" "$out"
assert_line "REVISE_TIER_2_STATUS=skipped-not-present" "$out"
assert_line "REVISE_TIER_3_STATUS=ok" "$out"
assert_line "REVISE_TIER=claude" "$out"
assert_contains "Write revised by claude prompt assertion." "$case_dir/plan.txt"
echo "PASS: case 11"

# 12. Tier-4 fenced file-replacement fallback succeeds and preserves forensics.
clear_stubs
case_dir=$(make_case case12)
codex_replacement="$TMPROOT/case12-codex.txt"
write_fenced_replacement "$codex_replacement" "Write revised by fallback codex." 22
export CODEX_STUB_CONTENT_FILE="$codex_replacement"
out=$(run_subject "$case_dir" true true)
assert_line "REVISE_TIER_1_STATUS=no-patch" "$out"
assert_line "REVISE_TIER_2_STATUS=no-patch" "$out"
assert_line "REVISE_TIER_3_STATUS=no-patch" "$out"
assert_line "REVISE_TIER_4_STATUS=ok" "$out"
assert_line "REVISE_STATUS=ok-fallback" "$out"
assert_line "REVISE_TIER=codex" "$out"
assert_line "REVISE_WINNING_TIER=codex" "$out"
printf '%s\n' "$out" | grep -Eq '^REVISE_PATCH_PATH=.*/plan-review/round-1/revise/codex-fallback-output\.txt$' || fail "fallback patch path should point at codex-fallback-output.txt"
assert_contains "Write revised by fallback codex." "$case_dir/plan.txt"
assert_contains "REVISE_STATUS=ok-fallback" "$case_dir/plan-review/round-1/revise/revise.env"
assert_contains "REVISE_TIER_4_STATUS=ok" "$case_dir/plan-review/round-1/revise/revise.env"
[[ -f "$case_dir/plan-review/round-1/revise/codex-output.txt" ]] || fail "tier-1 codex output should remain for forensics"
[[ -f "$case_dir/plan-review/round-1/revise/codex-fallback-output.txt" ]] || fail "tier-4 codex output should be preserved"
echo "PASS: case 12"

# 13. Tier-4 status keeps the worst non-ok fallback failure.
clear_stubs
case_dir=$(make_case case13)
bad_replacement="$TMPROOT/case13-heading-loss.txt"
write_heading_loss_replacement "$bad_replacement" "Plan without any file headings." 26
export CODEX_STUB_CONTENT_FILE="$bad_replacement"
out=$(run_subject "$case_dir" true true)
assert_line "REVISE_TIER_1_STATUS=no-patch" "$out"
assert_line "REVISE_TIER_2_STATUS=no-patch" "$out"
assert_line "REVISE_TIER_3_STATUS=no-patch" "$out"
assert_line "REVISE_TIER_4_STATUS=invalid-patch" "$out"
assert_line "REVISE_STATUS=failed-validation" "$out"
echo "PASS: case 13"

# 14. Unified-diff extraction stops at the closing fence.
clear_stubs
case_dir=$(make_case case14)
fenced_diff="$TMPROOT/case14.diff"
write_fenced_diff_with_trailing_prose "$fenced_diff" "Write revised from fenced diff." 23
export CODEX_STUB_CONTENT_FILE="$fenced_diff"
out=$(run_subject "$case_dir" true true)
assert_line "REVISE_TIER_1_STATUS=ok" "$out"
assert_contains "Write revised from fenced diff." "$case_dir/plan.txt"
echo "PASS: case 14"

# 15. Unified-diff extraction ignores later fenced diffs.
clear_stubs
case_dir=$(make_case case15)
multi_fence_diff="$TMPROOT/case15.diff"
write_multi_fence_diff "$multi_fence_diff" "Write revised from first fenced diff." 24
export CODEX_STUB_CONTENT_FILE="$multi_fence_diff"
out=$(run_subject "$case_dir" true true)
assert_line "REVISE_TIER_1_STATUS=ok" "$out"
assert_contains "Write revised from first fenced diff." "$case_dir/plan.txt"
echo "PASS: case 15"

# 16. Unified-diff extraction prefers the last unfenced canonical patch.
clear_stubs
case_dir=$(make_case case16)
illustrative_diff="$TMPROOT/case16.diff"
write_illustrative_then_real_diff "$illustrative_diff" "Write revised from real diff." 25
export CODEX_STUB_CONTENT_FILE="$illustrative_diff"
out=$(run_subject "$case_dir" true true)
assert_line "REVISE_TIER_1_STATUS=ok" "$out"
assert_contains "Write revised from real diff." "$case_dir/plan.txt"
echo "PASS: case 16"

echo "PASS: test-revise-plan-with-waterfall.sh"
