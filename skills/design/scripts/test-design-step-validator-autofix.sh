#!/usr/bin/env bash
# test-design-step-validator-autofix.sh — offline harness for validator autofix escalation and cancel paths.
set -euo pipefail
export LARCH_QUIET_DISABLE=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
SUBJECT="$ROOT/skills/design/scripts/design-step-validator-autofix.sh"
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$*"; }
kv() { printf '%s\n' "$1" | awk -F= -v k="$2" '$1==k{print substr($0,length(k)+2); exit}'; }

TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-design-step-validator-autofix.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

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

DISPATCH_STUB="$TMP/dispatch-stub.sh"
cat >"$DISPATCH_STUB" <<'STUB'
#!/usr/bin/env bash
while [ $# -gt 0 ]; do
  case "$1" in
    --run-dir) run_dir="$2"; shift 2 ;;
    --plan-file) plan_file="$2"; shift 2 ;;
    *) shift ;;
  esac
done
: >"${run_dir:-/tmp}/autofix-vendor-calls"
if [ "${AUTOFIX_TEST_MODE:-}" = fix-ok ] && [ -n "${plan_file:-}" ]; then
  printf '
autofix fixed
' >>"$plan_file"
fi
exit 0
STUB
chmod +x "$DISPATCH_STUB"

D=$(mktemp -d "$TMP/escalation.XXXXXX")
mkdir -p "$D"
printf 'plan body\ndiff_lines: 3\n' >"$D/plan.txt"
printf 'validate defects\n' >"$D/validate-plan-commands.log"
set +e
out=$(AUTOFIX_TEST_MODE=never-fix CLAUDE_PLUGIN_ROOT="$ROOT" DESIGN_TMPDIR="$D" \
  CODEX_BINARY_FOUND=true CURSOR_BINARY_FOUND=true \
  LARCH_AUTOFIX_DISPATCH_SH="$DISPATCH_STUB" \
  LARCH_AUTOFIX_VALIDATE_PLAN_SH="$VALIDATE_STUB" \
  "$SUBJECT" --site 'design Step 2b' --validator-target-file "$D/plan.txt" --validate-log-file "$D/validate-plan-commands.log" \
  --validate-defect-count 1 --validate-unsafe-token-count 0 --validate-skipped-count 0 2>"$D/err")
rc=$?
set -e
[[ "$rc" -eq 0 ]] || fail "validator autofix wrapper must exit 0 on exhausted (rc=$rc)"
[[ "$(kv "$out" AUTOFIX_STATUS)" == "exhausted" ]] || fail "exhausted autofix status missing: $out"
[ -s "$D/design-failure-escalation-ledger.tsv" ] || fail 'exhausted autofix must record escalation evidence'
pass 'validator autofix records escalation on exhausted status'

D2=$(mktemp -d "$TMP/cancel.XXXXXX")
mkdir -p "$D2"
: >"$D2/execution-issues.md"
CLAUDE_PLUGIN_ROOT="$ROOT" DESIGN_TMPDIR="$D2" SUMMARY_OUTCOME=cancelled-plan-size \
  "$SUBJECT" --operator-cancel >"$D2/cancel.out"
[ -s "$D2/design-failure-operator-action.env" ] || fail 'operator cancel must write sentinel'
[ -s "$D2/design-failure-operator-action-chat.md" ] || fail 'operator cancel must write chat sidecar'
grep -Fq 'cancelled-plan-size' "$D2/design-failure-operator-action-chat.md" || fail 'operator cancel chat must name outcome'
grep -Fq 'design validator autofix' "$D2/execution-issues.md" || grep -Fq '### Warnings' "$D2/execution-issues.md" || fail 'operator cancel must append run-log audit'
pass 'validator operator-cancel writes sentinel chat and run-log audit'


D_OK=$(mktemp -d "$TMP/ok.XXXXXX")
mkdir -p "$D_OK"
printf 'plan body\ndiff_lines: 3\n' >"$D_OK/plan.txt"
printf 'original validator defects\n' >"$D_OK/validate-plan-commands.log"
set +e
out_ok=$(AUTOFIX_TEST_MODE=fix-ok CLAUDE_PLUGIN_ROOT="$ROOT" DESIGN_TMPDIR="$D_OK" \
  CODEX_BINARY_FOUND=true CURSOR_BINARY_FOUND=false \
  LARCH_AUTOFIX_DISPATCH_SH="$DISPATCH_STUB" \
  LARCH_AUTOFIX_VALIDATE_PLAN_SH="$VALIDATE_STUB" \
  "$SUBJECT" --site 'design Step 2b' --validator-target-file "$D_OK/plan.txt" --validate-log-file "$D_OK/validate-plan-commands.log" \
  --validate-defect-count 1 --validate-unsafe-token-count 0 --validate-skipped-count 0 2>"$D_OK/err")
rc_ok=$?
set -e
[[ "$rc_ok" -eq 0 ]] || fail "validator autofix wrapper must exit 0 on ok (rc=$rc_ok)"
[[ "$(kv "$out_ok" AUTOFIX_STATUS)" == "ok" ]] || fail "ok autofix status missing: $out_ok"
issues_ok="$D_OK/execution-issues.md"
[ -s "$issues_ok" ] || fail 'ok autofix must append execution issue audit'
[[ "$(grep -Fc -- 'validate-plan-commands(auto-fixed:' "$issues_ok")" == "1" ]] || fail 'ok autofix must append exactly one auto-fixed Warnings row'
grep -Fq 'design Step 2b' "$issues_ok" || fail 'ok autofix Warnings row must include site value'
orig_log=$(kv "$out_ok" ORIGINAL_VALIDATE_LOG_FILE)
[ -n "$orig_log" ] || fail 'ok autofix output must include ORIGINAL_VALIDATE_LOG_FILE'
grep -Fq 'original validator defects' "$issues_ok" || fail 'ok autofix row must include preserved original validator log content'
grep -Fq 'autofix fixed' "$D_OK/plan.txt" || fail 'ok autofix dispatch must update plan once'
[ ! -s "$D_OK/design-failure-escalation-ledger.tsv" ] || fail 'ok autofix must not record escalation evidence'
pass 'validator autofix records exactly one ok-path Warnings row'

D_FALSE=$(mktemp -d "$TMP/false-ok.XXXXXX")
mkdir -p "$D_FALSE/bin" "$D_FALSE/fake-plugin/python"
printf 'plan body\ndiff_lines: 3\n' >"$D_FALSE/plan.txt"
printf 'validator defects\n' >"$D_FALSE/validate-plan-commands.log"
cat >"$D_FALSE/bin/python3" <<'STUBPY'
#!/usr/bin/env bash
set -euo pipefail
shift || true
if [ "${1:-} ${2:-}" = "plan auto-fix-commands" ]; then
  printf 'AUTOFIX_STATUS=ok\nFIXED_BY=codex\nORIGINAL_VALIDATE_LOG_FILE=%s\n' "$DESIGN_TMPDIR/validate-plan-commands.log"
  exit 7
fi
if [ "${1:-} ${2:-}" = "stall-recovery record-escalation" ]; then
  : >"$DESIGN_TMPDIR/design-failure-escalation-ledger.tsv"
  exit 0
fi
if [ "${1:-} ${2:-}" = "run-log append-failure" ]; then
  printf 'unexpected ok-path append on false ok\n' >>"$DESIGN_TMPDIR/execution-issues.md"
  exit 0
fi
exit 0
STUBPY
chmod +x "$D_FALSE/bin/python3"
set +e
out_false=$(PATH="$D_FALSE/bin:$PATH" CLAUDE_PLUGIN_ROOT="$D_FALSE/fake-plugin" DESIGN_TMPDIR="$D_FALSE" \
  CODEX_BINARY_FOUND=true CURSOR_BINARY_FOUND=false \
  "$SUBJECT" --site 'design Step 2b' --validator-target-file "$D_FALSE/plan.txt" --validate-log-file "$D_FALSE/validate-plan-commands.log" \
  --validate-defect-count 1 --validate-unsafe-token-count 0 --validate-skipped-count 0 2>"$D_FALSE/err")
rc_false=$?
set -e
[[ "$rc_false" -eq 0 ]] || fail "false-ok wrapper invocation must exit 0 for escalation path (rc=$rc_false)"
[[ "$(kv "$out_false" AUTOFIX_STATUS)" == "ok" ]] || fail "false-ok fixture must print raw ok status"
[ ! -s "$D_FALSE/execution-issues.md" ] || fail 'nonzero helper with ok output must not append ok-path Warnings row'
pass 'validator autofix suppresses ok audit when helper exits nonzero'

bash -n "$SUBJECT" || fail 'bash -n design-step-validator-autofix.sh failed'

printf 'PASS: test-design-step-validator-autofix.sh\n'
