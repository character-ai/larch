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
    *) shift ;;
  esac
done
: >"${run_dir:-/tmp}/autofix-vendor-calls"
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

bash -n "$SUBJECT" || fail 'bash -n design-step-validator-autofix.sh failed'

printf 'PASS: test-design-step-validator-autofix.sh\n'
