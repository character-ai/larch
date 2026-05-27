#!/usr/bin/env bash
# Regression harness for scripts/lib-design-reentry-guard.sh.
# shellcheck disable=SC2016 # Fixture bodies are single-quoted for evaluation inside a temporary HOME shell.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SUBJECT="$ROOT/scripts/lib-design-reentry-guard.sh"

fail() {
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

pass() {
    printf 'PASS: %s\n' "$1"
}

capture_fixture() {
    local name="$1"
    local out="$2"
    local rc_file="$3"
    local script="$4"
    local home_dir rc
    home_dir=$(mktemp -d "${TMPDIR:-/tmp}/tdrg.${name}.XXXXXX")
    set +e
    HOME="$home_dir" bash -c '
        set -euo pipefail
        source "$1"
        eval "$2"
    ' sh "$SUBJECT" "$script" >"$out" 2>"$out.err"
    rc=$?
    set -e
    printf '%s\n' "$rc" >"$rc_file"
    printf '%s\n' "$home_dir" >"$out.home"
}

TMP=$(mktemp -d "${TMPDIR:-/tmp}/tdrg-main.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

# F1: no marker.
out="$TMP/f1.out"; rc="$TMP/f1.rc"
capture_fixture f1 "$out" "$rc" 'design_reentry_marker_hit 2935 111'
[ "$(cat "$rc")" = "1" ] || fail "F1 expected rc=1"
grep -Fq 'MARKER_HIT=false REASON=absent' "$out" || fail "F1 expected absent"
rm -rf "$(cat "$out.home")"
pass "F1 absent marker"

# F2: same issue + same PPID fresh marker hits.
out="$TMP/f2.out"; rc="$TMP/f2.rc"
capture_fixture f2 "$out" "$rc" '
  design_reentry_marker_write 2935 111
  design_reentry_marker_hit 2935 111
'
[ "$(cat "$rc")" = "0" ] || fail "F2 expected rc=0"
grep -Fq 'MARKER_HIT=true' "$out" || fail "F2 expected hit"
grep -Fq 'MARKER_TTL=300' "$out" || fail "F2 expected default ttl"
rm -rf "$(cat "$out.home")"
pass "F2 fresh marker hit"

# F3: stale marker misses and is cleaned up.
out="$TMP/f3.out"; rc="$TMP/f3.rc"
# shellcheck disable=SC2016 # Fixture script is evaluated in a child shell with its own variables.
capture_fixture f3 "$out" "$rc" '
  design_reentry_marker_write 2935 111
  marker=$(design_reentry_marker_path 2935 111)
  touch -t 200001010101.01 "$marker"
  set +e
  design_reentry_marker_hit 2935 111 1
  hit_rc=$?
  set -e
  [ "$hit_rc" -eq 1 ]
  [ ! -f "$marker" ]
'
[ "$(cat "$rc")" = "0" ] || fail "F3 expected cleanup script rc=0"
grep -Fq 'MARKER_HIT=false REASON=stale' "$out" || fail "F3 expected stale"
rm -rf "$(cat "$out.home")"
pass "F3 stale cleanup"

# F4: same issue, different PPID does not hit.
out="$TMP/f4.out"; rc="$TMP/f4.rc"
# shellcheck disable=SC2016 # Fixture script is evaluated in a child shell with its own variables.
capture_fixture f4 "$out" "$rc" '
  design_reentry_marker_write 2935 111
  set +e
  design_reentry_marker_hit 2935 222
  hit_rc=$?
  set -e
  [ "$hit_rc" -eq 1 ]
'
[ "$(cat "$rc")" = "0" ] || fail "F4 expected wrapper rc=0"
grep -Fq 'MARKER_HIT=false REASON=absent' "$out" || fail "F4 expected absent"
rm -rf "$(cat "$out.home")"
pass "F4 different PPID admitted"

# F5: same PPID, different issue does not hit.
out="$TMP/f5.out"; rc="$TMP/f5.rc"
# shellcheck disable=SC2016 # Fixture script is evaluated in a child shell with its own variables.
capture_fixture f5 "$out" "$rc" '
  design_reentry_marker_write 2935 111
  set +e
  design_reentry_marker_hit 2936 111
  hit_rc=$?
  set -e
  [ "$hit_rc" -eq 1 ]
'
[ "$(cat "$rc")" = "0" ] || fail "F5 expected wrapper rc=0"
grep -Fq 'MARKER_HIT=false REASON=absent' "$out" || fail "F5 expected absent"
rm -rf "$(cat "$out.home")"
pass "F5 different issue admitted"

# F6: fresh HOME write creates parent dirs.
out="$TMP/f6.out"; rc="$TMP/f6.rc"
# shellcheck disable=SC2016 # Fixture script is evaluated in a child shell with its own variables.
capture_fixture f6 "$out" "$rc" '
  [ ! -d "$HOME/.cache/larch/sessions" ]
  design_reentry_marker_write 2935 111
  [ -d "$HOME/.cache/larch/sessions" ]
  design_reentry_marker_hit 2935 111
'
[ "$(cat "$rc")" = "0" ] || fail "F6 expected rc=0"
grep -Fq 'MARKER_HIT=true' "$out" || fail "F6 expected hit after write"
rm -rf "$(cat "$out.home")"
pass "F6 fresh HOME write"

# F7: future-dated marker misses and is removed.
out="$TMP/f7.out"; rc="$TMP/f7.rc"
# shellcheck disable=SC2016 # Fixture script is evaluated in a child shell with its own variables.
capture_fixture f7 "$out" "$rc" '
  design_reentry_marker_write 2935 111
  marker=$(design_reentry_marker_path 2935 111)
  touch -t 299901010101.01 "$marker"
  set +e
  design_reentry_marker_hit 2935 111
  hit_rc=$?
  set -e
  [ "$hit_rc" -eq 1 ]
  [ ! -f "$marker" ]
'
[ "$(cat "$rc")" = "0" ] || fail "F7 expected wrapper rc=0"
grep -Fq 'MARKER_HIT=false REASON=invalid-mtime' "$out" || fail "F7 expected invalid-mtime"
rm -rf "$(cat "$out.home")"
pass "F7 future mtime cleanup"

# F8: invalid input returns caller-error rc=2.
out="$TMP/f8.out"; rc="$TMP/f8.rc"
# shellcheck disable=SC2016 # Fixture script is evaluated in a child shell with its own variables.
capture_fixture f8 "$out" "$rc" '
  set +e
  design_reentry_marker_hit abc "$$"
  r1=$?
  design_reentry_marker_hit 2935 xyz
  r2=$?
  design_reentry_marker_write abc "$$" 2>/dev/null
  r3=$?
  set -e
  [ "$r1" -eq 2 ] && [ "$r2" -eq 2 ] && [ "$r3" -eq 2 ]
'
[ "$(cat "$rc")" = "0" ] || fail "F8 expected wrapper rc=0"
grep -Fc 'MARKER_HIT=false REASON=invalid-input' "$out" | grep -Fxq '2' || fail "F8 expected two invalid-input hit lines"
rm -rf "$(cat "$out.home")"
pass "F8 invalid input"

pass "test-design-reentry-guard.sh"
