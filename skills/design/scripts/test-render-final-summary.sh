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

pre_std="$TMP/std-pre.log"
DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-PRE" \
    "$SUBJECT" --outcome approved --mode SIMPLE --pre-publish-only >"$pre_std" 2>/dev/null
[ ! -s "$pre_std" ] || fail 'pre-publish path must not print summary to stdout'
grep -Fq -- '- **Cost**:' "$D/final-summary.md" || fail 'pre-publish path missing Cost bullet'
pass 'pre-publish writes file without chat output'

outline_std="$TMP/std-outline.log"
DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-OUTLINE" \
    "$SUBJECT" --outcome cancelled-outline --mode SIMPLE --post-publish-only >"$outline_std" 2>/dev/null
grep -Fq -- '- **Outcome**: cancelled-outline' "$D/final-summary.md" || fail 'cancelled-outline missing Outcome bullet'
grep -Fq -- '- **Cancel site**: Step 1d.7 outline gate' "$D/final-summary.md" || fail 'cancelled-outline missing Step 1d.7 outline phrasing'
cmp -s "$D/final-summary.md" "$outline_std" || fail 'cancelled-outline stdout/file mismatch'
pass 'cancelled-outline outcome renders'

PLUGIN_STUB="$TMP/plugin"
mkdir -p "$PLUGIN_STUB/scripts"
cp "$ROOT/scripts/render-run-summary.sh" "$PLUGIN_STUB/scripts/render-run-summary.sh"
cp "$ROOT/scripts/token-cost.sh" "$PLUGIN_STUB/scripts/token-cost.sh"
cp "$ROOT/scripts/lib-cost-line-format.sh" "$PLUGIN_STUB/scripts/lib-cost-line-format.sh"
cp "$ROOT/scripts/lib-quiet.sh" "$PLUGIN_STUB/scripts/lib-quiet.sh"
cp "$ROOT/scripts/append-tool-failure.sh" "$PLUGIN_STUB/scripts/append-tool-failure.sh"
cp "$ROOT/scripts/append-execution-issue.sh" "$PLUGIN_STUB/scripts/append-execution-issue.sh"
cp "$ROOT/scripts/redact-secrets.sh" "$PLUGIN_STUB/scripts/redact-secrets.sh"
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
    "$PLUGIN_STUB/scripts/render-run-summary.sh" "$PLUGIN_STUB/scripts/token-cost.sh" \
    "$PLUGIN_STUB/scripts/append-tool-failure.sh" "$PLUGIN_STUB/scripts/append-execution-issue.sh" \
    "$PLUGIN_STUB/scripts/redact-secrets.sh"

std_codex="$TMP/std-codex.log"
CLAUDE_PLUGIN_ROOT="$PLUGIN_STUB" DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-FIX" \
    "$SUBJECT" --outcome approved --mode SIMPLE --post-publish-only >"$std_codex" 2>"$TMP/std-codex.err"
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
cmp -s "$D/final-summary.md" "$std_codex" || fail 'codex buckets stdout/file mismatch'
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

- **Mode**: SIMPLE
- **Path**: SIMPLE
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

- **Mode**: SIMPLE
- **Path**: SIMPLE
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
    "$SUBJECT" --outcome approved --mode SIMPLE --post-publish-only >"$std_post_na" 2>/dev/null
# shellcheck disable=SC2016
grep -Fq '💰 TOTAL: $2.34' "$D/final-summary.md" || fail 'post success with N/A cost must preserve prior usable cost line'
cmp -s "$D/final-summary.md" "$std_post_na" || fail 'post success preserved-cost stdout/file mismatch'
pass 'post success preserves prior usable cost line'

cp "$PLUGIN_STUB/scripts/render-run-summary.sh" "$TMP/render-run-summary.real"
cat >"$PLUGIN_STUB/scripts/render-run-summary.sh" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
chmod +x "$PLUGIN_STUB/scripts/render-run-summary.sh"
cat >"$D/final-summary.md" <<'EOF'
## /design run RUN-PREGOOD — approved

- **Mode**: SIMPLE
- **Path**: SIMPLE
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
    "$SUBJECT" --outcome approved --mode SIMPLE --post-publish-only >"$std_fb" 2>/dev/null
grep -Fq -- '💰 TOTAL' "$D/final-summary.md" || fail 'renderer-fail post path must preserve prior usable cost line'
grep -Fq -- '## /design run RUN-FB — approved' "$D/final-summary.md" || fail 'renderer-fail post path must refresh title/run id'
grep -Fq -- '- **Exec issues**: 0' "$D/final-summary.md" || fail 'renderer-fail post path must refresh exec issue count'
grep -Fq -- '- **Warnings**: 1' "$D/final-summary.md" || fail 'renderer-fail post path must refresh warning count'
if grep -Fq -- '- **PR**:' "$D/final-summary.md"; then fail 'renderer-fail preserved file must not emit PR bullet'; fi
if grep -Fq -- '- **Code review**:' "$D/final-summary.md"; then fail 'renderer-fail preserved file must not emit Code review bullet'; fi
cmp -s "$D/final-summary.md" "$std_fb" || fail 'renderer-fail fallback stdout/file mismatch'
pass 'renderer-fail fallback prints final file once'
std_fb_cancel="$TMP/std-fallback-cancelled.log"
: >"$D/final-summary.md"
CLAUDE_PLUGIN_ROOT="$PLUGIN_STUB" DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-FB-CANCELLED" \
    "$SUBJECT" --outcome cancelled-clarify --mode SIMPLE --post-publish-only >"$std_fb_cancel" 2>/dev/null
grep -Fq -- '- **Outcome**: cancelled-clarify' "$D/final-summary.md" || fail 'renderer-fail cancelled fallback missing Outcome bullet'
grep -Fq -- '- **Cost**: N/A' "$D/final-summary.md" || fail 'renderer-fail cancelled fallback missing Cost N/A'
grep -Fq -- '- **Cost**: N/A' "$std_fb_cancel" || fail 'renderer-fail cancelled stdout missing Cost N/A'
cp "$TMP/render-run-summary.real" "$PLUGIN_STUB/scripts/render-run-summary.sh"
chmod +x "$PLUGIN_STUB/scripts/render-run-summary.sh"

PLUGIN_FAILTOK="$TMP/plugin-failtok"
mkdir -p "$PLUGIN_FAILTOK/scripts"
cp "$ROOT/scripts/render-run-summary.sh" "$PLUGIN_FAILTOK/scripts/render-run-summary.sh"
cp "$ROOT/scripts/token-cost.sh" "$PLUGIN_FAILTOK/scripts/token-cost.sh"
cp "$ROOT/scripts/lib-cost-line-format.sh" "$PLUGIN_FAILTOK/scripts/lib-cost-line-format.sh"
cp "$ROOT/scripts/lib-quiet.sh" "$PLUGIN_FAILTOK/scripts/lib-quiet.sh"
cp "$ROOT/scripts/append-tool-failure.sh" "$PLUGIN_FAILTOK/scripts/append-tool-failure.sh"
cp "$ROOT/scripts/append-execution-issue.sh" "$PLUGIN_FAILTOK/scripts/append-execution-issue.sh"
cp "$ROOT/scripts/redact-secrets.sh" "$PLUGIN_FAILTOK/scripts/redact-secrets.sh"
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
    "$SUBJECT" --outcome approved --mode SIMPLE --post-publish-only >"$std_failtok" 2>/dev/null
grep -Fq -- '- **Cost**: N/A' "$D/final-summary.md" || fail 'token-data-missing path missing Cost N/A'
if grep -Fq "Claude \$0.00, Codex \$0.00, Cursor \$0.00" "$D/final-summary.md"; then
    fail 'token-data-missing path rendered misleading zero-dollar cost'
fi
grep -Fq -- '--cost-unavailable' "$TMP/render-args.log" || fail 'token-data-missing path must pass --cost-unavailable to renderer'
pass 'token-data-missing path renders Cost N/A'

PLUGIN_BADJSON="$TMP/plugin-badjson"
mkdir -p "$PLUGIN_BADJSON/scripts"
cp "$ROOT/scripts/render-run-summary.sh" "$PLUGIN_BADJSON/scripts/render-run-summary.sh"
cp "$ROOT/scripts/token-cost.sh" "$PLUGIN_BADJSON/scripts/token-cost.sh"
cp "$ROOT/scripts/lib-cost-line-format.sh" "$PLUGIN_BADJSON/scripts/lib-cost-line-format.sh"
cp "$ROOT/scripts/lib-quiet.sh" "$PLUGIN_BADJSON/scripts/lib-quiet.sh"
cp "$ROOT/scripts/append-tool-failure.sh" "$PLUGIN_BADJSON/scripts/append-tool-failure.sh"
cp "$ROOT/scripts/append-execution-issue.sh" "$PLUGIN_BADJSON/scripts/append-execution-issue.sh"
cp "$ROOT/scripts/redact-secrets.sh" "$PLUGIN_BADJSON/scripts/redact-secrets.sh"
cat >"$PLUGIN_BADJSON/scripts/token-report.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
out=""
while [ $# -gt 0 ]; do
  case "$1" in --output) out=$2; shift 2 ;; *) shift ;; esac
done
[ -n "$out" ] || exit 2
printf '%s\n' '{not-json' >"$out"
EOF
cat >"$PLUGIN_BADJSON/scripts/timing-report.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
out=""
while [ $# -gt 0 ]; do
  case "$1" in --output) out=$2; shift 2 ;; *) shift ;; esac
done
[ -n "$out" ] || exit 2
printf '%s\n' '{"total_hms":"2s"}' >"$out"
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
    "$SUBJECT" --outcome approved --mode SIMPLE --post-publish-only >"$std_badjson" 2>/dev/null
grep -Fq -- '- **Cost**: N/A' "$D/final-summary.md" || fail 'malformed token JSON path missing Cost N/A'
if grep -Fq "Claude \$0.00, Codex \$0.00, Cursor \$0.00" "$D/final-summary.md"; then
    fail 'malformed token JSON path rendered misleading zero-dollar cost'
fi
grep -Fq -- '--cost-unavailable' "$TMP/render-badjson-args.log" || fail 'malformed token JSON path must pass --cost-unavailable to renderer'
pass 'malformed token JSON renders Cost N/A'

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

for summary_outcome in \
    approved \
    approved-partition \
    cancelled-clarify \
    cancelled-already-planned \
    cancelled-tier-gate \
    cancelled-title-filter \
    cancelled-sprawl \
    cancelled-plan-size-hard \
    cancelled-decompose \
    failed-plan-write
do
    session="RUN-MATRIX-${summary_outcome}"
    matrix_stdout="$TMP/std-matrix-${summary_outcome}.log"
    DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="$session" \
        "$SUBJECT" --outcome "$summary_outcome" --mode SIMPLE --post-publish-only >"$matrix_stdout" 2>/dev/null
    grep -Fq -- '- **Cost**:' "$D/final-summary.md" || fail "matrix $summary_outcome missing Cost bullet"
    grep -Fq "<!-- larch:run-summary v=1 -->" "$D/final-summary.md" || fail "matrix $summary_outcome missing sentinel"
    grep -Fq "## /design run $session — $summary_outcome" "$D/final-summary.md" || fail "matrix $summary_outcome missing title"
    grep -Fq -- '- **Cost**:' "$matrix_stdout" || fail "matrix $summary_outcome stdout missing Cost bullet"
    grep -Fq "<!-- larch:run-summary v=1 -->" "$matrix_stdout" || fail "matrix $summary_outcome stdout missing sentinel"
    cmp -s "$D/final-summary.md" "$matrix_stdout" || fail "matrix $summary_outcome stdout/file mismatch"
    if [[ "$summary_outcome" == approved || "$summary_outcome" == approved-partition ]]; then
        if grep -Fq -- '- **Outcome**:' "$D/final-summary.md"; then
            fail "matrix $summary_outcome must omit Outcome bullet"
        fi
    else
        grep -Fq -- "- **Outcome**: $summary_outcome" "$D/final-summary.md" || fail "matrix $summary_outcome missing Outcome bullet"
    fi
done
pass 'ten-outcome post-publish matrix'

grep -Fq -- '--redact' "$ROOT/skills/design/scripts/render-final-summary.sh" || fail 'render-final-summary append_render_warning must redact stderr'
pass 'render-final-summary append warning redacts stderr'

set +e
DESIGN_TMPDIR="$D" ISSUE_NUMBER="" SESSION_ID="RUN-FIX" \
    "$SUBJECT" --outcome cancelled-plan-size-soft --mode SIMPLE --post-publish-only >/dev/null 2>&1
rc=$?
set -e
test "$rc" -eq 2 || fail 'invalid outcome must exit 2'
pass 'invalid outcome rejected'

printf 'PASS: test-render-final-summary.sh\n'
