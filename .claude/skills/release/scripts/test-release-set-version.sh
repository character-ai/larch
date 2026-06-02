#!/usr/bin/env bash
# test-release-set-version.sh — Offline harness for release-set-version.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUBJECT="$SCRIPT_DIR/release-set-version.sh"

PASS=0
FAIL=0
TMPDIR_BASE=$(mktemp -d)
trap 'rm -rf "$TMPDIR_BASE"' EXIT

ok() { PASS=$((PASS + 1)); }
fail() { echo "FAIL: $*" >&2; FAIL=$((FAIL + 1)); }

setup_repo() {
  local repo=$1 version=$2
  mkdir -p "$repo/.claude-plugin"
  cat > "$repo/.claude-plugin/plugin.json" <<JSON
{
  "name": "larch",
  "version": "$version",
  "description": "test"
}
JSON
}

# Test 1: writes version, preserves other keys
repo="$TMPDIR_BASE/t1"
setup_repo "$repo" "1.0.0"
out=$(cd "$repo" && bash "$SUBJECT" 1.1.0 2>/dev/null)
ver=$(jq -r .version "$repo/.claude-plugin/plugin.json")
name=$(jq -r .name "$repo/.claude-plugin/plugin.json")
if printf '%s\n' "$out" | grep -q '^NEW_VERSION=1.1.0$' \
  && [[ "$ver" == "1.1.0" ]] && [[ "$name" == "larch" ]]; then
  ok
else
  fail "version write: ver=$ver out=$out"
fi

# Test 2: trailing newline preserved (file ends with newline)
if [[ -n "$(tail -c 1 "$repo/.claude-plugin/plugin.json")" ]]; then
  fail "plugin.json missing trailing newline"
else
  ok
fi

# Test 3: invalid semver rejected, file unchanged
repo="$TMPDIR_BASE/t3"
setup_repo "$repo" "1.0.0"
cp "$repo/.claude-plugin/plugin.json" "$repo/.claude-plugin/plugin.json.bak"
set +e
(cd "$repo" && bash "$SUBJECT" "not-semver" >/dev/null 2>&1)
rc=$?
set -e
if [[ $rc -ne 0 ]] && cmp -s "$repo/.claude-plugin/plugin.json" "$repo/.claude-plugin/plugin.json.bak"; then
  ok
else
  fail "invalid semver should refuse (rc=$rc)"
fi

# Test 4: downgrade refused
repo="$TMPDIR_BASE/t4"
setup_repo "$repo" "2.0.0"
set +e
(cd "$repo" && bash "$SUBJECT" 1.9.9 >/dev/null 2>&1)
rc=$?
set -e
ver=$(jq -r .version "$repo/.claude-plugin/plugin.json")
if [[ $rc -ne 0 && "$ver" == "2.0.0" ]]; then
  ok
else
  fail "downgrade should refuse: rc=$rc ver=$ver"
fi

# Test 5: no-op refused
repo="$TMPDIR_BASE/t5"
setup_repo "$repo" "1.2.3"
set +e
(cd "$repo" && bash "$SUBJECT" 1.2.3 >/dev/null 2>&1)
rc=$?
set -e
if [[ $rc -ne 0 ]]; then
  ok
else
  fail "no-op should refuse"
fi

total=$((PASS + FAIL))
echo "test-release-set-version: $PASS/$total passed"
[[ "$FAIL" -eq 0 ]] || exit 1
