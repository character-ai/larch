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
if grep -Eq 'BLENDED_WARN|blended rate' "$std_codex" "$D/final-summary.md" "$TMP/std-codex.err"; then
    fail 'codex per-bucket design summary must not surface blended-rate warnings'
fi
pass 'codex per-bucket summary omits blended warning'

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
