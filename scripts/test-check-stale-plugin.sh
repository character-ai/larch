#!/usr/bin/env bash
# test-check-stale-plugin.sh — regression harness for check-stale-plugin.sh

unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SCRIPT="$REPO_ROOT/scripts/check-stale-plugin.sh"

[ -x "$SCRIPT" ] || { echo "FAIL: $SCRIPT not executable"; exit 1; }

PASS=0
FAIL=0
SANDBOX=$(mktemp -d /tmp/larch-stale-plugin-test.XXXXXX)
trap 'rm -rf "$SANDBOX"' EXIT

assert_rc() {
    local actual=$1 expected=$2 label=$3
    if [ "$actual" -eq "$expected" ]; then
        PASS=$((PASS + 1))
        echo "PASS: $label"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: $label (expected rc=$expected got rc=$actual)"
    fi
}

assert_kv() {
    local key=$1 expected=$2 haystack=$3 label=$4
    local actual
    actual=$(printf '%s\n' "$haystack" | awk -F= "/^${key}=/ { v=\$2 } END { print v }")
    if [ "$actual" = "$expected" ]; then
        PASS=$((PASS + 1))
        echo "PASS: $label"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: $label (key=$key expected=$expected got=$actual)"
        printf '%s\n' "$haystack" | sed 's/^/    /'
    fi
}

make_plugin_json() {
    local dir=$1 version=$2
    mkdir -p "$dir"
    printf '{"name":"larch","version":"%s"}\n' "$version" > "$dir/plugin.json"
}

make_larch_clone() {
    local root=$1
    mkdir -p "$root/skills/implement"
    touch "$root/skills/implement/SKILL.md"
    mkdir -p "$root/.claude-plugin"
}

run_check() {
    local installed_json=$1 wt_root=$2
    set +e
    OUT=$("$SCRIPT" --installed-plugin-json "$installed_json" --working-tree-root "$wt_root" 2>&1)
    RC=$?
    set -e
}

run_check_default_env() {
    local root=$1
    set +e
    OUT=$(env -u CLAUDE_PLUGIN_ROOT "$SCRIPT" --working-tree-root "$root" 2>&1)
    RC=$?
    set -e
}

# --- Case 1: working-tree ahead → working-tree-ahead ---
dir1="$SANDBOX/case1"
mkdir -p "$dir1/installed" "$dir1/wt"
make_larch_clone "$dir1/wt"
make_plugin_json "$dir1/installed" "29.8.33"
make_plugin_json "$dir1/wt/.claude-plugin" "29.8.39"
run_check "$dir1/installed/plugin.json" "$dir1/wt"
assert_rc "$RC" 0 "case1: exits 0 when working-tree ahead"
assert_kv "STALE_PLUGIN_CHECK" "working-tree-ahead" "$OUT" "case1: check=working-tree-ahead"
assert_kv "STALE_PLUGIN_INSTALLED_VERSION" "29.8.33" "$OUT" "case1: installed version"
assert_kv "STALE_PLUGIN_WORKING_TREE_VERSION" "29.8.39" "$OUT" "case1: working-tree version"

# --- Case 2: versions match → versions-match ---
dir2="$SANDBOX/case2"
mkdir -p "$dir2/installed" "$dir2/wt"
make_larch_clone "$dir2/wt"
make_plugin_json "$dir2/installed" "29.8.39"
make_plugin_json "$dir2/wt/.claude-plugin" "29.8.39"
run_check "$dir2/installed/plugin.json" "$dir2/wt"
assert_rc "$RC" 0 "case2: exits 0 when versions match"
assert_kv "STALE_PLUGIN_CHECK" "versions-match" "$OUT" "case2: check=versions-match"

# --- Case 3: not a dev clone (no skills/implement/SKILL.md) → not-a-dev-clone ---
dir3="$SANDBOX/case3"
mkdir -p "$dir3/installed" "$dir3/wt/.claude-plugin"
make_plugin_json "$dir3/installed" "29.8.33"
make_plugin_json "$dir3/wt/.claude-plugin" "29.8.39"
# No skills/implement/SKILL.md in wt
run_check "$dir3/installed/plugin.json" "$dir3/wt"
assert_rc "$RC" 0 "case3: exits 0 when not dev clone"
assert_kv "STALE_PLUGIN_CHECK" "not-a-dev-clone" "$OUT" "case3: check=not-a-dev-clone"

# --- Case 4: installed ahead → installed-ahead, no warning keys ---
dir4="$SANDBOX/case4"
mkdir -p "$dir4/installed" "$dir4/wt"
make_larch_clone "$dir4/wt"
make_plugin_json "$dir4/installed" "29.8.40"
make_plugin_json "$dir4/wt/.claude-plugin" "29.8.39"
run_check "$dir4/installed/plugin.json" "$dir4/wt"
assert_rc "$RC" 0 "case4: exits 0 when installed ahead"
assert_kv "STALE_PLUGIN_CHECK" "installed-ahead" "$OUT" "case4: check=installed-ahead"

# --- Case 5: missing installed plugin.json → skip ---
dir5="$SANDBOX/case5"
mkdir -p "$dir5/wt"
make_larch_clone "$dir5/wt"
make_plugin_json "$dir5/wt/.claude-plugin" "29.8.39"
# No installed plugin.json
run_check "$dir5/installed-nonexistent/plugin.json" "$dir5/wt"
assert_rc "$RC" 0 "case5: exits 0 when installed plugin.json missing"
assert_kv "STALE_PLUGIN_CHECK" "skip" "$OUT" "case5: check=skip on missing installed"

# --- Case 6: major version difference ---
dir6="$SANDBOX/case6"
mkdir -p "$dir6/installed" "$dir6/wt"
make_larch_clone "$dir6/wt"
make_plugin_json "$dir6/installed" "28.9.99"
make_plugin_json "$dir6/wt/.claude-plugin" "29.0.0"
run_check "$dir6/installed/plugin.json" "$dir6/wt"
assert_rc "$RC" 0 "case6: exits 0 on major version difference"
assert_kv "STALE_PLUGIN_CHECK" "working-tree-ahead" "$OUT" "case6: check=working-tree-ahead (major)"

# --- Case 7: missing version field in installed plugin.json → skip ---
dir7="$SANDBOX/case7"
mkdir -p "$dir7/installed" "$dir7/wt"
make_larch_clone "$dir7/wt"
printf '{"name":"larch"}\n' > "$dir7/installed/plugin.json"
make_plugin_json "$dir7/wt/.claude-plugin" "29.8.39"
run_check "$dir7/installed/plugin.json" "$dir7/wt"
assert_rc "$RC" 0 "case7: exits 0 when installed plugin.json has no version"
assert_kv "STALE_PLUGIN_CHECK" "skip" "$OUT" "case7: check=skip on missing installed version"

# --- Case 8: working-tree plugin.json missing → skip ---
dir8="$SANDBOX/case8"
mkdir -p "$dir8/installed" "$dir8/wt"
make_larch_clone "$dir8/wt"
make_plugin_json "$dir8/installed" "29.8.39"
run_check "$dir8/installed/plugin.json" "$dir8/wt"
assert_rc "$RC" 0 "case8: exits 0 when working-tree plugin.json is missing"
assert_kv "STALE_PLUGIN_CHECK" "skip" "$OUT" "case8: check=skip on missing working-tree plugin.json"

# --- Case 9: CLAUDE_PLUGIN_ROOT unset on default path → skip ---
dir9="$SANDBOX/case9"
mkdir -p "$dir9/wt"
make_larch_clone "$dir9/wt"
make_plugin_json "$dir9/wt/.claude-plugin" "29.8.39"
run_check_default_env "$dir9/wt"
assert_rc "$RC" 0 "case9: exits 0 when CLAUDE_PLUGIN_ROOT is unset"
assert_kv "STALE_PLUGIN_CHECK" "skip" "$OUT" "case9: check=skip when CLAUDE_PLUGIN_ROOT is unset"

# --- Case 10: invalid working-tree root → skip ---
dir10="$SANDBOX/case10"
mkdir -p "$dir10/installed"
make_plugin_json "$dir10/installed" "29.8.39"
run_check "$dir10/installed/plugin.json" "$dir10/does-not-exist"
assert_rc "$RC" 0 "case10: exits 0 when working-tree root is invalid"
assert_kv "STALE_PLUGIN_CHECK" "skip" "$OUT" "case10: check=skip on invalid working-tree root"

echo
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
