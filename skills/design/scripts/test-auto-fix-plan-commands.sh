#!/usr/bin/env bash
# Offline harness for auto-fix-plan-commands.sh (#3628 Component D).
# Uses the LARCH_AUTOFIX_DISPATCH_SH and LARCH_AUTOFIX_VALIDATE_PLAN_SH seams so no
# real Codex/Cursor binary or validator runs.
set -euo pipefail
export LARCH_QUIET_DISABLE=1

ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
SUBJECT="$ROOT/skills/design/scripts/auto-fix-plan-commands.sh"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }

bash -n "$SUBJECT" || fail 'bash -n failed'

TMP=$(mktemp -d "${TMPDIR:-/tmp}/tafpc.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

# Validator stub: ok once the dispatch stub has written the .autofix-fixed marker,
# defects-found otherwise. Reads DESIGN_TMPDIR from the env exported by the subject.
VALIDATE_STUB="$TMP/validate-stub.sh"
cat >"$VALIDATE_STUB" <<'STUB'
#!/usr/bin/env bash
if [ -f "$DESIGN_TMPDIR/.autofix-fixed" ]; then
  printf 'VALIDATE_STATUS=ok\n'
else
  printf 'VALIDATE_STATUS=defects-found\n'
fi
exit 0
STUB
chmod +x "$VALIDATE_STUB"

# Dispatch stub: behavior keyed by AUTOFIX_TEST_MODE.
#   fix-first   → any vendor writes the fixed marker (attempt 1 succeeds).
#   never-fix   → no vendor writes the marker (loop exhausts).
#   codex-fail-cursor-fix → codex returns 1 + no marker; cursor writes marker.
DISPATCH_STUB="$TMP/dispatch-stub.sh"
cat >"$DISPATCH_STUB" <<'STUB'
#!/usr/bin/env bash
vendor=""; design_tmpdir=""
while [ $# -gt 0 ]; do
  case "$1" in
    --vendor) vendor="$2"; shift 2 ;;
    --design-tmpdir) design_tmpdir="$2"; shift 2 ;;
    *) shift ;;
  esac
done
printf '%s\n' "$vendor" >>"$design_tmpdir/.autofix-vendor-calls"
case "${AUTOFIX_TEST_MODE:-}" in
  fix-first) : >"$design_tmpdir/.autofix-fixed"; exit 0 ;;
  never-fix) exit 0 ;;
  codex-fail-cursor-fix)
    if [ "$vendor" = codex ]; then exit 1; fi
    : >"$design_tmpdir/.autofix-fixed"; exit 0 ;;
  *) exit 0 ;;
esac
STUB
chmod +x "$DISPATCH_STUB"

mk_design() {
  local d="$1"
  mkdir -p "$d"
  printf 'plan body\ndiff_lines: 3\n' >"$d/plan.txt"
}

kv() { printf '%s\n' "$1" | awk -F= -v k="$2" '$1==k{print substr($0,length(k)+2); exit}'; }

run_subject() {
  local d="$1"; shift
  LARCH_AUTOFIX_DISPATCH_SH="$DISPATCH_STUB" \
  LARCH_AUTOFIX_VALIDATE_PLAN_SH="$VALIDATE_STUB" \
  "$SUBJECT" --design-tmpdir "$d" --plan-file "$d/plan.txt" "$@" 2>/dev/null
}

# Case 1: no vendors available → unavailable, no dispatch.
D1="$TMP/d1"; mk_design "$D1"
out1=$(run_subject "$D1" --codex-present false --cursor-present false)
[[ "$(kv "$out1" AUTOFIX_STATUS)" == "unavailable" ]] || fail "case1 expected unavailable: $out1"
[[ "$(kv "$out1" ATTEMPTS)" == "0" ]] || fail "case1 expected 0 attempts"
[[ ! -f "$D1/.autofix-vendor-calls" ]] || fail "case1 must not dispatch any vendor"

# Case 2: codex fixes on first attempt → ok, FIXED_BY=codex, 1 attempt.
D2="$TMP/d2"; mk_design "$D2"
out2=$(AUTOFIX_TEST_MODE=fix-first run_subject "$D2" --codex-present true --cursor-present true)
[[ "$(kv "$out2" AUTOFIX_STATUS)" == "ok" ]] || fail "case2 expected ok: $out2"
[[ "$(kv "$out2" FIXED_BY)" == "codex" ]] || fail "case2 expected FIXED_BY=codex: $out2"
[[ "$(kv "$out2" ATTEMPTS)" == "1" ]] || fail "case2 expected 1 attempt: $out2"
[[ "$(kv "$out2" VENDOR_SEQUENCE)" == "codex" ]] || fail "case2 expected sequence codex: $out2"

# Case 3: never fixes → exhausted after 2 attempts, cross-vendor alternation.
D3="$TMP/d3"; mk_design "$D3"
out3=$(AUTOFIX_TEST_MODE=never-fix run_subject "$D3" --codex-present true --cursor-present true)
[[ "$(kv "$out3" AUTOFIX_STATUS)" == "exhausted" ]] || fail "case3 expected exhausted: $out3"
[[ "$(kv "$out3" ATTEMPTS)" == "2" ]] || fail "case3 expected 2 attempts: $out3"
[[ "$(kv "$out3" VENDOR_SEQUENCE)" == "codex,cursor" ]] || fail "case3 expected codex,cursor: $out3"
[[ "$(kv "$out3" FIXED_BY)" == "" ]] || fail "case3 FIXED_BY must be empty: $out3"
[[ "$(kv "$out3" FINAL_VALIDATE_STATUS)" == "defects-found" ]] || fail "case3 final status: $out3"

# Case 4: codex fails, cursor fixes → ok, FIXED_BY=cursor (cross-vendor recovery).
D4="$TMP/d4"; mk_design "$D4"
out4=$(AUTOFIX_TEST_MODE=codex-fail-cursor-fix run_subject "$D4" --codex-present true --cursor-present true)
[[ "$(kv "$out4" AUTOFIX_STATUS)" == "ok" ]] || fail "case4 expected ok: $out4"
[[ "$(kv "$out4" FIXED_BY)" == "cursor" ]] || fail "case4 expected FIXED_BY=cursor: $out4"
[[ "$(kv "$out4" VENDOR_SEQUENCE)" == "codex,cursor" ]] || fail "case4 expected codex,cursor: $out4"

# Case 5: only cursor present → sequence starts with cursor.
D5="$TMP/d5"; mk_design "$D5"
out5=$(AUTOFIX_TEST_MODE=never-fix run_subject "$D5" --codex-present false --cursor-present true --max-attempts 1)
[[ "$(kv "$out5" VENDOR_SEQUENCE)" == "cursor" ]] || fail "case5 expected cursor: $out5"
[[ "$(kv "$out5" ATTEMPTS)" == "1" ]] || fail "case5 expected 1 attempt: $out5"

# Case 6: argv validation — missing plan file fails closed.
D6="$TMP/d6"; mk_design "$D6"
if LARCH_AUTOFIX_DISPATCH_SH="$DISPATCH_STUB" LARCH_AUTOFIX_VALIDATE_PLAN_SH="$VALIDATE_STUB" \
   "$SUBJECT" --design-tmpdir "$D6" --plan-file "$D6/missing.txt" --codex-present true --cursor-present true >/dev/null 2>&1; then
  fail 'case6 missing plan file must fail closed'
fi
# bad boolean
if "$SUBJECT" --design-tmpdir "$D6" --plan-file "$D6/plan.txt" --codex-present maybe --cursor-present true >/dev/null 2>&1; then
  fail 'case6 invalid --codex-present must fail closed'
fi

pass 'auto-fix-plan-commands harness'
