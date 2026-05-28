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

assert_kv_suffix() {
    local haystack="$1" key="$2" suffix="$3"
    printf '%s\n' "$haystack" | grep -q "^${key}=.*${suffix}\$" || fail "expected ${key} suffix ${suffix}"
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

COMMON="$TMP/common"
mkdir -p "$COMMON/responses"
write_launcher_stub "$COMMON/launch-review.sh"
write_claude_stub "$COMMON/launch-claude-review.sh"
write_design_driver_stub "$COMMON/design-driver.sh"

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

echo "=== extract_patch failure downgrades to no-patch and continues ==="
C5="$TMP/case5"
setup_case "$C5"
cp "$COMMON/launch-review.sh" "$C5/launch-review.sh"
cp "$COMMON/launch-claude-review.sh" "$C5/launch-claude-review.sh"
cp "$COMMON/design-driver.sh" "$C5/design-driver.sh"
mkdir -p "$C5/responses" "$C5/path-bin"
REAL_PYTHON="$(command -v python3)"
cat >"$C5/responses/codex.txt" <<'EOF'
```diff
--- a/plan.txt
+++ b/plan.txt
@@ -1,3 +1,3 @@
 ## Plan
-alpha
+ignored
 diff_lines: 1
```
EOF
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
cat >"$C5/path-bin/python3" <<EOF
#!/usr/bin/env bash
set -euo pipefail
state="$C5/python.fail.count"
count=0
if [[ -f "\$state" ]]; then
    count=\$(cat "\$state")
fi
count=\$((count + 1))
printf '%s\n' "\$count" >"\$state"
if [[ "\$count" -eq 1 ]]; then
    exit 99
fi
exec "$REAL_PYTHON" "\$@"
EOF
chmod +x "$C5/path-bin/python3"
out5=$(PATH="$C5/path-bin:$PATH" run_case "$C5")
assert_kv "$out5" REVISE_STATUS ok
assert_kv "$out5" REVISE_TIER_1_STATUS no-patch
assert_kv "$out5" REVISE_TIER_2_STATUS ok
assert_kv "$out5" REVISE_TIER_4_STATUS not-attempted
grep -q '^cursor win$' "$C5/plan.txt" || fail "case5 should continue after extract failure"

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

printf '%s\n' 'test-revise-plan-with-waterfall: ok'
