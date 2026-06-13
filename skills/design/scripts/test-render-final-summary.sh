#!/usr/bin/env bash
# test-render-final-summary.sh — offline harness for skills/design/scripts/render-final-summary.sh
set -euo pipefail
export LARCH_QUIET_DISABLE=1
unset IMPLEMENT_TMPDIR REVIEW_TMPDIR DESIGN_TMPDIR RESEARCH_TMPDIR \
    LARCH_QUIET_BREADCRUMB_FD LARCH_QUIET_PID LARCH_QUIET_ACTIVE \
    LARCH_QUIET_LOG_FILE LARCH_QUIET_LOG LARCH_DONE_OWNER_PID 2>/dev/null || true

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
SUBJECT="$ROOT/skills/design/scripts/render-final-summary.sh"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }
stdout_starts_with_summary() {
    local summary_file="$1" stdout_file="$2" label="$3"
    python3 - "$summary_file" "$stdout_file" "$label" <<'PY_SUMMARY_PREFIX'
import sys
summary = open(sys.argv[1], encoding="utf-8").read()
stdout = open(sys.argv[2], encoding="utf-8").read()
label = sys.argv[3]
if not stdout.startswith(summary):
    print(f"FAIL: {label}", file=sys.stderr)
    raise SystemExit(1)
PY_SUMMARY_PREFIX
}

TMP=$(mktemp -d "${TMPDIR:-/tmp}/trfs.XXXXXX")
trap 'rm -rf "$TMP"' EXIT
export CLAUDE_PLUGIN_ROOT="$ROOT"
D="$TMP/design"
mkdir -p "$D"

cat >"$D/run-params.json" <<'JSON'
JSON
cat >"$D/voting-tally.md" <<'EOF'
# Tally
EOF
cat >"$D/accepted-plan-findings.md" <<'EOF'
### FINDING_1: Example
- **Reviewer**: Codex-Pragmatic
- **Focus area**: correctness
- **Concern**: example
EOF
: >"$D/oos-accepted-design.md"
: >"$D/execution-issues.md"
: >"$D/oos-issues-created.md"

std="$TMP/std.log"
DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-FIX" \
    "$SUBJECT" --outcome approved --post-publish-only >"$std" 2>/dev/null

grep -Fq -- '- **Cost**:' "$D/final-summary.md" || fail 'missing Cost bullet'
grep -Fq '<!-- larch:run-summary v=1 -->' "$D/final-summary.md" || fail 'missing sentinel'
cmp -s "$D/final-summary.md" "$std" || fail 'stdout vs final-summary.md byte mismatch'
grep -Fq -- '## Review Phase Detail' "$D/final-summary.md" || fail 'no-plan-review final summary missing Review Phase Detail'
grep -Fq -- 'No review rounds completed.' "$D/final-summary.md" || fail 'no-plan-review final summary missing no-round message'
grep -Fq -- '## Review Phase Detail' "$std" || fail 'no-plan-review stdout missing Review Phase Detail'
# Plan review line must report non-zero when accepted-plan-findings.md has FINDING_ blocks.
if grep -Fq -- '- **Plan review**: 0 findings' "$D/final-summary.md"; then
    fail 'plan review line must not show 0 findings when accepted-plan-findings.md has accepted blocks'
fi
grep -q -- '- \*\*Plan review\*\*: [1-9]' "$D/final-summary.md" || fail 'plan review line must show non-zero finding count'
pass 'approved happy path + cmp'

# Regression: plan review with OOS block also counts correctly.
cat >"$D/accepted-plan-findings.md" <<'EOF'
### FINDING_1: Security gap
- **Reviewer**: Cursor-Pragmatic
- **Focus area**: security
- **Concern**: missing auth check
EOF
cat >"$D/oos-accepted-design.md" <<'EOF'
### OOS_1: Extra cleanup
- **Reviewer**: Codex-Pragmatic
- **Focus area**: code-quality
- **Concern**: unused var
EOF
std_oos="$TMP/std-with-oos.log"
DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-OOS" \
    "$SUBJECT" --outcome approved --post-publish-only >"$std_oos" 2>/dev/null
if grep -Fq -- '- **Plan review**: 0 findings' "$D/final-summary.md"; then
    fail 'plan review must not show 0 findings when FINDING_+OOS_ blocks exist'
fi
grep -q -- '- \*\*Plan review\*\*: 2 ' "$D/final-summary.md" || fail 'plan review line must count FINDING_+OOS_ blocks (expected 2)'
pass 'plan review counts FINDING_+OOS_ blocks with bold Focus area format'
rm -f "$D/oos-accepted-design.md"
std_missing_oos="$TMP/std-missing-oos.log"
DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-MISSING-OOS" \
    "$SUBJECT" --outcome approved --post-publish-only >"$std_missing_oos" 2>/dev/null
grep -q -- '- \*\*Plan review\*\*: 1 ' "$D/final-summary.md" || fail 'missing optional OOS artifact must not zero accepted findings'
pass 'plan review counts accepted findings when optional OOS artifact is missing'

# --- sentinel fallback: oos-issues-created.md absent, oos-issue-sentinel present ---
rm -f "$D/oos-issues-created.md"
cat >"$D/oos-issue-sentinel" <<'EOF'
ISSUE_SENTINEL_VERSION=1
ISSUES_CREATED=3
ISSUES_DEDUPLICATED=0
ISSUES_FAILED=0
TIMESTAMP=2025-01-01T00:00:00Z
EOF
std_sentinel_oos="$TMP/std-sentinel-oos.log"
DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-SENTINEL-OOS" \
    "$SUBJECT" --outcome approved --post-publish-only >"$std_sentinel_oos" 2>/dev/null
grep -q -- '- \*\*OOS filed\*\*: 3' "$D/final-summary.md" || fail 'sentinel fallback must show OOS count from sentinel when oos-issues-created.md is absent'
grep -Fq -- 'URLs unavailable' "$D/final-summary.md" || fail 'sentinel fallback must note URLs unavailable when using sentinel count'
stdout_starts_with_summary "$D/final-summary.md" "$std_sentinel_oos" 'sentinel fallback stdout/file mismatch'
pass 'sentinel fallback reports OOS count when oos-issues-created.md is absent'
rm -f "$D/oos-issue-sentinel"
: >"$D/oos-issues-created.md"

cat >"$D/accepted-plan-findings-all.md" <<'EOF'
### FINDING_1: Security gap
- **Reviewer**: Cursor-Pragmatic
- **Focus area**: security
- **Concern**: missing auth check

### FINDING_1: Later correctness
- **Reviewer**: Codex-Pragmatic
- **Focus area**: correctness
- **Concern**: missing retry
EOF
std_all="$TMP/std-cumulative.log"
DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-CUMULATIVE" \
    "$SUBJECT" --outcome approved --post-publish-only >"$std_all" 2>/dev/null
grep -q -- '- \*\*Plan review\*\*: 2 ' "$D/final-summary.md" || fail 'plan review line must prefer cumulative accepted findings when present'
pass 'plan review counts cumulative accepted findings'
cat >"$D/accepted-plan-findings-all.md" <<'EOF'
### FINDING_1: Applied correctness
- **Reviewer**: Cursor-Pragmatic
- **Focus area**: correctness
- **Concern**: applied

### FINDING_2: Skipped security
- **Reviewer**: Codex-Pragmatic
- **Focus area**: security
- **Concern**: skipped
EOF
cat >"$D/accepted-plan-findings.md" <<'EOF'
### FINDING_1: Applied correctness
- **Reviewer**: Cursor-Pragmatic
- **Focus area**: correctness
- **Concern**: applied
EOF
cat >"$D/rejected-findings.md" <<'EOF'
### FINDING_2: Skipped security
- **Reviewer**: Codex-Pragmatic
- **Focus area**: security
- **Concern**: skipped
- **Reason not implemented**: rejected by user during one-by-one review
EOF
std_skipped="$TMP/std-cumulative-skipped.log"
DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-CUMULATIVE-SKIPPED" \
    "$SUBJECT" --outcome approved --post-publish-only >"$std_skipped" 2>/dev/null
grep -q -- '- \*\*Plan review\*\*: 1 ' "$D/final-summary.md" || fail 'plan review line must exclude Gate B skipped findings from cumulative count'
pass 'plan review excludes Gate B skipped cumulative findings'
rm -f "$D/rejected-findings.md"
rm -f "$D/voting-tally.md"
std_all_without_tally="$TMP/std-cumulative-no-tally.log"
DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-CUMULATIVE-NO-TALLY" \
    "$SUBJECT" --outcome approved --post-publish-only >"$std_all_without_tally" 2>/dev/null
grep -q -- '- \*\*Plan review\*\*: 2 ' "$D/final-summary.md" || fail 'missing voting tally must not zero cumulative accepted findings'
pass 'plan review counts cumulative accepted findings without voting tally'
rm -f "$D/accepted-plan-findings-all.md"
: >"$D/oos-accepted-design.md"
cat >"$D/accepted-plan-findings.md" <<'EOF'
### FINDING_1: Example
- **Reviewer**: Codex-Pragmatic
- **Focus area**: correctness
- **Concern**: example
EOF
cat >"$D/voting-tally.md" <<'EOF'
# Tally
EOF

pre_std="$TMP/std-pre.log"
DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-PRE" \
    "$SUBJECT" --outcome approved --pre-publish-only >"$pre_std" 2>/dev/null
[ ! -s "$pre_std" ] || fail 'pre-publish path must not print summary to stdout'
grep -Fq -- '- **Cost**:' "$D/final-summary.md" || fail 'pre-publish path missing Cost bullet'
pass 'pre-publish writes file without chat output'

outline_std="$TMP/std-outline.log"
DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-OUTLINE" \
    "$SUBJECT" --outcome cancelled-outline --post-publish-only >"$outline_std" 2>/dev/null
grep -Fq -- '- **Outcome**: cancelled-outline' "$D/final-summary.md" || fail 'cancelled-outline missing Outcome bullet'
grep -Fq -- '- **Cancel site**: Step 1d.7 outline gate' "$D/final-summary.md" || fail 'cancelled-outline missing Step 1d.7 outline phrasing'
outline_sentinel_line=$(grep -nF '<!-- larch:run-summary v=1 -->' "$D/final-summary.md" | head -1 | cut -d: -f1 || true)
outline_note_line=$(grep -nF -- '- **Cancel site**: Step 1d.7 outline gate' "$D/final-summary.md" | head -1 | cut -d: -f1 || true)
[[ -n "$outline_sentinel_line" && -n "$outline_note_line" && "$outline_note_line" -gt "$outline_sentinel_line" ]] \
    || fail 'cancelled-outline note must be appended after sentinel'
# shellcheck disable=SC2016
grep -Fq -- '**ℹ /design auto-report skipped:** operator action or cancellation outcome `cancelled-outline`.' "$outline_std" || fail 'cancelled-outline stdout missing operator-action sidecar'
python3 - "$D/final-summary.md" "$outline_std" <<'PY'
import sys
summary = open(sys.argv[1], encoding="utf-8").read()
stdout = open(sys.argv[2], encoding="utf-8").read()
if not stdout.startswith(summary):
    raise SystemExit("cancelled-outline stdout must start with final-summary body")
PY
pass 'cancelled-outline outcome renders'
rm -f "$D/design-failure-operator-action.env" "$D/design-failure-operator-action-chat.md"

PLUGIN_STUB="$TMP/plugin"
mkdir -p "$PLUGIN_STUB/scripts" "$PLUGIN_STUB/python"
cp "$ROOT/scripts/render-run-summary.sh" "$PLUGIN_STUB/scripts/render-run-summary.sh"
cp "$ROOT/scripts/lib-quiet.sh" "$PLUGIN_STUB/scripts/lib-quiet.sh"
cp "$ROOT/scripts/lib-design-tmpdir.sh" "$PLUGIN_STUB/scripts/lib-design-tmpdir.sh"
cat >"$PLUGIN_STUB/python/cli.py" <<'EOF'
import os, sys
cmd = sys.argv[1:3]
args = sys.argv[3:]
def get_out(argv):
    i = 0
    while i < len(argv):
        if argv[i] == "--output" and i+1 < len(argv):
            return argv[i+1]
        i += 1
    return None
if cmd == ["token", "report"]:
    out = get_out(args)
    if not out: raise SystemExit(2)
    with open(out, "w") as fh:
        fh.write('{"claude":{"totals":{"total":0}},"codex":{"totals":{"total":1050}},"cursor":{"totals":{"total":0}},"BUCKETS_claude":{"input":0,"cache_read":0,"cache_create_5m":0,"cache_create_1h":0,"output":0},"BUCKETS_codex":{"input":100,"cached_input":900,"output":50,"total":1050},"BUCKETS_cursor":{"input":0,"cache_read":0,"output":0}}\n')
elif cmd == ["timing", "report"]:
    out = get_out(args)
    if not out: raise SystemExit(2)
    with open(out, "w") as fh:
        fh.write('{"total_hms":"12s"}\n')
elif cmd == ["token", "cost"]:
    import subprocess
    raise SystemExit(subprocess.call([sys.executable, os.environ["TRFS_REAL_CLI"], "token", "cost", *args]))
elif cmd[:1] == ["run-log"]:
    import subprocess
    raise SystemExit(subprocess.call([sys.executable, os.environ["TRFS_REAL_CLI"], *sys.argv[1:]]))
else:
    print(f"unexpected cli args: {sys.argv[1:]}", file=sys.stderr)
    raise SystemExit(2)
EOF
export TRFS_REAL_CLI="$ROOT/python/cli.py"
chmod +x "$PLUGIN_STUB/scripts/render-run-summary.sh"

printf '%s\n' '{"total_hms":"44s"}' >"$D/timing-report-final.json"
rm -f "$D/timing-report-final.stderr.log" "$D/timing-report-final.failure.log"
std_fresh_timing="$TMP/std-fresh-timing.log"
CLAUDE_PLUGIN_ROOT="$PLUGIN_STUB" DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-REUSE-TIMING" \
    "$SUBJECT" --outcome approved --post-publish-only >"$std_fresh_timing" 2>/dev/null
grep -Fq -- '- **Duration**: 12s' "$D/final-summary.md" || fail 'post-publish path must refresh timing-report-final.json duration'
[[ -f "$D/timing-report-final.stderr.log" ]] || fail 'post-publish timing refresh must capture timing stderr'
stdout_starts_with_summary "$D/final-summary.md" "$std_fresh_timing" 'post-publish timing refresh stdout/file mismatch'
pass 'post-publish refreshes final timing JSON'

std_codex="$TMP/std-codex.log"
CLAUDE_PLUGIN_ROOT="$PLUGIN_STUB" DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-FIX" \
    "$SUBJECT" --outcome approved --post-publish-only >"$std_codex" 2>"$TMP/std-codex.err"
grep -Fq -- '- **Cost**:' "$D/final-summary.md" || fail 'codex buckets run missing Cost bullet'
grep -Fq '💰 TOTAL' "$D/final-summary.md" || fail 'per-agent cost line missing TOTAL marker'
grep -Fq 'Claude $' "$D/final-summary.md" || fail 'per-agent cost line missing Claude slot'
grep -Fq 'Codex $' "$D/final-summary.md" || fail 'per-agent cost line missing Codex slot'
grep -Fq 'Cursor $' "$D/final-summary.md" || fail 'per-agent cost line missing Cursor slot'
grep -Fq 'Tokens: ' "$D/final-summary.md" || fail 'per-agent cost line missing token count'
grep -Fq '💰 TOTAL' "$std_codex" || fail 'stdout per-agent cost line missing TOTAL marker'
grep -Fq 'Claude $' "$std_codex" || fail 'stdout per-agent cost line missing Claude slot'
grep -Fq 'Codex $' "$std_codex" || fail 'stdout per-agent cost line missing Codex slot'
grep -Fq 'Cursor $' "$std_codex" || fail 'stdout per-agent cost line missing Cursor slot'
grep -Fq 'Tokens: ' "$std_codex" || fail 'stdout per-agent cost line missing token count'
stdout_starts_with_summary "$D/final-summary.md" "$std_codex" 'codex buckets stdout/file mismatch'
if grep -Eq 'BLENDED_WARN|blended rate' "$std_codex" "$D/final-summary.md" "$TMP/std-codex.err"; then
    fail 'codex per-bucket design summary must not surface blended-rate warnings'
fi
pass 'codex per-bucket summary omits blended warning'

cat >"$PLUGIN_STUB/scripts/render-run-summary.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
out=""
while [ $# -gt 0 ]; do
    case "$1" in
        --output-file) out=$2; shift 2 ;;
        *) shift ;;
    esac
done
[ -n "$out" ] || exit 2
cat >"$out" <<'OUT'
## /design run RUN-POSTNA — approved

- **Duration**: 3s
- **Cost**: N/A
- **Issue**: N/A
- **Plan review**: N/A
- **OOS filed**: 0
- **Exec issues**: 0
- **Warnings**: 0
- **Run logs**: `larch-logs/design/RUN-POSTNA/`

<!-- larch:run-summary v=1 -->
OUT
EOF
chmod +x "$PLUGIN_STUB/scripts/render-run-summary.sh"
cat >"$D/final-summary.md" <<'EOF'
## /design run RUN-PREKEEP — approved

- **Duration**: 2s
- **Cost**: 💰 TOTAL: $2.34 | Claude $1.00 | Codex $1.34 | Cursor $0.00 | Tokens: 2345
- **Issue**: N/A
- **Plan review**: N/A
- **OOS filed**: 0
- **Exec issues**: 0
- **Warnings**: 0
- **Run logs**: `larch-logs/design/RUN-PREKEEP/`

<!-- larch:run-summary v=1 -->
EOF
std_post_na="$TMP/std-post-na.log"
CLAUDE_PLUGIN_ROOT="$PLUGIN_STUB" DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-POSTNA" \
    "$SUBJECT" --outcome approved --post-publish-only >"$std_post_na" 2>/dev/null
# shellcheck disable=SC2016
grep -Fq '💰 TOTAL: $2.34' "$D/final-summary.md" || fail 'post success with N/A cost must preserve prior usable cost line'
stdout_starts_with_summary "$D/final-summary.md" "$std_post_na" 'post success preserved-cost stdout/file mismatch'
pass 'post success preserves prior usable cost line'

cp "$PLUGIN_STUB/scripts/render-run-summary.sh" "$TMP/render-run-summary.real"
cat >"$PLUGIN_STUB/scripts/render-run-summary.sh" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
chmod +x "$PLUGIN_STUB/scripts/render-run-summary.sh"
cat >"$D/final-summary.md" <<'EOF'
## /design run RUN-PREGOOD — approved

- **Duration**: 9s
- **Cost**: 💰 TOTAL: $1.23 | Claude $0.50 | Codex $0.73 | Cursor $0.00 | Tokens: 1234
- **Issue**: N/A
- **Plan review**: 1 finding
- **OOS filed**: 0
- **Exec issues**: 0
- **Warnings**: 0
- **Run logs**: `larch-logs/design/RUN-PREGOOD/`

<!-- larch:run-summary v=1 -->
EOF
# Reset execution-issues.md: prior runs append token-report/timing-report warnings;
# this sub-case must see exactly 1 new warning from the renderer failure.
: >"$D/execution-issues.md"
std_fb="$TMP/std-fallback.log"
CLAUDE_PLUGIN_ROOT="$PLUGIN_STUB" DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-FB" \
    "$SUBJECT" --outcome approved --post-publish-only >"$std_fb" 2>/dev/null
grep -Fq -- '💰 TOTAL' "$D/final-summary.md" || fail 'renderer-fail post path must preserve prior usable cost line'
grep -Fq -- '## /design run RUN-FB — approved' "$D/final-summary.md" || fail 'renderer-fail post path must refresh title/run id'
grep -Fq -- '**⚠ Degraded fallback' "$D/final-summary.md" || fail 'renderer-fail fallback missing degraded banner'
grep -Fq -- '<!-- larch:final-summary-fallback v1 -->' "$D/final-summary.md" || fail 'renderer-fail fallback missing fallback marker'
grep -Fq -- '<!-- larch:run-summary v=1 -->' "$D/final-summary.md" || fail 'renderer-fail fallback missing run-summary marker'
fb_run_summary_line=$(grep -nF '<!-- larch:run-summary v=1 -->' "$D/final-summary.md" | head -1 | cut -d: -f1 || true)
fb_fallback_line=$(grep -nF '<!-- larch:final-summary-fallback v1 -->' "$D/final-summary.md" | head -1 | cut -d: -f1 || true)
[[ -n "$fb_run_summary_line" && -n "$fb_fallback_line" && "$fb_fallback_line" -gt "$fb_run_summary_line" ]] \
    || fail 'renderer-fail fallback marker must follow run-summary marker'
grep -Fq -- '- **Exec issues**: 0' "$D/final-summary.md" || fail 'renderer-fail post path must refresh exec issue count'
grep -Fq -- '- **Warnings**: 1' "$D/final-summary.md" || fail 'renderer-fail post path must refresh warning count'
fb_nonempty="$(awk 'NF { print; n++; if (n == 3) exit }' "$D/final-summary.md")"
fb_line1="$(printf '%s\n' "$fb_nonempty" | sed -n '1p')"
fb_line2="$(printf '%s\n' "$fb_nonempty" | sed -n '2p')"
fb_line3="$(printf '%s\n' "$fb_nonempty" | sed -n '3p')"
[ "$fb_line1" = '## /design run RUN-FB — approved' ] || fail 'renderer-fail fallback first non-empty line must be heading'
case "$fb_line2" in \*\*⚠\ Degraded\ fallback*) ;; *) fail 'renderer-fail fallback second non-empty line must be degraded banner' ;; esac
case "$fb_line3" in '- **Duration**:'*|'- **Outcome**:'*) ;; *) fail 'renderer-fail fallback third non-empty line must be first schema bullet' ;; esac
if grep -Fq -- '- **PR**:' "$D/final-summary.md"; then fail 'renderer-fail preserved file must not emit PR bullet'; fi
if grep -Fq -- '- **Code review**:' "$D/final-summary.md"; then fail 'renderer-fail preserved file must not emit Code review bullet'; fi
stdout_starts_with_summary "$D/final-summary.md" "$std_fb" 'renderer-fail fallback stdout/file mismatch'
pass 'renderer-fail fallback prints final file once'
std_fb_cancel="$TMP/std-fallback-cancelled.log"
: >"$D/final-summary.md"
CLAUDE_PLUGIN_ROOT="$PLUGIN_STUB" DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-FB-CANCELLED" \
    "$SUBJECT" --outcome cancelled-clarify --post-publish-only >"$std_fb_cancel" 2>/dev/null
grep -Fq -- '**⚠ Degraded fallback' "$D/final-summary.md" || fail 'renderer-fail cancelled fallback missing degraded banner'
grep -Fq -- '- **Outcome**: cancelled-clarify' "$D/final-summary.md" || fail 'renderer-fail cancelled fallback missing Outcome bullet'
grep -Fq -- '- **Cost**: N/A' "$D/final-summary.md" || fail 'renderer-fail cancelled fallback missing Cost N/A'
grep -Fq -- '<!-- larch:run-summary v=1 -->' "$D/final-summary.md" || fail 'renderer-fail cancelled fallback missing run-summary marker'
grep -Fq -- '<!-- larch:final-summary-fallback v1 -->' "$D/final-summary.md" || fail 'renderer-fail cancelled fallback missing fallback marker'
grep -Fq -- '- **Cost**: N/A' "$std_fb_cancel" || fail 'renderer-fail cancelled stdout missing Cost N/A'
fb_cancel_nonempty="$(awk 'NF { print; n++; if (n == 3) exit }' "$D/final-summary.md")"
fb_cancel_line1="$(printf '%s\n' "$fb_cancel_nonempty" | sed -n '1p')"
fb_cancel_line2="$(printf '%s\n' "$fb_cancel_nonempty" | sed -n '2p')"
fb_cancel_line3="$(printf '%s\n' "$fb_cancel_nonempty" | sed -n '3p')"
[ "$fb_cancel_line1" = '## /design run RUN-FB-CANCELLED — cancelled-clarify' ] || fail 'renderer-fail cancelled fallback first non-empty line must be heading'
case "$fb_cancel_line2" in \*\*⚠\ Degraded\ fallback*) ;; *) fail 'renderer-fail cancelled fallback second non-empty line must be degraded banner' ;; esac
[ "$fb_cancel_line3" = '- **Outcome**: cancelled-clarify' ] || fail 'renderer-fail cancelled fallback third non-empty line must be Outcome bullet'
fb_cancel_run_summary_line=$(grep -nF '<!-- larch:run-summary v=1 -->' "$D/final-summary.md" | head -1 | cut -d: -f1 || true)
fb_cancel_fallback_line=$(grep -nF '<!-- larch:final-summary-fallback v1 -->' "$D/final-summary.md" | head -1 | cut -d: -f1 || true)
[[ -n "$fb_cancel_run_summary_line" && -n "$fb_cancel_fallback_line" && "$fb_cancel_fallback_line" -gt "$fb_cancel_run_summary_line" ]] \
    || fail 'renderer-fail cancelled fallback marker must follow run-summary marker'
stdout_starts_with_summary "$D/final-summary.md" "$std_fb_cancel" 'renderer-fail cancelled fallback stdout/file mismatch'
std_fb_skip="$TMP/std-fallback-publish-skipped.log"
: >"$D/final-summary.md"
CLAUDE_PLUGIN_ROOT="$PLUGIN_STUB" DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="" \
    "$SUBJECT" --outcome publish-skipped --post-publish-only >"$std_fb_skip" 2>/dev/null
grep -Fq -- '**⚠ Degraded fallback' "$D/final-summary.md" || fail 'renderer-fail publish-skipped fallback missing degraded banner'
grep -Fq -- '- **Outcome**: publish-skipped' "$D/final-summary.md" || fail 'renderer-fail publish-skipped fallback missing Outcome bullet'
grep -Fq -- '- **Publish**: skipped — no SESSION_ID / run-log; the plan was written to the issue.' "$D/final-summary.md" || fail 'renderer-fail publish-skipped fallback missing publish note'
# shellcheck disable=SC2016 # literal markdown with backticks is intentionally single-quoted.
grep -Fq -- '- **Run logs**: `N/A`' "$D/final-summary.md" || fail 'renderer-fail publish-skipped fallback must keep Run logs N/A'
if grep -Fq 'Publish recovery' "$D/final-summary.md"; then fail 'renderer-fail publish-skipped fallback must not emit recovery prose'; fi
if grep -Fq 'Log recovery' "$D/final-summary.md"; then fail 'renderer-fail publish-skipped fallback must not emit log recovery prose'; fi
if grep -Fq 'larch-logs/design/unknown/' "$D/final-summary.md"; then fail 'renderer-fail publish-skipped fallback must not synthesize unknown run-log path'; fi
stdout_starts_with_summary "$D/final-summary.md" "$std_fb_skip" 'renderer-fail publish-skipped fallback stdout/file mismatch'
std_fb_co="$TMP/std-fallback-cancelled-outline.log"
: >"$D/final-summary.md"
CLAUDE_PLUGIN_ROOT="$PLUGIN_STUB" DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-FB-CO" \
    "$SUBJECT" --outcome cancelled-outline --post-publish-only >"$std_fb_co" 2>/dev/null
grep -Fq -- '**⚠ Degraded fallback' "$D/final-summary.md" || fail 'renderer-fail cancelled-outline fallback missing degraded banner'
grep -Fq -- '<!-- larch:final-summary-fallback v1 -->' "$D/final-summary.md" || fail 'renderer-fail cancelled-outline fallback missing fallback marker'
grep -Fq -- '<!-- larch:run-summary v=1 -->' "$D/final-summary.md" || fail 'renderer-fail cancelled-outline fallback missing run-summary marker'
grep -Fq -- '- **Cancel site**: Step 1d.7 outline gate' "$D/final-summary.md" || fail 'renderer-fail cancelled-outline fallback missing Cancel site bullet'
fb_co_fallback_line=$(grep -nF '<!-- larch:final-summary-fallback v1 -->' "$D/final-summary.md" | head -1 | cut -d: -f1 || true)
fb_co_cancel_line=$(grep -nF -- '- **Cancel site**: Step 1d.7 outline gate' "$D/final-summary.md" | head -1 | cut -d: -f1 || true)
[[ -n "$fb_co_fallback_line" && -n "$fb_co_cancel_line" && "$fb_co_cancel_line" -gt "$fb_co_fallback_line" ]] \
    || fail 'renderer-fail cancelled-outline Cancel site bullet must follow fallback marker'
pass 'renderer-fail cancelled-outline fallback preserves marker ordering before Cancel site'
rm -f "$PLUGIN_STUB/python/cli.py"
: >"$D/execution-issues.md"
std_fb_nowarn="$TMP/std-fallback-no-warning.log"
CLAUDE_PLUGIN_ROOT="$PLUGIN_STUB" DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-FB-NOWARN" \
    "$SUBJECT" --outcome approved --post-publish-only >"$std_fb_nowarn" 2>/dev/null
grep -Fq -- '**⚠ Degraded fallback — full renderer failed; warning could not be recorded in execution issues.**' "$D/final-summary.md" \
    || fail 'renderer-fail fallback must disclose missing warning record'
grep -Fq -- '- **Warnings**: 0' "$D/final-summary.md" || fail 'renderer-fail fallback without warning record must keep warning count at 0'
stdout_starts_with_summary "$D/final-summary.md" "$std_fb_nowarn" 'renderer-fail no-warning fallback stdout/file mismatch'
cp "$TMP/render-run-summary.real" "$PLUGIN_STUB/scripts/render-run-summary.sh"
chmod +x "$PLUGIN_STUB/scripts/render-run-summary.sh"

PLUGIN_FAILTOK="$TMP/plugin-failtok"
mkdir -p "$PLUGIN_FAILTOK/scripts" "$PLUGIN_FAILTOK/python"
cp "$ROOT/scripts/render-run-summary.sh" "$PLUGIN_FAILTOK/scripts/render-run-summary.sh"
cp "$ROOT/scripts/lib-quiet.sh" "$PLUGIN_FAILTOK/scripts/lib-quiet.sh"
cp "$ROOT/scripts/lib-design-tmpdir.sh" "$PLUGIN_FAILTOK/scripts/lib-design-tmpdir.sh"
cat >"$PLUGIN_FAILTOK/python/cli.py" <<'EOF'
import os, sys
cmd = sys.argv[1:3]
args = sys.argv[3:]
def get_out(argv):
    i = 0
    while i < len(argv):
        if argv[i] == "--output" and i+1 < len(argv): return argv[i+1]
        i += 1
    return None
if cmd == ["token", "report"]:
    print("token report unavailable", file=sys.stderr)
    raise SystemExit(9)
elif cmd == ["timing", "report"]:
    out = get_out(args)
    if not out: raise SystemExit(2)
    with open(out, "w") as fh: fh.write('{"total_hms":"1s"}\n')
elif cmd == ["token", "cost"]:
    pass
elif cmd[:1] == ["run-log"]:
    import subprocess
    raise SystemExit(subprocess.call([sys.executable, os.environ["TRFS_REAL_CLI"], *sys.argv[1:]]))
else:
    print(f"unexpected cli args: {sys.argv[1:]}", file=sys.stderr)
    raise SystemExit(2)
EOF
chmod +x "$PLUGIN_FAILTOK/scripts/"*.sh
FAILTOK_RENDER_STUB="$PLUGIN_FAILTOK/scripts/render-run-summary.sh"
mv "$FAILTOK_RENDER_STUB" "$PLUGIN_FAILTOK/scripts/render-run-summary.real"
cat >"$FAILTOK_RENDER_STUB" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >"${RENDER_ARGS_LOG:?}"
out=""
while [ $# -gt 0 ]; do
  case "$1" in
    --output-file) out=$2; shift 2 ;;
    *)
      if [ "$#" -ge 2 ] && [[ "$2" != --* ]]; then
        shift 2
      else
        shift
      fi
      ;;
  esac
done
printf '%s\n' '## /design run RUN-FAILTOK — approved' >"$out"
printf '%s\n' '' >>"$out"
printf '%s\n' '- **Cost**: N/A' >>"$out"
printf '%s\n' '' >>"$out"
printf '%s\n' '<!-- larch:run-summary v=1 -->' >>"$out"
EOF
chmod +x "$FAILTOK_RENDER_STUB"
std_failtok="$TMP/std-failtok.log"
RENDER_ARGS_LOG="$TMP/render-args.log" CLAUDE_PLUGIN_ROOT="$PLUGIN_FAILTOK" DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-FAILTOK" \
    "$SUBJECT" --outcome approved --post-publish-only >"$std_failtok" 2>/dev/null
grep -Fq -- '- **Cost**: N/A' "$D/final-summary.md" || fail 'token-data-missing path missing Cost N/A'
if grep -Fq "Claude \$0.00, Codex \$0.00, Cursor \$0.00" "$D/final-summary.md"; then
    fail 'token-data-missing path rendered misleading zero-dollar cost'
fi
grep -Fq -- '--cost-unavailable' "$TMP/render-args.log" || fail 'token-data-missing path must pass --cost-unavailable to renderer'
pass 'token-data-missing path renders Cost N/A'

PLUGIN_BADJSON="$TMP/plugin-badjson"
mkdir -p "$PLUGIN_BADJSON/scripts" "$PLUGIN_BADJSON/python"
cp "$ROOT/scripts/render-run-summary.sh" "$PLUGIN_BADJSON/scripts/render-run-summary.sh"
cp "$ROOT/scripts/lib-quiet.sh" "$PLUGIN_BADJSON/scripts/lib-quiet.sh"
cp "$ROOT/scripts/lib-design-tmpdir.sh" "$PLUGIN_BADJSON/scripts/lib-design-tmpdir.sh"
cat >"$PLUGIN_BADJSON/python/cli.py" <<'EOF'
import os, sys
cmd = sys.argv[1:3]
args = sys.argv[3:]
def get_out(argv):
    i = 0
    while i < len(argv):
        if argv[i] == "--output" and i+1 < len(argv): return argv[i+1]
        i += 1
    return None
if cmd == ["token", "report"]:
    out = get_out(args)
    if not out: raise SystemExit(2)
    with open(out, "w") as fh: fh.write('{not-json\n')
elif cmd == ["timing", "report"]:
    out = get_out(args)
    if not out: raise SystemExit(2)
    with open(out, "w") as fh: fh.write('{"total_hms":"2s"}\n')
elif cmd == ["token", "cost"]:
    pass
elif cmd[:1] == ["run-log"]:
    import subprocess
    raise SystemExit(subprocess.call([sys.executable, os.environ["TRFS_REAL_CLI"], *sys.argv[1:]]))
else:
    print(f"unexpected cli args: {sys.argv[1:]}", file=sys.stderr)
    raise SystemExit(2)
EOF
chmod +x "$PLUGIN_BADJSON/scripts/"*.sh
BADJSON_RENDER_STUB="$PLUGIN_BADJSON/scripts/render-run-summary.sh"
mv "$BADJSON_RENDER_STUB" "$PLUGIN_BADJSON/scripts/render-run-summary.real"
cat >"$BADJSON_RENDER_STUB" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >"${BADJSON_RENDER_ARGS_LOG:?}"
out=""
while [ $# -gt 0 ]; do
  case "$1" in
    --output-file) out=$2; shift 2 ;;
    *)
      if [ "$#" -ge 2 ] && [[ "$2" != --* ]]; then
        shift 2
      else
        shift
      fi
      ;;
  esac
done
printf '%s\n' '## /design run RUN-BADJSON — approved' >"$out"
printf '%s\n' '' >>"$out"
printf '%s\n' '- **Cost**: N/A' >>"$out"
printf '%s\n' '' >>"$out"
printf '%s\n' '<!-- larch:run-summary v=1 -->' >>"$out"
EOF
chmod +x "$BADJSON_RENDER_STUB"
std_badjson="$TMP/std-badjson.log"
BADJSON_RENDER_ARGS_LOG="$TMP/render-badjson-args.log" CLAUDE_PLUGIN_ROOT="$PLUGIN_BADJSON" DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-BADJSON" \
    "$SUBJECT" --outcome approved --post-publish-only >"$std_badjson" 2>/dev/null
grep -Fq -- '- **Cost**: N/A' "$D/final-summary.md" || fail 'malformed token JSON path missing Cost N/A'
if grep -Fq "Claude \$0.00, Codex \$0.00, Cursor \$0.00" "$D/final-summary.md"; then
    fail 'malformed token JSON path rendered misleading zero-dollar cost'
fi
grep -Fq -- '--cost-unavailable' "$TMP/render-badjson-args.log" || fail 'malformed token JSON path must pass --cost-unavailable to renderer'
pass 'malformed token JSON renders Cost N/A'

NOTEARG_PLUGIN="$TMP/plugin-notearg"
mkdir -p "$NOTEARG_PLUGIN/scripts" "$NOTEARG_PLUGIN/python"
cp "$ROOT/scripts/lib-quiet.sh" "$NOTEARG_PLUGIN/scripts/lib-quiet.sh"
cp "$ROOT/scripts/lib-design-tmpdir.sh" "$NOTEARG_PLUGIN/scripts/lib-design-tmpdir.sh"
cat >"$NOTEARG_PLUGIN/python/cli.py" <<'EOF'
import os, sys
cmd = sys.argv[1:3]
args = sys.argv[3:]
def get_out(argv):
    i = 0
    while i < len(argv):
        if argv[i] == "--output" and i+1 < len(argv): return argv[i+1]
        i += 1
    return None
if cmd == ["token", "report"]:
    out = get_out(args)
    if not out: raise SystemExit(2)
    with open(out, "w") as fh: fh.write('{"claude":{"totals":{"total":0}},"codex":{"totals":{"total":0}},"cursor":{"totals":{"total":0}}}\n')
elif cmd == ["timing", "report"]:
    out = get_out(args)
    if not out: raise SystemExit(2)
    with open(out, "w") as fh: fh.write('{"total_hms":"4s"}\n')
elif cmd == ["token", "cost"]:
    pass
elif cmd[:1] == ["run-log"]:
    import subprocess
    raise SystemExit(subprocess.call([sys.executable, os.environ["TRFS_REAL_CLI"], *sys.argv[1:]]))
else:
    print(f"unexpected cli args: {sys.argv[1:]}", file=sys.stderr)
    raise SystemExit(2)
EOF
cat >"$NOTEARG_PLUGIN/scripts/render-run-summary.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >"${NOTEARG_LOG:?}"
out=""
while [ $# -gt 0 ]; do
  case "$1" in
    --output-file) out=$2; shift 2 ;;
    *)
      if [ "$#" -ge 2 ] && [[ "$2" != --* ]]; then
        shift 2
      else
        shift
      fi
      ;;
  esac
done
[ -n "$out" ] || exit 2
printf '%s\n' '## /design run RUN-NOTEARG — approved' >"$out"
printf '%s\n' '' >>"$out"
printf '%s\n' '- **Cost**: N/A' >>"$out"
printf '%s\n' '' >>"$out"
printf '%s\n' '<!-- larch:run-summary v=1 -->' >>"$out"
EOF
chmod +x "$NOTEARG_PLUGIN/scripts/"*.sh
printf '%s\n' '- **Cancel site**: stale' >"$D/final-summary-notes.md"
NOTEARG_LOG="$TMP/render-notearg.log" CLAUDE_PLUGIN_ROOT="$NOTEARG_PLUGIN" DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-NOTEARG" \
    "$SUBJECT" --outcome approved --post-publish-only >/dev/null 2>&1
if grep -Fq -- '--note-lines-file' "$TMP/render-notearg.log"; then
    fail 'non-cancelled outcomes must not pass stale note file to renderer'
fi
pass 'non-cancelled outcomes omit stale note-file arg'

EMPTY_MODE_D="$TMP/design-empty-mode"
mkdir -p "$EMPTY_MODE_D"
: >"$EMPTY_MODE_D/execution-issues.md"
SUMMARY_OUTCOME=cancelled-sprawl
DESIGN_TMPDIR="$EMPTY_MODE_D" ISSUE_NUMBER="" SESSION_ID="RUN-EMPTY-MODE" \
    "$SUBJECT" --outcome "$SUMMARY_OUTCOME" --mode N/A --post-publish-only >"$TMP/std-empty-mode.log" 2>/dev/null
pass 'cancelled-title-filter outcome'

DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-FIX" \
    "$SUBJECT" --outcome approved-partition --post-publish-only >/dev/null 2>&1
grep -Fq '## /design run RUN-FIX — approved-partition' "$D/final-summary.md" || fail 'approved-partition title missing'
pass 'approved-partition outcome'

DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-FIX" \
    "$SUBJECT" --outcome cancelled-decompose --post-publish-only >/dev/null 2>&1
grep -Fq '## /design run RUN-FIX — cancelled-decompose' "$D/final-summary.md" || fail 'cancelled-decompose title missing'
grep -Fq -- '- **Outcome**: cancelled-decompose' "$D/final-summary.md" || fail 'missing cancelled-decompose outcome bullet'
pass 'cancelled-decompose outcome'


failed_publish_stdout="$TMP/std-failed-publish-recovery.log"
DESIGN_LOG_PR_NUMBER=456 \
DESIGN_LOG_PR_URL=https://github.com/owner/repo/pull/456 \
DESIGN_LOG_RECOVERY_BRANCH=larch-log-design-RUNRECOVERY \
RENAMED=true \
DESIGNED_ADMISSION_READY=true \
DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-RECOVERY" \
    "$SUBJECT" --outcome failed-publish --post-publish-only >"$failed_publish_stdout" 2>/dev/null
grep -Fq -- "- **Log recovery branch**: \`larch-log-design-RUNRECOVERY\`" "$D/final-summary.md" || fail 'failed-publish missing recovery branch'
grep -Fq -- '- **Log flush PR**: #456 — https://github.com/owner/repo/pull/456' "$D/final-summary.md" || fail 'failed-publish missing flush PR'
grep -Fq -- '- **Publish recovery**: design logs did not finish publishing and the issue is [DESIGNED]; retry log publish from the preserved design tmpdir before starting /implement when the session may contain secrets.' "$D/final-summary.md" || fail 'failed-publish missing admission-ready recovery guidance'
stdout_starts_with_summary "$D/final-summary.md" "$failed_publish_stdout" 'failed-publish recovery stdout/file mismatch'
failed_publish_not_ready_stdout="$TMP/std-failed-publish-not-ready.log"
DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-RECOVERY" \
    "$SUBJECT" --outcome failed-publish --post-publish-only >"$failed_publish_not_ready_stdout" 2>/dev/null
grep -Fq -- '- **Publish recovery**: design logs did not finish publishing and the [DESIGNED] rename was not confirmed; fix the issue title before /implement, then retry logs manually from the preserved design tmpdir.' "$D/final-summary.md" || fail 'failed-publish missing rename-not-confirmed recovery guidance'
stdout_starts_with_summary "$D/final-summary.md" "$failed_publish_not_ready_stdout" 'failed-publish not-ready stdout/file mismatch'
failed_publish_diagram_stdout="$TMP/std-failed-publish-diagram.log"
RENAMED=true UPSERT_RAN=true UPSERT_STATUS=failed \
DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-RECOVERY" \
    "$SUBJECT" --outcome failed-publish --post-publish-only >"$failed_publish_diagram_stdout" 2>/dev/null
grep -Fq -- "- **Publish recovery**: design logs did not finish publishing and the issue title is [DESIGNED], but the diagram comment was not confirmed; verify or repair \`larch:diagrams\` before starting /implement, then retry logs manually from the preserved design tmpdir." "$D/final-summary.md" || fail 'failed-publish missing diagram recovery guidance'
stdout_starts_with_summary "$D/final-summary.md" "$failed_publish_diagram_stdout" 'failed-publish diagram stdout/file mismatch'
unset DESIGN_LOG_PR_NUMBER DESIGN_LOG_PR_URL DESIGN_LOG_RECOVERY_BRANCH RENAMED DESIGNED_ADMISSION_READY UPSERT_RAN UPSERT_STATUS
pass 'failed-publish recovery bullets'

cp "$ROOT/scripts/render-run-summary.sh" "$PLUGIN_STUB/scripts/render-run-summary.sh"
chmod +x "$PLUGIN_STUB/scripts/render-run-summary.sh"
publish_skipped_stdout="$TMP/std-publish-skipped.log"
CLAUDE_PLUGIN_ROOT="$PLUGIN_STUB" DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID=""     "$SUBJECT" --outcome publish-skipped --post-publish-only >"$publish_skipped_stdout" 2>/dev/null
grep -Fq -- '- **Outcome**: publish-skipped' "$D/final-summary.md" || fail 'publish-skipped missing Outcome bullet'
grep -Fq -- '- **Publish**: skipped — no SESSION_ID / run-log; the plan was written to the issue.' "$D/final-summary.md" || fail 'publish-skipped missing publish note'
# shellcheck disable=SC2016 # literal markdown with backticks is intentionally single-quoted.
grep -Fq -- '- **Run logs**: `N/A`' "$D/final-summary.md" || fail 'publish-skipped Run logs must be N/A'
if grep -Fq 'Publish recovery' "$D/final-summary.md"; then fail 'publish-skipped must not emit failed-publish recovery prose'; fi
if grep -Fq 'larch-logs/design/unknown/' "$D/final-summary.md"; then fail 'publish-skipped must not synthesize unknown run-log path'; fi
stdout_starts_with_summary "$D/final-summary.md" "$publish_skipped_stdout" 'publish-skipped stdout/file mismatch'
pass 'publish-skipped primary bullets'

for summary_outcome in \
    approved \
    approved-partition \
    cancelled-clarify \
    cancelled-already-planned \
    cancelled-title-filter \
    cancelled-sprawl \
    cancelled-plan-size \
    cancelled-decompose \
    cancelled-outline \
    failed-plan-write \
    failed-publish \
    failed-postplan \
    failed-clarify \
    failed-judge-panel \
    failed-publish-tail \
    publish-skipped
do
    session="RUN-MATRIX-${summary_outcome}"
    matrix_stdout="$TMP/std-matrix-${summary_outcome}.log"
    CLAUDE_PLUGIN_ROOT="$PLUGIN_STUB" DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="$session" \
        "$SUBJECT" --outcome "$summary_outcome" --post-publish-only >"$matrix_stdout" 2>/dev/null
    grep -Fq -- '- **Cost**:' "$D/final-summary.md" || fail "matrix $summary_outcome missing Cost bullet"
    grep -Fq "<!-- larch:run-summary v=1 -->" "$D/final-summary.md" || fail "matrix $summary_outcome missing sentinel"
    grep -Fq "## /design run $session — $summary_outcome" "$D/final-summary.md" || fail "matrix $summary_outcome missing title"
    grep -Fq -- '- **Cost**:' "$matrix_stdout" || fail "matrix $summary_outcome stdout missing Cost bullet"
    grep -Fq "<!-- larch:run-summary v=1 -->" "$matrix_stdout" || fail "matrix $summary_outcome stdout missing sentinel"
    stdout_starts_with_summary "$D/final-summary.md" "$matrix_stdout" "matrix $summary_outcome stdout/file mismatch"
    if [[ "$summary_outcome" == approved || "$summary_outcome" == approved-partition ]]; then
        if grep -Fq -- '- **Outcome**:' "$D/final-summary.md"; then
            fail "matrix $summary_outcome must omit Outcome bullet"
        fi
    else
        grep -Fq -- "- **Outcome**: $summary_outcome" "$D/final-summary.md" || fail "matrix $summary_outcome missing Outcome bullet"
    fi
done
pass 'eighteen-outcome post-publish matrix'

# --- report-gate KV isolation: helper stdout stays in sidecar log ---
GATE_D="$TMP/design-gate-kv"
mkdir -p "$GATE_D"
: >"$GATE_D/execution-issues.md"
cat >"$GATE_D/run-params.json" <<'JSON'
JSON
cat >"$GATE_D/voting-tally.md" <<'EOF'
# Tally
EOF
: >"$GATE_D/accepted-plan-findings.md"
: >"$GATE_D/oos-accepted-design.md"
mkdir -p "$PLUGIN_STUB/skills/design/scripts"
cat >"$PLUGIN_STUB/skills/design/scripts/design-failure-report.sh" <<'EOF'
#!/usr/bin/env bash
printf 'DESIGN_FAILURE_REPORT_DECISION=skip\n'
printf 'DESIGN_FAILURE_REPORT_KV_ISOLATION_PROBE=distinctive-kv-42\n'
EOF
chmod +x "$PLUGIN_STUB/skills/design/scripts/design-failure-report.sh"
gate_kv_stdout="$TMP/std-gate-kv.log"
CLAUDE_PLUGIN_ROOT="$PLUGIN_STUB" DESIGN_TMPDIR="$GATE_D" ISSUE_NUMBER="" SESSION_ID="RUN-GATE-KV" \
    "$SUBJECT" --outcome approved --post-publish-only >"$gate_kv_stdout" 2>/dev/null
grep -Fq 'DESIGN_FAILURE_REPORT_KV_ISOLATION_PROBE=distinctive-kv-42' "$GATE_D/design-failure-report.stdout.log" \
    || fail 'report gate KV must land in sidecar stdout log'
if grep -Fq 'DESIGN_FAILURE_REPORT_KV_ISOLATION_PROBE' "$gate_kv_stdout"; then
    fail 'report gate KV must not leak into post-publish stdout'
fi
stdout_starts_with_summary "$GATE_D/final-summary.md" "$gate_kv_stdout" 'report gate KV isolation stdout/file mismatch'
pass 'report-gate helper KVs isolated to sidecar log'

# --- fallback chat-print sidecar after summary body ---
GATE_FB_D="$TMP/design-gate-fallback-chat"
mkdir -p "$GATE_FB_D"
: >"$GATE_FB_D/execution-issues.md"
cat >"$GATE_FB_D/run-params.json" <<'JSON'
JSON
cat >"$GATE_FB_D/voting-tally.md" <<'EOF'
# Tally
EOF
: >"$GATE_FB_D/accepted-plan-findings.md"
: >"$GATE_FB_D/oos-accepted-design.md"
cat >"$PLUGIN_STUB/skills/design/scripts/design-failure-report.sh" <<'EOF'
#!/usr/bin/env bash
cat >"$DESIGN_TMPDIR/design-failure-chat-print.md" <<'CHAT'
### [Bug] /design report fallback required

Fallback sidecar probe for harness.
CHAT
printf 'DESIGN_FAILURE_REPORT_DECISION=fallback-print-required\n'
printf 'DESIGN_FAILURE_REPORT_REASON=compose-probe\n'
EOF
chmod +x "$PLUGIN_STUB/skills/design/scripts/design-failure-report.sh"
gate_fb_stdout="$TMP/std-gate-fallback-chat.log"
CLAUDE_PLUGIN_ROOT="$PLUGIN_STUB" DESIGN_TMPDIR="$GATE_FB_D" ISSUE_NUMBER="" SESSION_ID="RUN-GATE-FB" \
    "$SUBJECT" --outcome failed-clarify --post-publish-only >"$gate_fb_stdout" 2>/dev/null
grep -Fq 'Fallback sidecar probe for harness.' "$gate_fb_stdout" \
    || fail 'fallback chat-print sidecar must appear after summary body in stdout'
if grep -Fq 'Fallback sidecar probe for harness.' "$GATE_FB_D/final-summary.md"; then
    fail 'fallback chat-print must stay outside final-summary.md body'
fi
stdout_starts_with_summary "$GATE_FB_D/final-summary.md" "$gate_fb_stdout" 'fallback chat-print sidecar stdout/file mismatch'
pass 'fallback chat-print sidecar prints after summary body'

# --- pre-publish must not invoke report gate ---
pre_gate_d="$TMP/design-pre-gate"
mkdir -p "$pre_gate_d"
: >"$pre_gate_d/execution-issues.md"
cat >"$pre_gate_d/run-params.json" <<'JSON'
JSON
cat >"$pre_gate_d/voting-tally.md" <<'EOF'
# Tally
EOF
: >"$pre_gate_d/accepted-plan-findings.md"
: >"$pre_gate_d/oos-accepted-design.md"
rm -f "$pre_gate_d/design-failure-report.stdout.log"
CLAUDE_PLUGIN_ROOT="$PLUGIN_STUB" DESIGN_TMPDIR="$pre_gate_d" ISSUE_NUMBER="" SESSION_ID="RUN-PRE-GATE" \
    "$SUBJECT" --outcome approved --pre-publish-only >/dev/null 2>&1
if [ -f "$pre_gate_d/design-failure-report.stdout.log" ]; then
    fail 'pre-publish path must not run design-failure-report gate'
fi
pass 'pre-publish path skips report gate'

# --- gate audit appends refresh warning counts before render ---
audit_d="$TMP/design-gate-audit"
mkdir -p "$audit_d"
: >"$audit_d/execution-issues.md"
cat >"$audit_d/run-params.json" <<'JSON'
JSON
cat >"$audit_d/voting-tally.md" <<'EOF'
# Tally
EOF
: >"$audit_d/accepted-plan-findings.md"
: >"$audit_d/oos-accepted-design.md"
env -u CLAUDE_PLUGIN_ROOT "$ROOT/skills/design/scripts/design-stage-terminal-state.sh" \
    --design-tmpdir "$audit_d" --outcome failed-clarify --step clarify --phase clarify-loop \
    --site clarify-loop --trigger failed --bail-reason clarify-hard-halt --exit-code 1 \
    --source-script clarify-loop --summary-outcome failed-clarify >/dev/null
audit_stdout="$TMP/std-gate-audit.log"
CLAUDE_PLUGIN_ROOT="$ROOT" DESIGN_TMPDIR="$audit_d" ISSUE_NUMBER="" SESSION_ID="RUN-GATE-AUDIT" \
    "$SUBJECT" --outcome failed-publish --post-publish-only >"$audit_stdout" 2>/dev/null
grep -Fq '### Warnings' "$audit_d/execution-issues.md" || fail 'invalid terminal state gate must append execution-issues audit'
grep -qE -- '\- \*\*Warnings\*\*: [1-9]' "$audit_d/final-summary.md" || fail 'warning count must refresh after gate audit before render'
pass 'report gate audit refreshes warning counts before render'

grep -Fq -- '--redact' "$ROOT/skills/design/scripts/render-final-summary.sh" || fail 'render-final-summary append_render_warning must redact stderr'
pass 'render-final-summary append warning redacts stderr'

set +e
DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-FIX" \
    "$SUBJECT" --outcome cancelled-plan-size-soft --post-publish-only >/dev/null 2>&1
rc=$?
set -e
test "$rc" -eq 2 || fail 'invalid outcome must exit 2'
pass 'invalid outcome rejected'

WARN_D="$TMP/design-warning-count"
mkdir -p "$WARN_D"
cat >"$WARN_D/run-params.json" <<'JSON'
JSON
cat >"$WARN_D/accepted-plan-findings.md" <<'EOF'
### FINDING_1: Example
- **Reviewer**: Codex-Pragmatic
- **Focus area**: correctness
- **Concern**: example
EOF
: >"$WARN_D/oos-accepted-design.md"
: >"$WARN_D/oos-issues-created.md"
cat >"$WARN_D/execution-issues.md" <<'EOF'
### Warnings

- **Non-step warning**:
  ```
- **Diagnostic bullet**: not an issue entry
  ```
EOF
DESIGN_TMPDIR="$WARN_D" ISSUE_NUMBER="" SESSION_ID="RUN-WARN-COUNT" IMPLEMENT_TMPDIR="" \
    "$SUBJECT" --outcome approved --post-publish-only >/dev/null 2>/dev/null
grep -Fq -- '- **Warnings**: 2' "$WARN_D/final-summary.md" || fail 'non-step warning entry must count once'
pass 'non-step warning entry count ignores fenced diagnostics'


BG_D="$TMP/design-bg-poll"
mkdir -p "$BG_D"
cat >"$BG_D/run-params.json" <<'JSON'
JSON
cat >"$BG_D/accepted-plan-findings.md" <<'EOF'
### FINDING_1: Example
- **Reviewer**: Codex-Pragmatic
- **Focus area**: correctness
- **Concern**: example
EOF
: >"$BG_D/oos-accepted-design.md"
: >"$BG_D/execution-issues.md"
: >"$BG_D/oos-issues-created.md"
std_bg_none="$TMP/std-bg-none.log"
DESIGN_TMPDIR="$BG_D" ISSUE_NUMBER="" SESSION_ID="RUN-BG-NONE" \
    "$SUBJECT" --outcome approved --post-publish-only >"$std_bg_none" 2>/dev/null
if grep -Fq -- '- **Blocked polling attempts**:' "$BG_D/final-summary.md"; then
    fail 'missing denial sidecar must not render blocked-polling note'
fi
pass 'no denial sidecar omits blocked-polling note'

printf '0\n' >"$BG_D/bg-poll-guard-denials.count"
std_bg_zero="$TMP/std-bg-zero.log"
DESIGN_TMPDIR="$BG_D" ISSUE_NUMBER="" SESSION_ID="RUN-BG-ZERO" \
    "$SUBJECT" --outcome approved --post-publish-only >"$std_bg_zero" 2>/dev/null
if grep -Fq -- '- **Blocked polling attempts**:' "$BG_D/final-summary.md"; then
    fail 'zero denial sidecar must not render blocked-polling note'
fi
pass 'zero denial sidecar omits blocked-polling note'

: >"$BG_D/execution-issues.md"
printf '3\n' >"$BG_D/bg-poll-guard-denials.count"
std_bg_positive="$TMP/std-bg-positive.log"
DESIGN_TMPDIR="$BG_D" ISSUE_NUMBER="" SESSION_ID="RUN-BG-POSITIVE" IMPLEMENT_TMPDIR="" \
    "$SUBJECT" --outcome approved --post-publish-only >"$std_bg_positive" 2>/dev/null
grep -Fq -- '- **Blocked polling attempts**: 3' "$BG_D/final-summary.md" || fail 'positive denial sidecar must render blocked-polling note'
grep -Fq -- '- **Warnings**: 2' "$BG_D/final-summary.md" || fail 'positive denial sidecar must increase warning count'
grep -Fq -- 'Blocked polling attempts: 3' "$BG_D/execution-issues.md" || fail 'positive denial sidecar must append warning evidence'
cmp -s "$BG_D/final-summary.md" "$std_bg_positive" || fail 'blocked-polling stdout/file mismatch'
pass 'positive denial sidecar records warning and note'

RPD_D="$TMP/design-rpd"
mkdir -p "$RPD_D/plan-review/round-1"
cat >"$RPD_D/run-params.json" <<'JSON'
JSON
cat >"$RPD_D/voting-tally.md" <<'EOF'
# Tally
EOF
cat >"$RPD_D/accepted-plan-findings.md" <<'EOF'
### FINDING_D1: First accepted
- **Reviewer**: Claude-Generic
- **Focus area**: correctness
- **Concern**: first concern

### FINDING_D2: Second accepted
- **Reviewer**: Claude-Generic
- **Focus area**: correctness
- **Concern**: second concern
EOF
: >"$RPD_D/oos-accepted-design.md"
: >"$RPD_D/execution-issues.md"
printf 'reviewer output\n' >"$RPD_D/claude-plan-generic-output.txt"
printf '{"slot":"claude-plan-generic","tool":"claude_sub","output":"%s"}\n' \
    "$RPD_D/claude-plan-generic-output.txt" >"$RPD_D/plan-review/round-1/plan-review-slots.ndjson"
cp "$RPD_D/plan-review/round-1/plan-review-slots.ndjson" "$RPD_D/plan-review/round-1/panel-manifest.ndjson"
cat >"$RPD_D/plan-review/round-1/round-meta.json" <<'JSON'
{"tally":{"ACCEPTED_COUNT":"2","REJECTED_COUNT":"1","EXONERATED_COUNT":"0","NEUTRAL_COUNT":"1","OOS_ACCEPTED_COUNT":"1","OOS_REJECTED_COUNT":"1"},"summary":{"panel":{"total_slot_count":1}},"collector":"TOOL=unknown\nSTATUS=FAILED\nREVIEWER_FILE=collector-failure-1.txt\n"}
JSON
printf 'v1\tround\t1700000000\tdesign\tdesign Step 3 — plan review\t1\t1700000000\t1700000065\t65\t2\t1\t1\t-\n' \
    >"$RPD_D/timing-ledger.tsv"
printf 'v1\tvendor\t1700000010\timplement\t-\tclaude\treview\t1700000010\t1700000060\t50\tclaude-plan-generic-output.txt\t0\tcomplete\n' \
    >>"$RPD_D/timing-ledger.tsv"
std_rpd="$TMP/std-review-phase-detail.log"
DESIGN_TMPDIR="$RPD_D" ISSUE_NUMBER="" SESSION_ID="RUN-RPD" \
    "$SUBJECT" --outcome approved --post-publish-only >"$std_rpd" 2>/dev/null
grep -Fq -- '## Review Phase Detail' "$RPD_D/final-summary.md" \
    || fail 'post-publish path missing Review Phase Detail section'
grep -Fq -- '| 1 | 4 | 2 | 2 | 1 | 1m 05s | — | 1 |' "$RPD_D/final-summary.md" \
    || fail "Review Phase Detail row wrong: $(grep -F '| 1 |' "$RPD_D/final-summary.md" || true)"
grep -Fq -- '1. claude_sub/claude-plan-generic — 2' "$RPD_D/final-summary.md" \
    || fail "Review Phase Detail top reviewer wrong: $(grep -F 'claude' "$RPD_D/final-summary.md" || true)"
grep -Fq -- '**Reviewer slot failures**: 1' "$RPD_D/final-summary.md" \
    || fail 'Review Phase Detail missing collector failure count'
grep -Fq -- '### Round 1 reviewer timing' "$RPD_D/final-summary.md" \
    || fail 'design final summary missing reviewer timing heading'
grep -Fq -- '```' "$RPD_D/final-summary.md" \
    || fail 'design final summary missing plain ASCII fence'
if grep -Fq -- '```mermaid' "$RPD_D/final-summary.md"; then fail 'design final summary must omit Mermaid fence'; fi
if grep -Fq -- 'dateFormat X' "$RPD_D/final-summary.md"; then fail 'design final summary must omit dateFormat X'; fi
if grep -Fq -- 'axisFormat %H:%M:%S' "$RPD_D/final-summary.md"; then fail 'design final summary must omit hour axisFormat'; fi
grep -Fq -- 'claude_sub/claude-plan-generic' "$RPD_D/final-summary.md" \
    || fail 'design final summary missing ASCII chart label'
grep -Fq -- '50s' "$RPD_D/final-summary.md" \
    || fail 'design final summary missing bare ASCII duration'
grep -Fq -- 'window 0:00-1:05 (65s)' "$RPD_D/final-summary.md" \
    || fail 'design final summary missing m:ss chart title'
grep -Fq -- '## Review Phase Detail' "$std_rpd" || fail 'stdout missing Review Phase Detail section'
pass 'post-publish appends Review Phase Detail from plan-review rounds'


grep -Fq 'design-failure-report.sh' "$SUBJECT" || fail 'render-final-summary must invoke design-failure-report.sh'
grep -Fq 'design-failure-report.stdout.log' "$SUBJECT" || fail 'render-final-summary must capture report helper stdout'
grep -Fq 'design-failure-report.stderr.log' "$SUBJECT" || fail 'render-final-summary must capture report helper stderr'
grep -Fq 'print_report_gate_sidecars' "$SUBJECT" || fail 'render-final-summary must print report sidecars outside summary body'
for outcome in failed-postplan failed-clarify failed-judge-panel failed-publish-tail; do
  grep -Fq "$outcome" "$SUBJECT" || fail "render-final-summary must accept $outcome"
done
pass 'design failure report gate static contract'

printf 'PASS: test-render-final-summary.sh\n'
