#!/usr/bin/env bash
# test-show-skill.sh — regression harness for skills/show-skill/scripts/show.sh.
#
# Black-box contract test. Covers: bare name resolution, larch:/prefix stripping,
# path-traversal rejection, and STATUS=not-found on missing skills.
#
# Usage:
#   bash skills/show-skill/scripts/test-show-skill.sh
#
# Exit codes:
#   0 — all assertions passed
#   1 — at least one assertion failed
set -euo pipefail

SHOW="${BASH_SOURCE[0]%/*}/show.sh"
PASS=0; FAIL=0

check() {
  local desc="$1" expected_status="$2" expected_path_contains="${3:-}" expected_content="${4:-}"
  local out
  out=$(bash "$SHOW" "${@:5}" 2>/dev/null) || true
  # STATUS= and SKILL_PATH= are the leading KV protocol lines on stdout.
  local status path
  status=$(printf '%s\n' "$out" | awk -F= '/^STATUS=/{print $2; exit}')
  path=$(printf '%s\n' "$out" | awk -F= '/^SKILL_PATH=/{print $2; exit}')
  # body is stdout minus the leading KV protocol lines (the SKILL.md content).
  local body
  body=$(printf '%s\n' "$out" | grep -Ev '^STATUS=|^SKILL_PATH=') || true
  if [[ "$status" != "$expected_status" ]]; then
    echo "FAIL [$desc]: expected STATUS=$expected_status, got STATUS=$status"
    FAIL=$((FAIL+1)); return
  fi
  if [[ -n "$expected_path_contains" ]]; then
    if [[ "$path" != *"$expected_path_contains"* ]]; then
      echo "FAIL [$desc]: SKILL_PATH='$path' does not contain '$expected_path_contains'"
      FAIL=$((FAIL+1)); return
    fi
  fi
  if [[ -n "$expected_content" ]]; then
    if [[ "$body" != *"$expected_content"* ]]; then
      echo "FAIL [$desc]: output does not contain '$expected_content'"
      FAIL=$((FAIL+1)); return
    fi
  fi
  if [[ -z "$expected_content" && -n "$body" ]]; then
    echo "FAIL [$desc]: expected empty output, got '$body'"
    FAIL=$((FAIL+1)); return
  fi
  echo "PASS [$desc]"
  PASS=$((PASS+1))
}

# Bare name that exists in plugin skills/
check "bare name found" found "show-skill/SKILL.md" "name: show-skill" show-skill

# larch: prefix stripped
check "larch: prefix" found "show-skill/SKILL.md" "name: show-skill" larch:show-skill

# leading / stripped
check "leading / stripped" found "show-skill/SKILL.md" "name: show-skill" /show-skill

# Non-existent skill
check "not-found" not-found "" "" nonexistent-skill-xyz-abc

# Empty argument
check "empty argument" not-found "" "" ""

# Path traversal rejected
check "dotdot rejected" not-found "" "" "../etc/passwd"
check "slash rejected" not-found "" "" "foo/bar"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
