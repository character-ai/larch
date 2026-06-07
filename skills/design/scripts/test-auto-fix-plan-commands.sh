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

# Validator stub: ok once the dispatch stub has updated the target plan file,
# defects-found otherwise.
VALIDATE_STUB="$TMP/validate-stub.sh"
cat >"$VALIDATE_STUB" <<'STUB'
#!/usr/bin/env bash
plan_file=""
while [ $# -gt 0 ]; do
  case "$1" in
    --plan-file) plan_file="$2"; shift 2 ;;
    *) shift ;;
  esac
done
if grep -Fq 'autofix fixed' "$plan_file"; then
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
vendor=""; plan_file=""; run_dir=""
while [ $# -gt 0 ]; do
  case "$1" in
    --vendor) vendor="$2"; shift 2 ;;
    --plan-file) plan_file="$2"; shift 2 ;;
    --run-dir) run_dir="$2"; shift 2 ;;
    --design-tmpdir) shift 2 ;;
    *) shift ;;
  esac
done
printf '%s\n' "$vendor" >>"$run_dir/autofix-vendor-calls"
case "${AUTOFIX_TEST_MODE:-}" in
  fix-first) printf 'plan body\nautofix fixed\ndiff_lines: 3\n' >"$plan_file"; exit 0 ;;
  never-fix) exit 0 ;;
  codex-fail-cursor-fix)
    if [ "$vendor" = codex ]; then exit 1; fi
    printf 'plan body\nautofix fixed\ndiff_lines: 3\n' >"$plan_file"; exit 0 ;;
  mutate-tmpdir)
    printf 'bad mutation\n' >"$(dirname "$plan_file")/accepted-plan-findings.md"
    printf 'plan body\nautofix fixed\ndiff_lines: 3\n' >"$plan_file"
    exit 0
    ;;
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
[[ ! -d "$D1/plan-autofix" ]] || fail "case1 must not dispatch any vendor"

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

# Case 5: only cursor present → sequence starts with cursor and does not duplicate
# the sole vendor even when max-attempts is higher.
D5="$TMP/d5"; mk_design "$D5"
out5=$(AUTOFIX_TEST_MODE=never-fix run_subject "$D5" --codex-present false --cursor-present true --max-attempts 3)
[[ "$(kv "$out5" VENDOR_SEQUENCE)" == "cursor" ]] || fail "case5 expected cursor: $out5"
[[ "$(kv "$out5" ATTEMPTS)" == "1" ]] || fail "case5 expected 1 attempt: $out5"

# Case 6: argv validation — missing plan file fails closed.
D6="$TMP/d6"; mk_design "$D6"
if LARCH_AUTOFIX_DISPATCH_SH="$DISPATCH_STUB" LARCH_AUTOFIX_VALIDATE_PLAN_SH="$VALIDATE_STUB" \
   "$SUBJECT" --design-tmpdir "$D6" --plan-file "$D6/missing.txt" --codex-present true --cursor-present true >/dev/null 2>&1; then
  fail 'case6 missing plan file must fail closed'
fi
# plan file must be a real session-local file, not a symlink or outside path.
OUTSIDE="$TMP/outside-plan.txt"
printf 'outside\n' >"$OUTSIDE"
if LARCH_AUTOFIX_DISPATCH_SH="$DISPATCH_STUB" LARCH_AUTOFIX_VALIDATE_PLAN_SH="$VALIDATE_STUB" \
   "$SUBJECT" --design-tmpdir "$D6" --plan-file "$OUTSIDE" --codex-present true --cursor-present true >/dev/null 2>&1; then
  fail 'case6 outside plan file must fail closed'
fi
ln -s "$D6/plan.txt" "$D6/plan-link.txt"
if LARCH_AUTOFIX_DISPATCH_SH="$DISPATCH_STUB" LARCH_AUTOFIX_VALIDATE_PLAN_SH="$VALIDATE_STUB" \
   "$SUBJECT" --design-tmpdir "$D6" --plan-file "$D6/plan-link.txt" --codex-present true --cursor-present true >/dev/null 2>&1; then
  fail 'case6 symlink plan file must fail closed'
fi
# bad boolean
if "$SUBJECT" --design-tmpdir "$D6" --plan-file "$D6/plan.txt" --codex-present maybe --cursor-present true >/dev/null 2>&1; then
  fail 'case6 invalid --codex-present must fail closed'
fi

# Case 7: prompt rendering fails closed on validator-log redaction failure and
# preserves the original validator log path after revalidation overwrites the live log.
D7="$TMP/d7"; mk_design "$D7"
D7_CANON="$(cd "$D7" && pwd -P)"
printf 'raw-secret-token\n' >"$D7/validate-plan-commands.log"
REDACT_FAIL="$TMP/redact-fail-plugin"
mkdir -p "$REDACT_FAIL/scripts" "$REDACT_FAIL/skills/design/scripts"
cp "$ROOT/scripts/lib-quiet.sh" "$REDACT_FAIL/scripts/lib-quiet.sh"
cp "$ROOT/scripts/lib-design-tmpdir.sh" "$REDACT_FAIL/scripts/lib-design-tmpdir.sh"
cat >"$REDACT_FAIL/scripts/redact-secrets.sh" <<'STUB'
#!/usr/bin/env bash
exit 1
STUB
chmod +x "$REDACT_FAIL/scripts/redact-secrets.sh"
out7=$(AUTOFIX_TEST_MODE=never-fix CLAUDE_PLUGIN_ROOT="$REDACT_FAIL" run_subject "$D7" --codex-present true --cursor-present false --max-attempts 1)
prompt7="$D7/plan-autofix/attempt-1-codex/prompt.md"
grep -Fq '[validator log redaction failed; raw log intentionally withheld]' "$prompt7" \
  || fail 'case7 prompt must include redaction-failed placeholder'
if grep -Fq 'raw-secret-token' "$prompt7"; then
  fail 'case7 prompt must not include raw validator log after redaction failure'
fi
orig_log7="$(kv "$out7" ORIGINAL_VALIDATE_LOG_FILE)"
[[ "$orig_log7" == "$D7_CANON/plan-autofix/original-validate-plan-commands-design_plan-command_auto-fix-plan.txt.log" ]] \
  || fail "case7 original log path drifted: $out7"
grep -Fq 'raw-secret-token' "$orig_log7" || fail 'case7 original validator evidence copy missing'

# Case 8: non-target tmpdir mutation is restored and cannot be treated as success
# even when the plan file itself was fixed.
D8="$TMP/d8"; mk_design "$D8"
printf 'trusted accepted\n' >"$D8/accepted-plan-findings.md"
out8=$(AUTOFIX_TEST_MODE=mutate-tmpdir run_subject "$D8" --codex-present true --cursor-present false --max-attempts 1)
[[ "$(kv "$out8" AUTOFIX_STATUS)" == "exhausted" ]] || fail "case8 expected exhausted after guard failure: $out8"
[[ "$(cat "$D8/accepted-plan-findings.md")" == "trusted accepted" ]] || fail 'case8 trusted artifact mutation must be restored'

# Case 9: validator infrastructure failure stops after the first attempt and
# leaves a durable revalidation log path.
INFRA_VALIDATE="$TMP/validate-infra.sh"
cat >"$INFRA_VALIDATE" <<'STUB'
#!/usr/bin/env bash
printf 'validator crashed\n' >&2
exit 2
STUB
chmod +x "$INFRA_VALIDATE"
D9="$TMP/d9"; mk_design "$D9"
out9=$(AUTOFIX_TEST_MODE=fix-first LARCH_AUTOFIX_VALIDATE_PLAN_SH="$INFRA_VALIDATE" \
  LARCH_AUTOFIX_DISPATCH_SH="$DISPATCH_STUB" "$SUBJECT" --design-tmpdir "$D9" --plan-file "$D9/plan.txt" \
  --codex-present true --cursor-present true 2>/dev/null)
[[ "$(kv "$out9" AUTOFIX_STATUS)" == "exhausted" ]] || fail "case9 expected exhausted after infra failure: $out9"
[[ "$(kv "$out9" FINAL_VALIDATE_STATUS)" == "validator-infra-failed" ]] || fail "case9 final status: $out9"
[[ -f "$(kv "$out9" REVALIDATE_LOG_FILE)" ]] || fail "case9 missing revalidate log: $out9"

pass 'auto-fix-plan-commands harness'
