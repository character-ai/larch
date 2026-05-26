#!/usr/bin/env bash
# test-render-final-summary.sh — offline harness for skills/design/scripts/render-final-summary.sh
set -euo pipefail
export LARCH_QUIET_DISABLE=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
SUBJECT="$ROOT/skills/design/scripts/render-final-summary.sh"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }

TMP=$(mktemp -d "${TMPDIR:-/tmp}/trfs.XXXXXX")
trap 'rm -rf "$TMP"' EXIT
export CLAUDE_PLUGIN_ROOT="$ROOT"
D="$TMP/design"
mkdir -p "$D"

cat >"$D/run-params.json" <<'JSON'
{"classification":"SIMPLE","workflow_path":"SIMPLE"}
JSON
cat >"$D/voting-tally.md" <<'EOF'
# Tally
EOF
cat >"$D/accepted-plan-findings.md" <<'EOF'
### FINDING_1: Example
- **Reviewer**: Codex-Pragmatic
- focus-area = correctness
- Concern: example
EOF
: >"$D/oos-accepted-design.md"
: >"$D/execution-issues.md"
: >"$D/oos-issues-created.md"

std="$TMP/std.log"
DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-FIX" \
    "$SUBJECT" --outcome approved --mode SIMPLE --post-publish-only >"$std" 2>/dev/null

grep -Fq -- '- **Cost**:' "$D/final-summary.md" || fail 'missing Cost bullet'
grep -Fq '<!-- larch:run-summary v=1 -->' "$D/final-summary.md" || fail 'missing sentinel'
cmp -s "$D/final-summary.md" "$std" || fail 'stdout vs final-summary.md byte mismatch'
pass 'approved happy path + cmp'

PLUGIN_STUB="$TMP/plugin"
mkdir -p "$PLUGIN_STUB/scripts"
cp "$ROOT/scripts/render-run-summary.sh" "$PLUGIN_STUB/scripts/render-run-summary.sh"
cp "$ROOT/scripts/token-cost.sh" "$PLUGIN_STUB/scripts/token-cost.sh"
cp "$ROOT/scripts/lib-cost-line-format.sh" "$PLUGIN_STUB/scripts/lib-cost-line-format.sh"
cat >"$PLUGIN_STUB/scripts/token-report.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
out=""
while [ $# -gt 0 ]; do
    case "$1" in
        --output) out=$2; shift 2 ;;
        *) shift ;;
    esac
done
[ -n "$out" ] || exit 2
cat >"$out" <<'JSON'
{
  "claude": {"totals": {"total": 0}},
  "codex": {"totals": {"total": 1050}},
  "cursor": {"totals": {"total": 0}},
  "BUCKETS_claude": {"input": 0, "cache_read": 0, "cache_create_5m": 0, "cache_create_1h": 0, "output": 0},
  "BUCKETS_codex": {"input": 100, "cached_input": 900, "output": 50, "total": 1050},
  "BUCKETS_cursor": {"input": 0, "cache_read": 0, "output": 0}
}
JSON
EOF
cat >"$PLUGIN_STUB/scripts/timing-report.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
out=""
while [ $# -gt 0 ]; do
    case "$1" in
        --output) out=$2; shift 2 ;;
        *) shift ;;
    esac
done
[ -n "$out" ] || exit 2
printf '%s\n' '{"total_hms":"12s"}' >"$out"
EOF
chmod +x "$PLUGIN_STUB/scripts/token-report.sh" "$PLUGIN_STUB/scripts/timing-report.sh" \
    "$PLUGIN_STUB/scripts/render-run-summary.sh" "$PLUGIN_STUB/scripts/token-cost.sh"

std_codex="$TMP/std-codex.log"
CLAUDE_PLUGIN_ROOT="$PLUGIN_STUB" DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-FIX" \
    "$SUBJECT" --outcome approved --mode SIMPLE --post-publish-only >"$std_codex" 2>"$TMP/std-codex.err"
grep -Fq -- '- **Cost**:' "$D/final-summary.md" || fail 'codex buckets run missing Cost bullet'
grep -Fq '💰 TOTAL' "$D/final-summary.md" || fail 'per-agent cost line missing TOTAL marker'
grep -Fq 'Claude $' "$D/final-summary.md" || fail 'per-agent cost line missing Claude slot'
grep -Fq 'Codex $' "$D/final-summary.md" || fail 'per-agent cost line missing Codex slot'
grep -Fq 'Cursor $' "$D/final-summary.md" || fail 'per-agent cost line missing Cursor slot'
grep -Fq 'Tokens: ' "$D/final-summary.md" || fail 'per-agent cost line missing token count'
if grep -Eq 'BLENDED_WARN|blended rate' "$std_codex" "$D/final-summary.md" "$TMP/std-codex.err"; then
    fail 'codex per-bucket design summary must not surface blended-rate warnings'
fi
pass 'codex per-bucket summary omits blended warning'

cp "$PLUGIN_STUB/scripts/render-run-summary.sh" "$TMP/render-run-summary.real"
cat >"$PLUGIN_STUB/scripts/render-run-summary.sh" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
chmod +x "$PLUGIN_STUB/scripts/render-run-summary.sh"
std_fb="$TMP/std-fallback.log"
CLAUDE_PLUGIN_ROOT="$PLUGIN_STUB" DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-FB" \
    "$SUBJECT" --outcome approved --mode SIMPLE --post-publish-only >"$std_fb" 2>/dev/null
grep -Fq -- '- **Cost**: N/A' "$D/final-summary.md" || fail 'renderer-fail fallback missing Cost N/A'
cmp -s "$D/final-summary.md" "$std_fb" || fail 'renderer-fail fallback stdout/file mismatch'
pass 'renderer-fail fallback prints final file once'
cp "$TMP/render-run-summary.real" "$PLUGIN_STUB/scripts/render-run-summary.sh"
chmod +x "$PLUGIN_STUB/scripts/render-run-summary.sh"

PLUGIN_FAILTOK="$TMP/plugin-failtok"
mkdir -p "$PLUGIN_FAILTOK/scripts"
cp "$ROOT/scripts/render-run-summary.sh" "$PLUGIN_FAILTOK/scripts/render-run-summary.sh"
cp "$ROOT/scripts/token-cost.sh" "$PLUGIN_FAILTOK/scripts/token-cost.sh"
cp "$ROOT/scripts/lib-cost-line-format.sh" "$PLUGIN_FAILTOK/scripts/lib-cost-line-format.sh"
cat >"$PLUGIN_FAILTOK/scripts/token-report.sh" <<'EOF'
#!/usr/bin/env bash
printf 'token report unavailable\n' >&2
exit 9
EOF
cat >"$PLUGIN_FAILTOK/scripts/timing-report.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
out=""
while [ $# -gt 0 ]; do
  case "$1" in --output) out=$2; shift 2 ;; *) shift ;; esac
done
printf '%s\n' '{"total_hms":"1s"}' >"$out"
EOF
chmod +x "$PLUGIN_FAILTOK/scripts/"*.sh
std_failtok="$TMP/std-failtok.log"
CLAUDE_PLUGIN_ROOT="$PLUGIN_FAILTOK" DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-FAILTOK" \
    "$SUBJECT" --outcome approved --mode SIMPLE --post-publish-only >"$std_failtok" 2>/dev/null
grep -Fq -- '- **Cost**: N/A' "$D/final-summary.md" || fail 'token-data-missing path missing Cost N/A'
if grep -Fq "Claude \$0.00, Codex \$0.00, Cursor \$0.00" "$D/final-summary.md"; then
    fail 'token-data-missing path rendered misleading zero-dollar cost'
fi
pass 'token-data-missing path renders Cost N/A'

EMPTY_MODE_D="$TMP/design-empty-mode"
mkdir -p "$EMPTY_MODE_D"
: >"$EMPTY_MODE_D/execution-issues.md"
SUMMARY_OUTCOME=cancelled-tier-gate
SUMMARY_MODE_STRING=""
if [ -f "$EMPTY_MODE_D/run-params.json" ] && command -v jq >/dev/null 2>&1; then
  SUMMARY_MODE_STRING="$(jq -r '.design_classification // "N/A"' "$EMPTY_MODE_D/run-params.json" 2>/dev/null || echo N/A)"
fi
[ -n "$SUMMARY_MODE_STRING" ] || SUMMARY_MODE_STRING=N/A
DESIGN_TMPDIR="$EMPTY_MODE_D" ISSUE_NUMBER="" SESSION_ID="RUN-EMPTY-MODE" \
    "$SUBJECT" --outcome "$SUMMARY_OUTCOME" --mode "$SUMMARY_MODE_STRING" --post-publish-only >"$TMP/std-empty-mode.log" 2>/dev/null
grep -Fq -- '- **Mode**: N/A' "$EMPTY_MODE_D/final-summary.md" || fail 'empty-mode fence did not default to N/A'
grep -Fq '## /design run RUN-EMPTY-MODE — cancelled-tier-gate' "$EMPTY_MODE_D/final-summary.md" || fail 'empty-mode cancellation summary missing'
pass 'early cancellation empty-mode default'

DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-FIX" \
    "$SUBJECT" --outcome cancelled-clarify --mode SIMPLE --post-publish-only >/dev/null 2>&1
grep -Fq -- '- **Outcome**: cancelled-clarify' "$D/final-summary.md" || fail 'missing outcome bullet'
pass 'cancelled-clarify outcome'

DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-FIX" \
    "$SUBJECT" --outcome cancelled-title-filter --mode SIMPLE --post-publish-only >/dev/null 2>&1
grep -Fq '## /design run RUN-FIX — cancelled-title-filter' "$D/final-summary.md" || fail 'cancelled-title-filter title missing'
grep -Fq -- '- **Outcome**: cancelled-title-filter' "$D/final-summary.md" || fail 'missing cancelled-title-filter outcome bullet'
grep -Fq -- '- **Mode**: Refused (title-filter)' "$D/final-summary.md" || fail 'missing Refused (title-filter) mode line'
pass 'cancelled-title-filter outcome'

DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-FIX" \
    "$SUBJECT" --outcome approved-partition --mode SIMPLE --post-publish-only >/dev/null 2>&1
grep -Fq '## /design run RUN-FIX — approved-partition' "$D/final-summary.md" || fail 'approved-partition title missing'
pass 'approved-partition outcome'

DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-FIX" \
    "$SUBJECT" --outcome cancelled-decompose --mode SIMPLE --post-publish-only >/dev/null 2>&1
grep -Fq '## /design run RUN-FIX — cancelled-decompose' "$D/final-summary.md" || fail 'cancelled-decompose title missing'
grep -Fq -- '- **Outcome**: cancelled-decompose' "$D/final-summary.md" || fail 'missing cancelled-decompose outcome bullet'
pass 'cancelled-decompose outcome'

set +e
DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-FIX" \
    "$SUBJECT" --outcome cancelled-plan-size-soft --mode SIMPLE --post-publish-only >/dev/null 2>&1
rc=$?
set -e
test "$rc" -eq 2 || fail 'invalid outcome must exit 2'
pass 'invalid outcome rejected'

printf 'PASS: test-render-final-summary.sh\n'
