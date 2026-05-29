#!/usr/bin/env bash
# Offline harness for skills/design/scripts/revise-plan-with-waterfall.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SCRIPT="$ROOT/skills/design/scripts/revise-plan-with-waterfall.sh"

fail() { printf '%s\n' "$1" >&2; exit 1; }

assert_kv() {
    local haystack="$1" key="$2" expected="$3"
    printf '%s\n' "$haystack" | grep -q "^${key}=${expected}\$" || fail "expected ${key}=${expected}"
}

assert_has_key() {
    local haystack="$1" key="$2"
    printf '%s\n' "$haystack" | grep -q "^${key}=" || fail "missing ${key}= line"
}

assert_lacks_key() {
    local haystack="$1" key="$2"
    if printf '%s\n' "$haystack" | grep -q "^${key}="; then
        fail "unexpected ${key}= line"
    fi
}

assert_kv_suffix() {
    local haystack="$1" key="$2" suffix="$3"
    printf '%s\n' "$haystack" | grep -q "^${key}=.*${suffix}\$" || fail "expected ${key} suffix ${suffix}"
}

assert_file_kv() {
    local file="$1" key="$2" expected="$3"
    grep -q "^${key}=${expected}\$" "$file" || fail "expected ${file} to contain ${key}=${expected}"
}

assert_file_kv_suffix() {
    local file="$1" key="$2" suffix="$3"
    grep -q "^${key}=.*${suffix}\$" "$file" || fail "expected ${file} to contain ${key} suffix ${suffix}"
}

write_plan() {
    local target="$1"
    cat >"$target" <<'EOF'
## Plan
alpha
diff_lines: 1
EOF
}

write_feature_and_findings() {
    local dir="$1"
    printf '%s\n' 'feature context' >"$dir/feature.txt"
    printf '%s\n' '### FINDING_1:' >"$dir/findings.md"
}

write_launcher_stub() {
    local target="$1"
    cat >"$target" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
tool="${LARCH_TOOL_OVERRIDE:-}"
output=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tool) tool="${2:?}"; shift 2 ;;
        --output) output="${2:?}"; shift 2 ;;
        *) shift ;;
    esac
done
[[ -n "$tool" && -n "$output" ]] || exit 2
src="${RESPONSE_DIR:?}/${tool}.txt"
if [[ -f "$src" ]]; then
    cp "$src" "$output"
else
    : >"$output"
fi
EOF
    chmod +x "$target"
}

write_claude_stub() {
    local target="$1"
    cat >"$target" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
export LARCH_TOOL_OVERRIDE=claude
"${LAUNCH_REVIEW_STUB:?}" "$@"
EOF
    chmod +x "$target"
}

write_design_driver_stub() {
    local target="$1"
    cat >"$target" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
design_tmpdir=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) design_tmpdir="${2:?}"; shift 2 ;;
        *) shift ;;
    esac
done
[[ -n "$design_tmpdir" ]] || exit 2
last_line=$(awk 'NF { line=$0 } END { print line }' "$design_tmpdir/plan.txt")
if [[ "$last_line" =~ ^diff_lines:\ [0-9]+$ ]]; then
    printf '%s\n' 'EMIT_PLAN_STATUS=ok'
else
    printf '%s\n' 'EMIT_PLAN_STATUS=fail'
fi
EOF
    chmod +x "$target"
}

setup_case() {
    local dir="$1"
    mkdir -p "$dir"
    git -C "$dir" init -q
    write_plan "$dir/plan.txt"
    write_feature_and_findings "$dir"
}

run_case() {
    local dir="$1"
    shift
    RESPONSE_DIR="$dir/responses" \
    LAUNCH_REVIEW_STUB="$dir/launch-review.sh" \
    LARCH_TEST_LAUNCH_CODEX_REVIEW="$dir/launch-review.sh" \
    LARCH_TEST_LAUNCH_CURSOR_REVIEW="$dir/launch-review.sh" \
    LARCH_TEST_LAUNCH_CLAUDE_REVIEW="$dir/launch-claude-review.sh" \
    LARCH_TEST_DESIGN_DRIVER="$dir/design-driver.sh" \
    LARCH_QUIET_DISABLE=1 \
    "$SCRIPT" \
        --design-tmpdir "$dir" \
        --plan-file "$dir/plan.txt" \
        --findings-file "$dir/findings.md" \
        --feature-file "$dir/feature.txt" \
        --round-num 1 \
        --codex-present true \
        --cursor-present true \
        "$@"
}

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-revise-plan-with-waterfall.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

bash -n "$SCRIPT" || fail "bash -n failed"

set +e
"$SCRIPT" --design-tmpdir "$TMP" --plan-file "$TMP/plan.txt" --findings-file "$TMP/findings.md" --feature-file "$TMP/feature.txt" --round-num 1 --codex-present true 2>/dev/null
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "missing --cursor-present should exit 2"

set +e
missing_plan_out=$(
    "$SCRIPT" --design-tmpdir "$TMP" --findings-file "$TMP/findings.md" --feature-file "$TMP/feature.txt" --round-num 1 --codex-present true --cursor-present true 2>/dev/null
)
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "missing --plan-file should exit 2"
assert_lacks_key "$missing_plan_out" REVISE_STATUS

COMMON="$TMP/common"
mkdir -p "$COMMON/responses"
write_launcher_stub "$COMMON/launch-review.sh"
write_claude_stub "$COMMON/launch-claude-review.sh"
write_design_driver_stub "$COMMON/design-driver.sh"

echo "=== non-canonical plan path is rejected ==="
C0="$TMP/case0"
setup_case "$C0"
cp "$COMMON/launch-review.sh" "$C0/launch-review.sh"
cp "$COMMON/launch-claude-review.sh" "$C0/launch-claude-review.sh"
cp "$COMMON/design-driver.sh" "$C0/design-driver.sh"
cp "$C0/plan.txt" "$C0/not-plan.txt"
set +e
out0=$(
    RESPONSE_DIR="$C0/responses" \
    LAUNCH_REVIEW_STUB="$C0/launch-review.sh" \
    LARCH_TEST_LAUNCH_CODEX_REVIEW="$C0/launch-review.sh" \
    LARCH_TEST_LAUNCH_CURSOR_REVIEW="$C0/launch-review.sh" \
    LARCH_TEST_LAUNCH_CLAUDE_REVIEW="$C0/launch-claude-review.sh" \
    LARCH_TEST_DESIGN_DRIVER="$C0/design-driver.sh" \
    LARCH_QUIET_DISABLE=1 \
    "$SCRIPT" \
        --design-tmpdir "$C0" \
        --plan-file "$C0/not-plan.txt" \
        --findings-file "$C0/findings.md" \
        --feature-file "$C0/feature.txt" \
        --round-num 1 \
        --codex-present true \
        --cursor-present true 2>&1
)
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "non-canonical plan path should exit 2"
printf '%s\n' "$out0" | grep -q 'must resolve to DESIGN_TMPDIR/plan.txt' || fail "non-canonical plan path should explain canonical invariant"

echo "=== symlinked plan path resolving to plan.txt is accepted ==="
C0S="$TMP/case0-symlink"
setup_case "$C0S"
cp "$COMMON/launch-review.sh" "$C0S/launch-review.sh"
cp "$COMMON/launch-claude-review.sh" "$C0S/launch-claude-review.sh"
cp "$COMMON/design-driver.sh" "$C0S/design-driver.sh"
mkdir -p "$C0S/responses"
ln -s "$C0S/plan.txt" "$C0S/linked-plan.txt"
cat >"$C0S/responses/codex.txt" <<'EOF'
```diff
--- a/plan.txt
+++ b/plan.txt
@@ -1,3 +1,3 @@
 ## Plan
-alpha
+symlink ok
 diff_lines: 1
```
EOF
out0s=$(
    RESPONSE_DIR="$C0S/responses" \
    LAUNCH_REVIEW_STUB="$C0S/launch-review.sh" \
    LARCH_TEST_LAUNCH_CODEX_REVIEW="$C0S/launch-review.sh" \
    LARCH_TEST_LAUNCH_CURSOR_REVIEW="$C0S/launch-review.sh" \
    LARCH_TEST_LAUNCH_CLAUDE_REVIEW="$C0S/launch-claude-review.sh" \
    LARCH_TEST_DESIGN_DRIVER="$C0S/design-driver.sh" \
    LARCH_QUIET_DISABLE=1 \
    "$SCRIPT" \
        --design-tmpdir "$C0S" \
        --plan-file "$C0S/linked-plan.txt" \
        --findings-file "$C0S/findings.md" \
        --feature-file "$C0S/feature.txt" \
        --round-num 1 \
        --codex-present true \
        --cursor-present true
)
assert_kv "$out0s" REVISE_STATUS ok
grep -q '^symlink ok$' "$C0S/plan.txt" || fail "symlinked canonical plan path should succeed"

# Legacy acceptance matrix: keep the original scenario spine traceable in cases 1-9.

echo "=== later valid unified diff beats earlier wrong-path diff ==="
C1="$TMP/case1"
setup_case "$C1"
cp "$COMMON/launch-review.sh" "$C1/launch-review.sh"
cp "$COMMON/launch-claude-review.sh" "$C1/launch-claude-review.sh"
cp "$COMMON/design-driver.sh" "$C1/design-driver.sh"
mkdir -p "$C1/responses"
cat >"$C1/responses/codex.txt" <<'EOF'
```diff
--- a/notes.txt
+++ b/notes.txt
@@ -1 +1 @@
-bad
+badder
```
```diff
--- a/plan.txt
+++ b/plan.txt
@@ -1,3 +1,3 @@
 ## Plan
-alpha
+beta
 diff_lines: 1
```
EOF
out1=$(run_case "$C1")
assert_kv "$out1" REVISE_STATUS ok
assert_kv "$out1" REVISE_TIER_1_STATUS ok
assert_kv "$out1" REVISE_TIER_4_STATUS not-attempted
grep -q '^beta$' "$C1/plan.txt" || fail "case1 should apply later valid patch"

echo "=== earlier valid unified diff beats later corrupt wrong-path diff ==="
C1B="$TMP/case1b"
setup_case "$C1B"
cp "$COMMON/launch-review.sh" "$C1B/launch-review.sh"
cp "$COMMON/launch-claude-review.sh" "$C1B/launch-claude-review.sh"
cp "$COMMON/design-driver.sh" "$C1B/design-driver.sh"
mkdir -p "$C1B/responses"
cat >"$C1B/responses/codex.txt" <<'EOF'
```diff
--- a/plan.txt
+++ b/plan.txt
@@ -1,3 +1,3 @@
 ## Plan
-alpha
+gamma
 diff_lines: 1
```
```diff
--- a/notes.txt
+++ b/notes.txt
@@ -1 +1 @@
-bad
+badder
```
EOF
out1b=$(run_case "$C1B")
assert_kv "$out1b" REVISE_STATUS ok
assert_kv "$out1b" REVISE_TIER_1_STATUS ok
grep -q '^gamma$' "$C1B/plan.txt" || fail "case1b should keep the earlier valid plan patch"

echo "=== timestamped headers classify as valid patch ==="
C2="$TMP/case2"
setup_case "$C2"
cp "$COMMON/launch-review.sh" "$C2/launch-review.sh"
cp "$COMMON/launch-claude-review.sh" "$C2/launch-claude-review.sh"
cp "$COMMON/design-driver.sh" "$C2/design-driver.sh"
mkdir -p "$C2/responses"
cat >"$C2/responses/codex.txt" <<'EOF'
```diff
--- a/plan.txt	2026-05-28 10:00:00
+++ b/plan.txt	2026-05-28 10:00:01
@@ -1,3 +1,3 @@
 ## Plan
-alpha
+timestamped
 diff_lines: 1
```
EOF
out2=$(run_case "$C2")
assert_kv "$out2" REVISE_STATUS ok
assert_kv "$out2" REVISE_TIER_1_STATUS ok
assert_kv "$out2" REVISE_TIER_4_STATUS not-attempted
grep -q '^timestamped$' "$C2/plan.txt" || fail "case2 should accept timestamped headers"

echo "=== unfenced diff excludes trailing prose ==="
C2B="$TMP/case2b"
setup_case "$C2B"
cp "$COMMON/launch-review.sh" "$C2B/launch-review.sh"
cp "$COMMON/launch-claude-review.sh" "$C2B/launch-claude-review.sh"
cp "$COMMON/design-driver.sh" "$C2B/design-driver.sh"
mkdir -p "$C2B/responses"
cat >"$C2B/responses/codex.txt" <<'EOF'
--- a/plan.txt
+++ b/plan.txt
@@ -1,3 +1,3 @@
 ## Plan
-alpha
+delta
 diff_lines: 1

Summary: trailing prose must not be part of the patch.
EOF
out2b=$(run_case "$C2B")
assert_kv "$out2b" REVISE_STATUS ok
assert_kv "$out2b" REVISE_TIER_1_STATUS ok
assert_kv "$out2b" REVISE_TIER_4_STATUS not-attempted
grep -q '^delta$' "$C2B/plan.txt" || fail "case2b should apply the diff without trailing prose"

echo "=== leading prose before a valid unfenced diff is ignored ==="
C2C="$TMP/case2c"
setup_case "$C2C"
cp "$COMMON/launch-review.sh" "$C2C/launch-review.sh"
cp "$COMMON/launch-claude-review.sh" "$C2C/launch-claude-review.sh"
cp "$COMMON/design-driver.sh" "$C2C/design-driver.sh"
mkdir -p "$C2C/responses"
cat >"$C2C/responses/codex.txt" <<'EOF'
I revised the plan below.

--- a/plan.txt
+++ b/plan.txt
@@ -1,3 +1,3 @@
 ## Plan
-alpha
+leading prose
 diff_lines: 1
EOF
out2c=$(run_case "$C2C")
assert_kv "$out2c" REVISE_STATUS ok
assert_kv "$out2c" REVISE_TIER_1_STATUS ok
assert_kv "$out2c" REVISE_TIER_4_STATUS not-attempted
grep -q '^leading prose$' "$C2C/plan.txt" || fail "case2c should accept a diff after leading prose"

echo "=== corrupt fenced diff does not suppress a later valid raw diff ==="
C2D="$TMP/case2d"
setup_case "$C2D"
cp "$COMMON/launch-review.sh" "$C2D/launch-review.sh"
cp "$COMMON/launch-claude-review.sh" "$C2D/launch-claude-review.sh"
cp "$COMMON/design-driver.sh" "$C2D/design-driver.sh"
mkdir -p "$C2D/responses"
cat >"$C2D/responses/codex.txt" <<'EOF'
```diff
--- a/notes.txt
+++ b/notes.txt
@@ -1 +1 @@
-bad
+still bad
```

--- a/plan.txt
+++ b/plan.txt
@@ -1,3 +1,3 @@
 ## Plan
-alpha
+raw fallback
 diff_lines: 1
EOF
out2d=$(run_case "$C2D")
assert_kv "$out2d" REVISE_STATUS ok
assert_kv "$out2d" REVISE_TIER_1_STATUS ok
assert_kv "$out2d" REVISE_TIER_4_STATUS not-attempted
grep -q '^raw fallback$' "$C2D/plan.txt" || fail "case2d should scan the full response after fenced candidates"

echo "=== trailing markdown bullets are excluded from unified diff extraction ==="
C2E="$TMP/case2e"
setup_case "$C2E"
cp "$COMMON/launch-review.sh" "$C2E/launch-review.sh"
cp "$COMMON/launch-claude-review.sh" "$C2E/launch-claude-review.sh"
cp "$COMMON/design-driver.sh" "$C2E/design-driver.sh"
mkdir -p "$C2E/responses"
cat >"$C2E/responses/codex.txt" <<'EOF'
--- a/plan.txt
+++ b/plan.txt
@@ -1,3 +1,3 @@
 ## Plan
-alpha
+bullet safe
 diff_lines: 1

- Summary bullet outside the diff.
EOF
out2e=$(run_case "$C2E")
assert_kv "$out2e" REVISE_STATUS ok
assert_kv "$out2e" REVISE_TIER_1_STATUS ok
assert_kv "$out2e" REVISE_TIER_4_STATUS not-attempted
grep -q '^bullet safe$' "$C2E/plan.txt" || fail "case2e should stop before trailing markdown bullets"

echo "=== blank lines between hunks do not split a valid patch ==="
C2F="$TMP/case2f"
setup_case "$C2F"
cp "$COMMON/launch-review.sh" "$C2F/launch-review.sh"
cp "$COMMON/launch-claude-review.sh" "$C2F/launch-claude-review.sh"
cp "$COMMON/design-driver.sh" "$C2F/design-driver.sh"
mkdir -p "$C2F/responses"
cat >"$C2F/plan.txt" <<'EOF'
## Plan
alpha
bravo
charlie
diff_lines: 3
EOF
cat >"$C2F/responses/codex.txt" <<'EOF'
--- a/plan.txt
+++ b/plan.txt
@@ -1,3 +1,3 @@
 ## Plan
-alpha
+alpha updated
 bravo

@@ -3,2 +3,2 @@
 charlie
-diff_lines: 3
+diff_lines: 4
EOF
out2f=$(run_case "$C2F")
assert_kv "$out2f" REVISE_STATUS ok
assert_kv "$out2f" REVISE_TIER_1_STATUS ok
assert_kv "$out2f" REVISE_TIER_4_STATUS not-attempted
grep -q '^alpha updated$' "$C2F/plan.txt" || fail "case2f should keep the first hunk"
grep -q '^diff_lines: 4$' "$C2F/plan.txt" || fail "case2f should keep the second hunk"

echo "=== overlapping embedded headers do not create partial duplicate candidates ==="
C2G="$TMP/case2g"
setup_case "$C2G"
cp "$COMMON/launch-review.sh" "$C2G/launch-review.sh"
cp "$COMMON/launch-claude-review.sh" "$C2G/launch-claude-review.sh"
cp "$COMMON/design-driver.sh" "$C2G/design-driver.sh"
mkdir -p "$C2G/responses"
cat >"$C2G/plan.txt" <<'EOF'
## Plan
keep this
--- a/embedded.txt
+++ b/embedded.txt
diff_lines: 3
EOF
cat >"$C2G/responses/codex.txt" <<'EOF'
diff --git a/plan.txt b/plan.txt
--- a/plan.txt
+++ b/plan.txt
@@ -1,4 +1,4 @@
 ## Plan
 keep this
 --- a/embedded.txt
-+++ b/embedded.txt
++++ b/embedded.txt
 diff_lines: 3
EOF
out2g=$(run_case "$C2G")
assert_kv "$out2g" REVISE_STATUS ok
assert_kv "$out2g" REVISE_TIER_1_STATUS ok
assert_kv "$out2g" REVISE_TIER_4_STATUS not-attempted
grep -q '^+++ b/embedded.txt$' "$C2G/plan.txt" || fail "case2g should apply the full diff rather than an overlapping partial candidate"

echo "=== wrong-path invalid tiers 1-3 fall through to tier-4 success ==="
C3="$TMP/case3"
setup_case "$C3"
cp "$COMMON/launch-claude-review.sh" "$C3/launch-claude-review.sh"
cp "$COMMON/design-driver.sh" "$C3/design-driver.sh"
mkdir -p "$C3/responses"
cat >"$C3/launch-review.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
tool="${LARCH_TOOL_OVERRIDE:-}"
output=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tool) tool="${2:?}"; shift 2 ;;
        --output) output="${2:?}"; shift 2 ;;
        *) shift ;;
    esac
done
[[ -n "$tool" && -n "$output" ]] || exit 2
if [[ "$output" == *"/codex-output.txt" && -f "${DESIGN_TMPDIR:-}/.tier4" ]]; then
    cp "${RESPONSE_DIR:?}/codex-fallback.txt" "$output"
elif [[ -f "${RESPONSE_DIR:?}/${tool}.txt" ]]; then
    cp "${RESPONSE_DIR:?}/${tool}.txt" "$output"
else
    : >"$output"
fi
if [[ "$output" == *"/claude-output.txt" ]]; then
    : >"${DESIGN_TMPDIR:?}/.tier4"
fi
EOF
chmod +x "$C3/launch-review.sh"
cat >"$C3/responses/codex.txt" <<'EOF'
--- a/notes.txt
+++ b/notes.txt
@@ -1 +1 @@
-bad
+still bad
EOF
cp "$C3/responses/codex.txt" "$C3/responses/cursor.txt"
cp "$C3/responses/codex.txt" "$C3/responses/claude.txt"
cat >"$C3/responses/codex-fallback.txt" <<'EOF'
## Plan
fallback win
diff_lines: 1
EOF
out3=$(DESIGN_TMPDIR="$C3" run_case "$C3")
assert_kv "$out3" REVISE_STATUS ok-fallback
assert_kv "$out3" REVISE_TIER_1_STATUS invalid-patch
assert_kv "$out3" REVISE_TIER_2_STATUS invalid-patch
assert_kv "$out3" REVISE_TIER_3_STATUS invalid-patch
assert_kv "$out3" REVISE_TIER_4_STATUS ok
assert_kv_suffix "$out3" REVISE_PATCH_PATH "/plan-review/round-1/revise/codex-output.txt"
[[ ! -e "$C3/plan-review/round-1/revise/codex-fallback-output.txt" ]] || fail "fallback should reuse codex-output.txt"

echo "=== file replacement prefers last complete plan and keeps trailer outside fence ==="
C4="$TMP/case4"
setup_case "$C4"
cp "$COMMON/launch-review.sh" "$C4/launch-review.sh"
cp "$COMMON/launch-claude-review.sh" "$C4/launch-claude-review.sh"
cp "$COMMON/design-driver.sh" "$C4/design-driver.sh"
mkdir -p "$C4/responses"
printf '\n' >"$C4/responses/codex.txt"
printf '\n' >"$C4/responses/cursor.txt"
printf '\n' >"$C4/responses/claude.txt"
cat >"$C4/launch-review.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
tool="${LARCH_TOOL_OVERRIDE:-}"
output=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tool) tool="${2:?}"; shift 2 ;;
        --output) output="${2:?}"; shift 2 ;;
        *) shift ;;
    esac
done
[[ -n "$tool" && -n "$output" ]] || exit 2
if [[ "$output" == *"/codex-output.txt" && -f "${DESIGN_TMPDIR:?}/.tier4" ]]; then
    cat >"$output" <<'INNER'
```markdown
## Plan
illustrative
diff_lines: 1
```

```markdown
## Plan
```text
diff_lines: 1
```
final replacement
```
diff_lines: 2
INNER
elif [[ -f "${RESPONSE_DIR:?}/${tool}.txt" ]]; then
    cp "${RESPONSE_DIR:?}/${tool}.txt" "$output"
else
    : >"$output"
fi
if [[ "$output" == *"/claude-output.txt" ]]; then
    : >"${DESIGN_TMPDIR:?}/.tier4"
fi
EOF
chmod +x "$C4/launch-review.sh"
out4=$(DESIGN_TMPDIR="$C4" run_case "$C4")
assert_kv "$out4" REVISE_STATUS ok-fallback
assert_kv "$out4" REVISE_TIER_4_STATUS ok
grep -q '^final replacement$' "$C4/plan.txt" || fail "case4 should keep the last complete replacement plan"
grep -q '^```$' "$C4/plan.txt" || fail "case4 should preserve literal standalone fences inside the plan body"

echo "=== stale unified-diff candidates from an earlier run are ignored ==="
C4B="$TMP/case4b"
setup_case "$C4B"
cp "$COMMON/launch-review.sh" "$C4B/launch-review.sh"
cp "$COMMON/launch-claude-review.sh" "$C4B/launch-claude-review.sh"
cp "$COMMON/design-driver.sh" "$C4B/design-driver.sh"
mkdir -p "$C4B/responses" "$C4B/plan-review/round-1/revise"
cat >"$C4B/plan-review/round-1/revise/codex-output-candidate-002.patch" <<'EOF'
--- a/plan.txt
+++ b/plan.txt
@@ -1,3 +1,3 @@
 ## Plan
-alpha
+stale patch
 diff_lines: 1
EOF
cat >"$C4B/responses/codex.txt" <<'EOF'
```diff
--- a/notes.txt
+++ b/notes.txt
@@ -1 +1 @@
-bad
+still bad
```
EOF
cat >"$C4B/responses/cursor.txt" <<'EOF'
```diff
--- a/plan.txt
+++ b/plan.txt
@@ -1,3 +1,3 @@
 ## Plan
-alpha
+fresh cursor
 diff_lines: 1
```
EOF
out4b=$(run_case "$C4B")
assert_kv "$out4b" REVISE_STATUS ok
assert_kv "$out4b" REVISE_TIER_1_STATUS invalid-patch
assert_kv "$out4b" REVISE_TIER_2_STATUS ok
grep -q '^fresh cursor$' "$C4B/plan.txt" || fail "case4b should ignore stale extracted candidates from earlier runs"

echo "=== no candidate patch downgrades to no-patch and continues ==="
C5="$TMP/case5"
setup_case "$C5"
cp "$COMMON/launch-review.sh" "$C5/launch-review.sh"
cp "$COMMON/launch-claude-review.sh" "$C5/launch-claude-review.sh"
cp "$COMMON/design-driver.sh" "$C5/design-driver.sh"
mkdir -p "$C5/responses"
printf '%s\n' 'no diff candidate here' >"$C5/responses/codex.txt"
cat >"$C5/responses/cursor.txt" <<'EOF'
```diff
--- a/plan.txt
+++ b/plan.txt
@@ -1,3 +1,3 @@
 ## Plan
-alpha
+cursor win
 diff_lines: 1
```
EOF
out5=$(run_case "$C5")
assert_kv "$out5" REVISE_STATUS ok
assert_kv "$out5" REVISE_TIER_1_STATUS no-patch
assert_kv "$out5" REVISE_TIER_2_STATUS ok
assert_kv "$out5" REVISE_TIER_4_STATUS not-attempted
grep -q '^cursor win$' "$C5/plan.txt" || fail "case5 should continue after a no-patch tier"

echo "=== full no-patch failure still emits tier-4 status ==="
C6="$TMP/case6"
setup_case "$C6"
cp "$COMMON/launch-review.sh" "$C6/launch-review.sh"
cp "$COMMON/launch-claude-review.sh" "$C6/launch-claude-review.sh"
cp "$COMMON/design-driver.sh" "$C6/design-driver.sh"
mkdir -p "$C6/responses"
out6=$(run_case "$C6")
assert_kv "$out6" REVISE_STATUS failed-no-patch
assert_kv "$out6" REVISE_TIER_1_STATUS no-patch
assert_kv "$out6" REVISE_TIER_2_STATUS no-patch
assert_kv "$out6" REVISE_TIER_3_STATUS no-patch
assert_kv "$out6" REVISE_TIER_4_STATUS no-patch
assert_has_key "$out6" REVISE_PATCH_PATH

echo "=== heading-loss patch is rejected and prior plan is restored before cursor fallback ==="
C7="$TMP/case7"
setup_case "$C7"
cp "$COMMON/launch-review.sh" "$C7/launch-review.sh"
cp "$COMMON/launch-claude-review.sh" "$C7/launch-claude-review.sh"
cp "$COMMON/design-driver.sh" "$C7/design-driver.sh"
mkdir -p "$C7/responses"
cat >"$C7/plan.txt" <<'EOF'
## Plan
### NEW: keep heading
alpha
diff_lines: 1
EOF
cat >"$C7/responses/codex.txt" <<'EOF'
```diff
--- a/plan.txt
+++ b/plan.txt
@@ -1,4 +1,3 @@
 ## Plan
-### NEW: keep heading
-alpha
+heading removed
 diff_lines: 1
```
EOF
cat >"$C7/responses/cursor.txt" <<'EOF'
```diff
--- a/plan.txt
+++ b/plan.txt
@@ -1,4 +1,4 @@
 ## Plan
 ### NEW: keep heading
-alpha
+cursor restored
 diff_lines: 1
```
EOF
out7=$(run_case "$C7")
assert_kv "$out7" REVISE_STATUS ok
assert_kv "$out7" REVISE_TIER_1_STATUS invalid-patch
assert_kv "$out7" REVISE_TIER_2_STATUS ok
grep -q '^### NEW: keep heading$' "$C7/plan.txt" || fail "case7 should preserve at least one heading"
grep -q '^cursor restored$' "$C7/plan.txt" || fail "case7 should restore the original plan before cursor applies"

echo "=== emit-plan failure restores the snapshot before the next tier applies ==="
C8="$TMP/case8"
setup_case "$C8"
cp "$COMMON/launch-review.sh" "$C8/launch-review.sh"
cp "$COMMON/launch-claude-review.sh" "$C8/launch-claude-review.sh"
mkdir -p "$C8/responses"
cat >"$C8/design-driver.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
state="${DESIGN_TMPDIR:?}/emit.count"
count=0
if [[ -f "$state" ]]; then
    count=$(cat "$state")
fi
count=$((count + 1))
printf '%s\n' "$count" >"$state"
if [[ "$count" -eq 1 ]]; then
    printf '%s\n' 'EMIT_PLAN_STATUS=fail'
else
    printf '%s\n' 'EMIT_PLAN_STATUS=ok'
fi
EOF
chmod +x "$C8/design-driver.sh"
cat >"$C8/responses/codex.txt" <<'EOF'
```diff
--- a/plan.txt
+++ b/plan.txt
@@ -1,3 +1,3 @@
 ## Plan
-alpha
+emit failure
 diff_lines: 1
```
EOF
cat >"$C8/responses/cursor.txt" <<'EOF'
```diff
--- a/plan.txt
+++ b/plan.txt
@@ -1,3 +1,3 @@
 ## Plan
-alpha
+cursor after emit
 diff_lines: 1
```
EOF
out8=$(DESIGN_TMPDIR="$C8" run_case "$C8")
assert_kv "$out8" REVISE_STATUS ok
assert_kv "$out8" REVISE_TIER_1_STATUS emit-plan-failed
assert_kv "$out8" REVISE_TIER_2_STATUS ok
assert_kv "$out8" REVISE_TIER_4_STATUS not-attempted
grep -q '^cursor after emit$' "$C8/plan.txt" || fail "case8 should restore the snapshot before the cursor tier"

echo "=== mismatched hunk counts still apply with --recount ==="
C8B="$TMP/case8b"
setup_case "$C8B"
cp "$COMMON/launch-review.sh" "$C8B/launch-review.sh"
cp "$COMMON/launch-claude-review.sh" "$C8B/launch-claude-review.sh"
cp "$COMMON/design-driver.sh" "$C8B/design-driver.sh"
mkdir -p "$C8B/responses"
cat >"$C8B/responses/codex.txt" <<'EOF'
--- a/plan.txt
+++ b/plan.txt
@@ -1,99 +1,99 @@
 ## Plan
-alpha
+recount win
 diff_lines: 1
EOF
out8b=$(run_case "$C8B")
assert_kv "$out8b" REVISE_STATUS ok
assert_kv "$out8b" REVISE_TIER_1_STATUS ok
assert_kv "$out8b" REVISE_TIER_4_STATUS not-attempted
grep -q '^recount win$' "$C8B/plan.txt" || fail "case8b should accept miscounted hunks via --recount"

echo "=== mismatched context is rejected before later fallback succeeds ==="
C8C="$TMP/case8c"
setup_case "$C8C"
cp "$COMMON/launch-claude-review.sh" "$C8C/launch-claude-review.sh"
cp "$COMMON/design-driver.sh" "$C8C/design-driver.sh"
mkdir -p "$C8C/responses"
cat >"$C8C/launch-review.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
tool="${LARCH_TOOL_OVERRIDE:-}"
output=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tool) tool="${2:?}"; shift 2 ;;
        --output) output="${2:?}"; shift 2 ;;
        *) shift ;;
    esac
done
[[ -n "$tool" && -n "$output" ]] || exit 2
if [[ "$output" == *"/codex-output.txt" && -f "${DESIGN_TMPDIR:?}/.tier4" ]]; then
    cat >"$output" <<'INNER'
## Plan
context fallback
diff_lines: 1
INNER
elif [[ -f "${RESPONSE_DIR:?}/${tool}.txt" ]]; then
    cp "${RESPONSE_DIR:?}/${tool}.txt" "$output"
else
    : >"$output"
fi
if [[ "$output" == *"/claude-output.txt" ]]; then
    : >"${DESIGN_TMPDIR:?}/.tier4"
fi
EOF
chmod +x "$C8C/launch-review.sh"
cat >"$C8C/responses/codex.txt" <<'EOF'
--- a/plan.txt
+++ b/plan.txt
@@ -1,3 +1,3 @@
 ## Plan
-wrong context
+never applies
 diff_lines: 1
EOF
cp "$C8C/responses/codex.txt" "$C8C/responses/cursor.txt"
cp "$C8C/responses/codex.txt" "$C8C/responses/claude.txt"
out8c=$(DESIGN_TMPDIR="$C8C" run_case "$C8C")
assert_kv "$out8c" REVISE_STATUS ok-fallback
assert_kv "$out8c" REVISE_TIER_1_STATUS invalid-patch
assert_kv "$out8c" REVISE_TIER_2_STATUS invalid-patch
assert_kv "$out8c" REVISE_TIER_3_STATUS invalid-patch
assert_kv "$out8c" REVISE_TIER_4_STATUS ok
grep -q '^context fallback$' "$C8C/plan.txt" || fail "case8c should reject mismatched diff context"

echo "=== long-line corrupt multi-hunk response falls back to file replacement ==="
C8D="$TMP/case8d"
setup_case "$C8D"
cp "$COMMON/launch-claude-review.sh" "$C8D/launch-claude-review.sh"
cp "$COMMON/design-driver.sh" "$C8D/design-driver.sh"
mkdir -p "$C8D/responses"
python3 - <<'PY' >"$C8D/plan.txt"
print("## Plan")
print("A" * 5000)
print("B" * 5000)
print("diff_lines: 2")
PY
cat >"$C8D/launch-review.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
tool="${LARCH_TOOL_OVERRIDE:-}"
output=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tool) tool="${2:?}"; shift 2 ;;
        --output) output="${2:?}"; shift 2 ;;
        *) shift ;;
    esac
done
[[ -n "$tool" && -n "$output" ]] || exit 2
if [[ "$output" == *"/codex-output.txt" && -f "${DESIGN_TMPDIR:?}/.tier4" ]]; then
    python3 - <<'PY' >"$output"
print("## Plan")
print("replacement after long line")
print("diff_lines: 1")
PY
elif [[ -f "${RESPONSE_DIR:?}/${tool}.txt" ]]; then
    cp "${RESPONSE_DIR:?}/${tool}.txt" "$output"
else
    : >"$output"
fi
if [[ "$output" == *"/claude-output.txt" ]]; then
    : >"${DESIGN_TMPDIR:?}/.tier4"
fi
EOF
chmod +x "$C8D/launch-review.sh"
python3 - <<'PY' >"$C8D/responses/codex.txt"
line_a = "A" * 5000
line_b = "B" * 5000
print("--- a/plan.txt")
print("+++ b/plan.txt")
print("@@ -1,4 +1,4 @@")
print(" ## Plan")
print("-" + line_a)
print("+" + ("A" * 4999) + "!")
print("")
print("@@ -2,2 +2,2 @@")
print("-" + line_b)
print("+" + ("B" * 4999) + "!")
print(" diff_lines: 2")
PY
cp "$C8D/responses/codex.txt" "$C8D/responses/cursor.txt"
cp "$C8D/responses/codex.txt" "$C8D/responses/claude.txt"
out8d=$(DESIGN_TMPDIR="$C8D" run_case "$C8D")
assert_kv "$out8d" REVISE_STATUS ok-fallback
assert_kv "$out8d" REVISE_TIER_4_STATUS ok
grep -q '^replacement after long line$' "$C8D/plan.txt" || fail "case8d should survive the long-line corrupt patch path"

echo "=== tier-4 fallback can skip codex and let cursor win ==="
C8E="$TMP/case8e"
setup_case "$C8E"
cp "$COMMON/launch-claude-review.sh" "$C8E/launch-claude-review.sh"
cp "$COMMON/design-driver.sh" "$C8E/design-driver.sh"
mkdir -p "$C8E/responses"
cat >"$C8E/launch-review.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
tool="${LARCH_TOOL_OVERRIDE:-}"
output=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tool) tool="${2:?}"; shift 2 ;;
        --output) output="${2:?}"; shift 2 ;;
        *) shift ;;
    esac
done
[[ -n "$tool" && -n "$output" ]] || exit 2
if [[ -f "${DESIGN_TMPDIR:?}/.tier4" ]]; then
    if [[ "$output" == *"/cursor-output.txt" ]]; then
        cat >"$output" <<'INNER'
## Plan
cursor tier4
diff_lines: 1
INNER
    else
        : >"$output"
    fi
elif [[ -f "${RESPONSE_DIR:?}/${tool}.txt" ]]; then
    cp "${RESPONSE_DIR:?}/${tool}.txt" "$output"
else
    : >"$output"
fi
if [[ "$output" == *"/claude-output.txt" ]]; then
    : >"${DESIGN_TMPDIR:?}/.tier4"
fi
EOF
chmod +x "$C8E/launch-review.sh"
cat >"$C8E/responses/codex.txt" <<'EOF'
--- a/notes.txt
+++ b/notes.txt
@@ -1 +1 @@
-bad
+still bad
EOF
cp "$C8E/responses/codex.txt" "$C8E/responses/cursor.txt"
cp "$C8E/responses/codex.txt" "$C8E/responses/claude.txt"
out8e=$(DESIGN_TMPDIR="$C8E" run_case "$C8E")
assert_kv "$out8e" REVISE_STATUS ok-fallback
assert_kv "$out8e" REVISE_TIER_1_STATUS invalid-patch
assert_kv "$out8e" REVISE_TIER_2_STATUS invalid-patch
assert_kv "$out8e" REVISE_TIER_3_STATUS invalid-patch
assert_kv "$out8e" REVISE_TIER_4_STATUS ok
assert_kv "$out8e" REVISE_WINNING_TIER cursor
grep -q '^cursor tier4$' "$C8E/plan.txt" || fail "case8e should allow cursor to win inside tier-4 fallback"

echo "=== tier-4 fallback can skip codex and cursor and let claude win ==="
C8F="$TMP/case8f"
setup_case "$C8F"
cp "$COMMON/launch-claude-review.sh" "$C8F/launch-claude-review.sh"
cp "$COMMON/design-driver.sh" "$C8F/design-driver.sh"
mkdir -p "$C8F/responses"
cat >"$C8F/launch-review.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
tool="${LARCH_TOOL_OVERRIDE:-}"
output=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tool) tool="${2:?}"; shift 2 ;;
        --output) output="${2:?}"; shift 2 ;;
        *) shift ;;
    esac
done
[[ -n "$tool" && -n "$output" ]] || exit 2
if [[ -f "${DESIGN_TMPDIR:?}/.tier4" ]]; then
    : >"$output"
elif [[ -f "${RESPONSE_DIR:?}/${tool}.txt" ]]; then
    cp "${RESPONSE_DIR:?}/${tool}.txt" "$output"
else
    : >"$output"
fi
if [[ "$output" == *"/claude-output.txt" && -f "${DESIGN_TMPDIR:?}/.tier4" ]]; then
    cat >"$output" <<'INNER'
## Plan
claude tier4
diff_lines: 1
INNER
fi
if [[ "$output" == *"/claude-output.txt" ]]; then
    : >"${DESIGN_TMPDIR:?}/.tier4"
fi
EOF
chmod +x "$C8F/launch-review.sh"
cat >"$C8F/responses/codex.txt" <<'EOF'
--- a/notes.txt
+++ b/notes.txt
@@ -1 +1 @@
-bad
+still bad
EOF
cp "$C8F/responses/codex.txt" "$C8F/responses/cursor.txt"
cp "$C8F/responses/codex.txt" "$C8F/responses/claude.txt"
out8f=$(DESIGN_TMPDIR="$C8F" run_case "$C8F")
assert_kv "$out8f" REVISE_STATUS ok-fallback
assert_kv "$out8f" REVISE_TIER_1_STATUS invalid-patch
assert_kv "$out8f" REVISE_TIER_2_STATUS invalid-patch
assert_kv "$out8f" REVISE_TIER_3_STATUS invalid-patch
assert_kv "$out8f" REVISE_TIER_4_STATUS ok
assert_kv "$out8f" REVISE_WINNING_TIER claude
grep -q '^claude tier4$' "$C8F/plan.txt" || fail "case8f should allow claude to win inside tier-4 fallback"

echo "=== codex absence is reported and cursor can still win ==="
C9="$TMP/case9"
setup_case "$C9"
cp "$COMMON/launch-review.sh" "$C9/launch-review.sh"
cp "$COMMON/launch-claude-review.sh" "$C9/launch-claude-review.sh"
cp "$COMMON/design-driver.sh" "$C9/design-driver.sh"
mkdir -p "$C9/responses"
cat >"$C9/responses/cursor.txt" <<'EOF'
```diff
--- a/plan.txt
+++ b/plan.txt
@@ -1,3 +1,3 @@
 ## Plan
-alpha
+cursor only
 diff_lines: 1
```
EOF
out9=$(run_case "$C9" --codex-present false)
assert_kv "$out9" REVISE_TIER_1_STATUS skipped-not-present
assert_kv "$out9" REVISE_TIER_2_STATUS ok
assert_kv "$out9" REVISE_STATUS ok
assert_kv "$out9" REVISE_TIER_4_STATUS not-attempted
grep -q '^cursor only$' "$C9/plan.txt" || fail "case9 should allow cursor to win when codex is absent"

echo "=== claude tier can win when codex and cursor are unavailable ==="
C10="$TMP/case10"
setup_case "$C10"
cp "$COMMON/launch-review.sh" "$C10/launch-review.sh"
cp "$COMMON/launch-claude-review.sh" "$C10/launch-claude-review.sh"
cp "$COMMON/design-driver.sh" "$C10/design-driver.sh"
mkdir -p "$C10/responses"
cat >"$C10/responses/claude.txt" <<'EOF'
```diff
--- a/plan.txt
+++ b/plan.txt
@@ -1,3 +1,3 @@
 ## Plan
-alpha
+claude win
 diff_lines: 1
```
EOF
out10=$(run_case "$C10" --codex-present false --cursor-present false)
assert_kv "$out10" REVISE_TIER_1_STATUS skipped-not-present
assert_kv "$out10" REVISE_TIER_2_STATUS skipped-not-present
assert_kv "$out10" REVISE_TIER_3_STATUS ok
assert_kv "$out10" REVISE_STATUS ok
assert_kv "$out10" REVISE_TIER_4_STATUS not-attempted
grep -q '^claude win$' "$C10/plan.txt" || fail "case10 should allow the Claude tier to win"

echo "=== file replacement mode can succeed on codex, cursor, and claude tiers ==="
C10B="$TMP/case10b"
setup_case "$C10B"
cp "$COMMON/launch-review.sh" "$C10B/launch-review.sh"
cp "$COMMON/launch-claude-review.sh" "$C10B/launch-claude-review.sh"
cp "$COMMON/design-driver.sh" "$C10B/design-driver.sh"
mkdir -p "$C10B/responses"
cat >"$C10B/responses/codex.txt" <<'EOF'
## Plan
file replacement codex
diff_lines: 1
EOF
out10b=$(run_case "$C10B" --patch-format file-replacement)
assert_kv "$out10b" REVISE_STATUS ok
assert_kv "$out10b" REVISE_TIER_1_STATUS ok
assert_kv "$out10b" REVISE_TIER_4_STATUS not-attempted
grep -q '^file replacement codex$' "$C10B/plan.txt" || fail "case10b should allow codex to win in file-replacement mode"

C10C="$TMP/case10c"
setup_case "$C10C"
cp "$COMMON/launch-review.sh" "$C10C/launch-review.sh"
cp "$COMMON/launch-claude-review.sh" "$C10C/launch-claude-review.sh"
cp "$COMMON/design-driver.sh" "$C10C/design-driver.sh"
mkdir -p "$C10C/responses"
printf '\n' >"$C10C/responses/codex.txt"
cat >"$C10C/responses/cursor.txt" <<'EOF'
## Plan
file replacement cursor
diff_lines: 1
EOF
out10c=$(run_case "$C10C" --patch-format file-replacement)
assert_kv "$out10c" REVISE_STATUS ok
assert_kv "$out10c" REVISE_TIER_1_STATUS no-patch
assert_kv "$out10c" REVISE_TIER_2_STATUS ok
assert_kv "$out10c" REVISE_TIER_4_STATUS not-attempted
grep -q '^file replacement cursor$' "$C10C/plan.txt" || fail "case10c should allow cursor to win in file-replacement mode"

C10D="$TMP/case10d"
setup_case "$C10D"
cp "$COMMON/launch-review.sh" "$C10D/launch-review.sh"
cp "$COMMON/launch-claude-review.sh" "$C10D/launch-claude-review.sh"
cp "$COMMON/design-driver.sh" "$C10D/design-driver.sh"
mkdir -p "$C10D/responses"
printf '\n' >"$C10D/responses/codex.txt"
printf '\n' >"$C10D/responses/cursor.txt"
cat >"$C10D/responses/claude.txt" <<'EOF'
## Plan
file replacement claude
diff_lines: 1
EOF
out10d=$(run_case "$C10D" --patch-format file-replacement)
assert_kv "$out10d" REVISE_STATUS ok
assert_kv "$out10d" REVISE_TIER_1_STATUS no-patch
assert_kv "$out10d" REVISE_TIER_2_STATUS no-patch
assert_kv "$out10d" REVISE_TIER_3_STATUS ok
assert_kv "$out10d" REVISE_TIER_4_STATUS not-attempted
grep -q '^file replacement claude$' "$C10D/plan.txt" || fail "case10d should allow claude to win in file-replacement mode"

echo "=== tier-4 status preserves the worst non-ok failure and revise.env matches stdout ==="
C11="$TMP/case11"
setup_case "$C11"
cp "$COMMON/launch-claude-review.sh" "$C11/launch-claude-review.sh"
mkdir -p "$C11/responses"
cat >"$C11/design-driver.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [[ -f "${DESIGN_TMPDIR:?}/.force-emit-fail" ]]; then
    rm -f "${DESIGN_TMPDIR:?}/.force-emit-fail"
    printf '%s\n' 'EMIT_PLAN_STATUS=fail'
else
    printf '%s\n' 'EMIT_PLAN_STATUS=ok'
fi
EOF
chmod +x "$C11/design-driver.sh"
cat >"$C11/launch-review.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
tool="${LARCH_TOOL_OVERRIDE:-}"
output=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tool) tool="${2:?}"; shift 2 ;;
        --output) output="${2:?}"; shift 2 ;;
        *) shift ;;
    esac
done
[[ -n "$tool" && -n "$output" ]] || exit 2
if [[ "$output" == *"/codex-output.txt" && -f "${DESIGN_TMPDIR:?}/.tier4" ]]; then
    cat >"$output" <<'INNER'
## Plan
diff_lines:	1
INNER
elif [[ "$output" == *"/cursor-output.txt" && -f "${DESIGN_TMPDIR:?}/.tier4" ]]; then
    : >"${DESIGN_TMPDIR:?}/.force-emit-fail"
    cat >"$output" <<'INNER'
## Plan
cursor fallback
diff_lines: 1
INNER
elif [[ -f "${RESPONSE_DIR:?}/${tool}.txt" ]]; then
    cp "${RESPONSE_DIR:?}/${tool}.txt" "$output"
else
    : >"$output"
fi
if [[ "$output" == *"/claude-output.txt" ]]; then
    : >"${DESIGN_TMPDIR:?}/.tier4"
fi
EOF
chmod +x "$C11/launch-review.sh"
printf '\n' >"$C11/responses/codex.txt"
printf '\n' >"$C11/responses/cursor.txt"
printf '\n' >"$C11/responses/claude.txt"
out11=$(DESIGN_TMPDIR="$C11" run_case "$C11")
assert_kv "$out11" REVISE_STATUS failed-validation
assert_kv "$out11" REVISE_TIER_4_STATUS invalid-patch
assert_file_kv "$C11/plan-review/round-1/revise/revise.env" REVISE_STATUS failed-validation
assert_file_kv "$C11/plan-review/round-1/revise/revise.env" REVISE_TIER_4_STATUS invalid-patch
assert_file_kv "$C11/plan-review/round-1/revise/revise.env" REVISE_WINNING_TIER ''
assert_file_kv "$C11/plan-review/round-1/revise/revise.env" REVISE_PATCH_PATH ''

before_hash=$(grep '^REVISE_PLAN_HASH_BEFORE=' "$C11/plan-review/round-1/revise/revise.env" | cut -d= -f2-)
after_hash=$(grep '^REVISE_PLAN_HASH_AFTER=' "$C11/plan-review/round-1/revise/revise.env" | cut -d= -f2-)
[[ "$before_hash" == "$after_hash" ]] || fail "failed revision should preserve the plan hash"
grep -q '^alpha$' "$C11/plan.txt" || fail "case11 should restore the original plan"
[[ -f "$C11/plan.txt.before-revise" ]] || fail "case11 should preserve the rollback snapshot"

echo "=== revise.env persists success metadata for ok-fallback winners ==="
C11B="$TMP/case11b"
setup_case "$C11B"
cp "$C3/launch-review.sh" "$C11B/launch-review.sh"
cp "$COMMON/launch-claude-review.sh" "$C11B/launch-claude-review.sh"
cp "$COMMON/design-driver.sh" "$C11B/design-driver.sh"
mkdir -p "$C11B/responses"
cat >"$C11B/responses/codex.txt" <<'EOF'
--- a/notes.txt
+++ b/notes.txt
@@ -1 +1 @@
-bad
+still bad
EOF
cp "$C11B/responses/codex.txt" "$C11B/responses/cursor.txt"
cp "$C11B/responses/codex.txt" "$C11B/responses/claude.txt"
cat >"$C11B/responses/codex-fallback.txt" <<'EOF'
## Plan
persist fallback
diff_lines: 1
EOF
out11b=$(DESIGN_TMPDIR="$C11B" run_case "$C11B")
assert_kv "$out11b" REVISE_STATUS ok-fallback
assert_file_kv "$C11B/plan-review/round-1/revise/revise.env" REVISE_STATUS ok-fallback
assert_file_kv "$C11B/plan-review/round-1/revise/revise.env" REVISE_TIER_4_STATUS ok
assert_file_kv "$C11B/plan-review/round-1/revise/revise.env" REVISE_WINNING_TIER codex
assert_file_kv_suffix "$C11B/plan-review/round-1/revise/revise.env" REVISE_PATCH_PATH "/plan-review/round-1/revise/codex-output.txt"
[[ ! -f "$C11B/plan.txt.before-revise" ]] || fail "successful fallback should remove the rollback snapshot"

echo "=== emit-plan rollback does not leave a false ok status behind ==="
C11C="$TMP/case11c"
setup_case "$C11C"
cp "$COMMON/launch-review.sh" "$C11C/launch-review.sh"
cp "$COMMON/launch-claude-review.sh" "$C11C/launch-claude-review.sh"
mkdir -p "$C11C/responses"
cat >"$C11C/design-driver.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' 'EMIT_PLAN_STATUS=fail'
EOF
chmod +x "$C11C/design-driver.sh"
cat >"$C11C/responses/codex.txt" <<'EOF'
```diff
--- a/plan.txt
+++ b/plan.txt
@@ -1,3 +1,3 @@
 ## Plan
-alpha
+never persists
 diff_lines: 1
```
EOF
cat >"$C11C/responses/cursor.txt" <<'EOF'
no diff here
EOF
cat >"$C11C/responses/claude.txt" <<'EOF'
no diff here
EOF
out11c=$(run_case "$C11C")
assert_kv "$out11c" REVISE_STATUS failed-apply
assert_kv "$out11c" REVISE_TIER_1_STATUS emit-plan-failed
assert_kv "$out11c" REVISE_TIER_2_STATUS no-patch
assert_kv "$out11c" REVISE_TIER_3_STATUS no-patch
assert_kv "$out11c" REVISE_TIER_4_STATUS no-patch
grep -q '^alpha$' "$C11C/plan.txt" || fail "case11c should roll back the failed winner"

echo "=== unified-diff rejects candidate that drops optional size trailers ==="
C12="$TMP/case12-trailers"
setup_case "$C12"
cp "$COMMON/launch-review.sh" "$C12/launch-review.sh"
cp "$COMMON/launch-claude-review.sh" "$C12/launch-claude-review.sh"
cp "$COMMON/design-driver.sh" "$C12/design-driver.sh"
mkdir -p "$C12/responses"
cat >"$C12/plan.txt" <<'EOF'
## Plan
alpha
diff_added: 100
diff_deleted: 50
mechanical_churn: true
diff_lines: 150
EOF
cat >"$C12/responses/codex.txt" <<'EOF'
--- a/plan.txt
+++ b/plan.txt
@@ -1,6 +1,3 @@
 ## Plan
 alpha
-diff_added: 100
-diff_deleted: 50
-mechanical_churn: true
 diff_lines: 150
EOF
cat >"$C12/responses/cursor.txt" <<'EOF'
--- a/plan.txt
+++ b/plan.txt
@@ -1,6 +1,6 @@
 ## Plan
-alpha
+beta
 diff_added: 100
 diff_deleted: 50
 mechanical_churn: true
 diff_lines: 150
EOF
printf '\n' >"$C12/responses/claude.txt"
out12=$(run_case "$C12")
assert_kv "$out12" REVISE_STATUS ok
assert_kv "$out12" REVISE_TIER_1_STATUS invalid-patch
assert_kv "$out12" REVISE_TIER_2_STATUS ok
grep -q '^diff_added: 100$' "$C12/plan.txt" || fail "case12 should preserve diff_added trailer"
grep -q '^mechanical_churn: true$' "$C12/plan.txt" || fail "case12 should preserve mechanical_churn trailer"
grep -q '^diff_lines: 150$' "$C12/plan.txt" || fail "case12 should preserve diff_lines trailer"

echo "=== file-replacement preserves optional size trailers ==="
C13="$TMP/case13-trailers-fr"
setup_case "$C13"
cp "$COMMON/launch-review.sh" "$C13/launch-review.sh"
cp "$COMMON/launch-claude-review.sh" "$C13/launch-claude-review.sh"
cp "$COMMON/design-driver.sh" "$C13/design-driver.sh"
mkdir -p "$C13/responses"
cat >"$C13/plan.txt" <<'EOF'
## Plan
alpha
diff_added: 200
diff_deleted: 10
mechanical_churn: false
diff_lines: 210
EOF
cat >"$C13/responses/codex.txt" <<'EOF'
## Plan
revised body
diff_added: 200
diff_deleted: 10
mechanical_churn: false
diff_lines: 210
EOF
printf '\n' >"$C13/responses/cursor.txt"
printf '\n' >"$C13/responses/claude.txt"
out13=$(run_case "$C13" --patch-format file-replacement)
assert_kv "$out13" REVISE_STATUS ok
grep -q '^diff_added: 200$' "$C13/plan.txt" || fail "case13 file-replacement should preserve diff_added"
grep -q '^mechanical_churn: false$' "$C13/plan.txt" || fail "case13 file-replacement should preserve mechanical_churn"

printf '%s\n' 'test-revise-plan-with-waterfall: ok'
