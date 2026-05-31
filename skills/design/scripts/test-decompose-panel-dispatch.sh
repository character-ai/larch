#!/usr/bin/env bash
# test-decompose-panel-dispatch.sh — offline harness for decompose-panel-dispatch.sh.
# Topology composition: offline panel regression harness
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
PANEL="$REPO_ROOT/skills/design/scripts/decompose-panel-dispatch.sh"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-decompose-panel.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

[[ -x "$PANEL" ]] || fail "decompose-panel-dispatch.sh not executable"

prep_common() {
    local d="$1"
    mkdir -p "$d"
    printf 'Feature text.\n' >"$d/feature-description.txt"
    printf 'Plan body.\n' >"$d/plan.txt"
    printf 'Discussion.\n' >"$d/discussion-round1.md"
}

make_stub() {
    cat <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
log="${WATERFALL_STUB_LOG:?}"
paths_out="${WATERFALL_STUB_PATHS_OUT:?}"
mode="${W_STUB_MODE:-ok}"
printf '%s\n' "$0 $*" >>"$log"
slots=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --slots-file) slots="${2:?}"; shift 2 ;;
        --paths-file) paths_out="${2:?}"; shift 2 ;;
        --codex-present|--cursor-present|--mode|--timeout|--plan-file|--feature-file|--no-fallback) shift 2 ;;
        *) shift 1 ;;
    esac
done
[[ -n "$slots" ]] || exit 2
: >"$paths_out"
while IFS= read -r row || [[ -n "$row" ]]; do
    [[ -n "$row" ]] || continue
    out=$(printf '%s' "$row" | jq -r '.output // empty')
    mkdir -p "$(dirname "$out")"
    case "$mode" in
        ok) printf '## Recommendation\nsplit\n' >"$out" ;;
        nop) printf 'no heading here\n' >"$out" ;;
        *) printf '## Recommendation\nsplit\n' >"$out" ;;
    esac
    printf '%s\n' "$out" >>"$paths_out"
done <"$slots"
fc="${W_STUB_FALLBACK_COUNT:-0}"
case "$fc" in ''|*[!0-9]*) fc=0 ;; esac
cfc="${W_STUB_COMBINED_FALLBACK_COUNT:-$fc}"
case "$cfc" in ''|*[!0-9]*) cfc="$fc" ;; esac
p2="${W_STUB_PHASE2_RELAUNCH_COUNT:-0}"
case "$p2" in ''|*[!0-9]*) p2=0 ;; esac
static_ok="${W_STUB_STATIC_OK:-true}"
printf 'DISPATCH_OK=true\n'
printf 'FALLBACK_COUNT=%s\n' "$fc"
printf 'PHASE2_RELAUNCH_COUNT=%s\n' "$p2"
printf 'COMBINED_FALLBACK_COUNT=%s\n' "$cfc"
printf 'STATIC_DISPATCH_OK=%s\n' "$static_ok"
printf 'DYNAMIC_DISPATCH_OK=true\n'
printf 'ALL_OUTPUT_FILES_PATH=%s\n' "$paths_out"
exit "${W_STUB_EXIT_CODE:-0}"
STUB
}

echo "=== plan mode: 8 slots + substitution ==="
D1="$TMP/m1"
prep_common "$D1"
STUB1="$TMP/stub1.sh"
make_stub >"$STUB1"
chmod +x "$STUB1"
: >"$D1/wf.log"
DECOMPOSE_PANEL_WATERFALL_SH="$STUB1" \
    WATERFALL_STUB_LOG="$D1/wf.log" \
    WATERFALL_STUB_PATHS_OUT="$D1/paths.out" \
    W_STUB_MODE=ok \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    "$PANEL" \
    --design-tmpdir "$D1" \
    --codex-present true \
    --cursor-present true \
    --mode plan \
    --plan-file "$D1/plan.txt" \
    --timeout 30 >"$D1/out.kv"
grep -Fq 'PANEL_STATUS=ok' "$D1/out.kv" || fail "expected PANEL_STATUS=ok"
grep -Fq 'PANEL_OUTPUTS_FILE=' "$D1/out.kv" || fail "missing PANEL_OUTPUTS_FILE"
rows=$(grep -c . "$D1/decompose/panel-outputs.ndjson" || true)
[[ "$rows" == "8" ]] || fail "expected 8 panel rows got $rows"
grep -Fq 'Plan body.' "$D1/decompose/render-decomp-cursor-decomposition-specialist.prompt" \
    || fail "plan body missing from rendered prompt"
grep -Fq -- '--no-fallback' "$D1/wf.log" || fail "decompose dispatch must pass --no-fallback"
jq -s -e 'all(.[]; has("fallback_group") | not)' "$D1/decompose/decompose-slots.ndjson" >/dev/null \
    || fail "decompose slots must not include fallback_group"
for archetype in decomposition-specialist dependency-analyst scope-minimalist risk-isolation; do
    jq -s -e --arg a "$archetype" '
        [.[] | select(.slot == ("decomp-cursor-" + $a) or .slot == ("decomp-codex-" + $a))]
        | length == 2
    ' "$D1/decompose/decompose-slots.ndjson" >/dev/null \
        || fail "both vendors expected for decompose archetype $archetype"
done

# Recommendation-heading gate threaded to the waterfall (Fix 2 caller adoption).
grep -Fq -- '--require-result-pattern' "$D1/wf.log" \
    || fail "expected --require-result-pattern threaded to waterfall"
grep -Fq -- '^[[:space:]]*## Recommendation' "$D1/wf.log" \
    || fail "expected recommendation-heading regex threaded to waterfall"

echo "=== degraded when STATIC_DISPATCH_OK=false ==="
D2="$TMP/m2"
prep_common "$D2"
STUB2="$TMP/stub2.sh"
make_stub >"$STUB2"
chmod +x "$STUB2"
: >"$D2/wf.log"
DECOMPOSE_PANEL_WATERFALL_SH="$STUB2" \
    WATERFALL_STUB_LOG="$D2/wf.log" \
    WATERFALL_STUB_PATHS_OUT="$D2/paths.out" \
    W_STUB_STATIC_OK=false \
    W_STUB_MODE=ok \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    "$PANEL" \
    --design-tmpdir "$D2" \
    --codex-present true \
    --cursor-present true \
    --mode plan \
    --plan-file "$D2/plan.txt" \
    --timeout 30 >"$D2/out.kv"
grep -Fq 'DEGRADED_PANEL=true' "$D2/out.kv" || fail "expected degraded panel"
grep -Fq 'PANEL_STATUS=degraded' "$D2/out.kv" || fail "expected PANEL_STATUS=degraded"

echo "=== panel-failed when zero parseable Recommendation ==="
D3="$TMP/m3"
prep_common "$D3"
STUB3="$TMP/stub3.sh"
make_stub >"$STUB3"
chmod +x "$STUB3"
: >"$D3/wf.log"
DECOMPOSE_PANEL_WATERFALL_SH="$STUB3" \
    WATERFALL_STUB_LOG="$D3/wf.log" \
    WATERFALL_STUB_PATHS_OUT="$D3/paths.out" \
    W_STUB_MODE=nop \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    "$PANEL" \
    --design-tmpdir "$D3" \
    --codex-present true \
    --cursor-present true \
    --mode feature-only \
    --feature-file "$D3/feature-description.txt" \
    --discussion-round1-file "$D3/discussion-round1.md" \
    --timeout 30 >"$D3/out.kv"
grep -Fq 'PANEL_STATUS=panel-failed' "$D3/out.kv" || fail "expected panel-failed"

echo "=== degraded when waterfall non-zero but proposals parse ==="
D4="$TMP/m4"
prep_common "$D4"
STUB4="$TMP/stub4.sh"
make_stub >"$STUB4"
chmod +x "$STUB4"
: >"$D4/wf.log"
DECOMPOSE_PANEL_WATERFALL_SH="$STUB4" \
    WATERFALL_STUB_LOG="$D4/wf.log" \
    WATERFALL_STUB_PATHS_OUT="$D4/paths.out" \
    W_STUB_MODE=ok \
    W_STUB_EXIT_CODE=3 \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    "$PANEL" \
    --design-tmpdir "$D4" \
    --codex-present true \
    --cursor-present true \
    --mode plan \
    --plan-file "$D4/plan.txt" \
    --timeout 30 >"$D4/out.kv"
grep -Fq 'PANEL_STATUS=degraded' "$D4/out.kv" || fail "expected degraded when waterfall fails with usable outputs"
grep -Fq 'DEGRADED_PANEL=true' "$D4/out.kv" || fail "expected DEGRADED_PANEL true"

echo "=== plan mode: partial slot drop under --no-fallback ==="
D5="$TMP/m5"
prep_common "$D5"
STUB5="$TMP/stub5.sh"
cat >"$STUB5" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
log="${WATERFALL_STUB_LOG:?}"
paths_out="${WATERFALL_STUB_PATHS_OUT:?}"
printf '%s\n' "$0 $*" >>"$log"
slots=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --slots-file) slots="${2:?}"; shift 2 ;;
        --paths-file) paths_out="${2:?}"; shift 2 ;;
        --codex-present|--cursor-present|--mode|--timeout|--plan-file|--feature-file|--no-fallback) shift 2 ;;
        *) shift 1 ;;
    esac
done
[[ -n "$slots" ]] || exit 2
: >"$paths_out"
first=true
while IFS= read -r row || [[ -n "$row" ]]; do
    [[ -n "$row" ]] || continue
    out=$(printf '%s' "$row" | jq -r '.output // empty')
    mkdir -p "$(dirname "$out")"
    if [[ "$first" == true ]]; then
        printf 'narration only, no heading\n' >"$out"
        first=false
    else
        printf '## Recommendation\nsplit\n' >"$out"
        printf '%s\n' "$out" >>"$paths_out"
    fi
done <"$slots"
printf 'DISPATCH_OK=true\n'
printf 'FALLBACK_COUNT=0\n'
printf 'STATIC_DISPATCH_OK=true\n'
printf 'DYNAMIC_DISPATCH_OK=true\n'
printf 'ALL_OUTPUT_FILES_PATH=%s\n' "$paths_out"
exit 0
STUB
chmod +x "$STUB5"
: >"$D5/wf.log"
DECOMPOSE_PANEL_WATERFALL_SH="$STUB5" \
    WATERFALL_STUB_LOG="$D5/wf.log" \
    WATERFALL_STUB_PATHS_OUT="$D5/paths.out" \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    "$PANEL" \
    --design-tmpdir "$D5" \
    --codex-present true \
    --cursor-present true \
    --mode plan \
    --plan-file "$D5/plan.txt" \
    --timeout 30 >"$D5/out.kv"
grep -Fq 'DEGRADED_PANEL=true' "$D5/out.kv" || fail "partial slot drop should mark degraded panel"
_paths5=$(grep '^ALL_OUTPUT_FILES_PATH=' "$D5/out.kv" | head -1 | cut -d= -f2-)
[[ "$(grep -c . "$_paths5" || true)" == "7" ]] || fail "partial drop should list seven succeeded paths"
grep -Fq -- '-phase2.txt' "$_paths5" && fail "no-fallback partial drop must not list phase-2 recovery paths"
first_row=$(sed -n '1p' "$D5/decompose/panel-outputs.ndjson")
first_status=$(printf '%s' "$first_row" | jq -r '.status')
[[ "$first_status" == "unparsed" || "$first_status" == "missing" ]] \
    || fail "dropped slot row should be unparsed/missing, got '$first_status'"

echo "=== DEGRADED_PANEL when paths-file has fewer entries than manifest slots ==="
D6="$TMP/m6"
prep_common "$D6"
STUB6="$TMP/stub6.sh"
cat >"$STUB6" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
paths_out="${WATERFALL_STUB_PATHS_OUT:?}"
slots=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --slots-file) slots="${2:?}"; shift 2 ;;
        --paths-file) paths_out="${2:?}"; shift 2 ;;
        *) shift 1 ;;
    esac
done
: >"$paths_out"
n=0
while IFS= read -r row || [[ -n "$row" ]]; do
    [[ -n "$row" ]] || continue
    out=$(printf '%s' "$row" | jq -r '.output // empty')
    mkdir -p "$(dirname "$out")"
    printf '## Recommendation\nsplit\n' >"$out"
    n=$((n + 1))
    (( n <= 4 )) && printf '%s\n' "$out" >>"$paths_out"
done <"$slots"
printf 'DISPATCH_OK=true\nSTATIC_DISPATCH_OK=true\nALL_OUTPUT_FILES_PATH=%s\n' "$paths_out"
STUB
chmod +x "$STUB6"
: >"$D6/wf.log"
DECOMPOSE_PANEL_WATERFALL_SH="$STUB6" \
    WATERFALL_STUB_PATHS_OUT="$D6/paths.out" \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    "$PANEL" \
    --design-tmpdir "$D6" \
    --codex-present true \
    --cursor-present true \
    --mode plan \
    --plan-file "$D6/plan.txt" \
    --timeout 30 >"$D6/out.kv"
grep -Fq 'DEGRADED_PANEL=true' "$D6/out.kv" || fail "partial paths-file should mark degraded panel on 8 slots"

echo "=== availability matrix: codex-down => cursor-only rows ==="
D8="$TMP/m8"
prep_common "$D8"
STUB8="$TMP/stub8.sh"
make_stub >"$STUB8"
chmod +x "$STUB8"
: >"$D8/wf.log"
DECOMPOSE_PANEL_WATERFALL_SH="$STUB8" \
    WATERFALL_STUB_LOG="$D8/wf.log" \
    WATERFALL_STUB_PATHS_OUT="$D8/paths.out" \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    "$PANEL" \
    --design-tmpdir "$D8" \
    --codex-present false \
    --cursor-present true \
    --mode plan \
    --plan-file "$D8/plan.txt" \
    --timeout 30 >"$D8/out.kv"
[[ "$(grep -c . "$D8/decompose/decompose-slots.ndjson" || true)" == "4" ]] || fail "codex-down expected 4 cursor rows"
grep -Fq 'decomp-codex-' "$D8/decompose/decompose-slots.ndjson" && fail "codex-down must not emit codex rows"
grep -Fq -- '--no-fallback' "$D8/wf.log" || fail "codex-down dispatch must pass --no-fallback"

echo "=== availability matrix: cursor-down => codex-only rows ==="
D9="$TMP/m9"
prep_common "$D9"
STUB9="$TMP/stub9.sh"
make_stub >"$STUB9"
chmod +x "$STUB9"
: >"$D9/wf.log"
DECOMPOSE_PANEL_WATERFALL_SH="$STUB9" \
    WATERFALL_STUB_LOG="$D9/wf.log" \
    WATERFALL_STUB_PATHS_OUT="$D9/paths.out" \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    "$PANEL" \
    --design-tmpdir "$D9" \
    --codex-present true \
    --cursor-present false \
    --mode plan \
    --plan-file "$D9/plan.txt" \
    --timeout 30 >"$D9/out.kv"
[[ "$(grep -c . "$D9/decompose/decompose-slots.ndjson" || true)" == "4" ]] || fail "cursor-down expected 4 codex rows"
grep -Fq 'decomp-cursor-' "$D9/decompose/decompose-slots.ndjson" && fail "cursor-down must not emit cursor rows"
grep -Fq -- '--no-fallback' "$D9/wf.log" || fail "cursor-down dispatch must pass --no-fallback"

echo "=== availability matrix: both-absent => generic Claude reviewer ==="
PLUGIN_STUB="$TMP/plugin-stub"
mkdir -p "$PLUGIN_STUB/scripts" "$PLUGIN_STUB/skills/design/scripts"
cp "$REPO_ROOT/scripts/lib-quiet.sh" "$PLUGIN_STUB/scripts/"
cp "$REPO_ROOT/scripts/lib-design-tmpdir.sh" "$PLUGIN_STUB/scripts/"
cat >"$PLUGIN_STUB/scripts/launch-claude-review.sh" <<'CLAUDE_STUB'
#!/usr/bin/env bash
OUTPUT="" PROMPT_FILE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) OUTPUT="${2:?}"; shift 2 ;;
        --prompt-file) PROMPT_FILE="${2:?}"; shift 2 ;;
        --mode|--timeout|--timing-task-kind|--feature-file) shift 2 ;;
        *) shift ;;
    esac
done
printf '## Recommendation\nGeneric decomposition.\n' >"$OUTPUT"
printf '0\n' >"${OUTPUT}.done"
CLAUDE_STUB
chmod +x "$PLUGIN_STUB/scripts/launch-claude-review.sh"
D10="$TMP/m10"
prep_common "$D10"
DECOMPOSE_PANEL_WATERFALL_SH="$STUB9" \
    CLAUDE_PLUGIN_ROOT="$PLUGIN_STUB" \
    "$PANEL" \
    --design-tmpdir "$D10" \
    --codex-present false \
    --cursor-present false \
    --mode plan \
    --plan-file "$D10/plan.txt" \
    --timeout 30 >"$D10/out.kv"
[[ ! -s "$D10/decompose/decompose-slots.ndjson" ]] || fail "both-absent must emit zero manifest rows"
[[ "$(grep -c . "$D10/decompose/panel-outputs.ndjson" || true)" == "1" ]] || fail "both-absent expected one generic panel row"
grep -Fq 'decomp-claude-generic-output.txt' "$D10/decompose/panel-outputs.ndjson" \
    || fail "both-absent must record generic Claude output path"
grep -Fq 'PANEL_STATUS=ok' "$D10/out.kv" || fail "both-absent generic path should yield ok panel status"

echo "PASS: test-decompose-panel-dispatch.sh"
