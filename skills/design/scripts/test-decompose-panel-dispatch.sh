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
        --codex-present|--cursor-present|--mode|--timeout|--plan-file|--feature-file) shift 2 ;;
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
static_ok="${W_STUB_STATIC_OK:-true}"
printf 'DISPATCH_OK=true\n'
printf 'FALLBACK_COUNT=%s\n' "$fc"
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

echo "PASS: test-decompose-panel-dispatch.sh"
