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
jq -s -e 'all(.[]; .fallback_group != null)' "$D1/decompose/decompose-slots.ndjson" >/dev/null \
    || fail "every decompose slot must include fallback_group"
for archetype in decomposition-specialist dependency-analyst scope-minimalist risk-isolation; do
    expected="decomp-${archetype}"
    jq -s -e --arg a "$archetype" --arg fg "$expected" '
        [.[] | select(.slot == ("decomp-cursor-" + $a) or .slot == ("decomp-codex-" + $a))]
        | length == 2 and all(.[]; .fallback_group == $fg)
    ' "$D1/decompose/decompose-slots.ndjson" >/dev/null \
        || fail "fallback_group pairing mismatch for $archetype"
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

echo "=== plan mode: resolved-paths panel rows ==="
# When the dispatcher resolves a slot through phase-2/phase-3 fallback, the
# `ALL_OUTPUT_FILES_PATH` line for that slot points at the fallback file. The
# panel must record THAT path in `panel-outputs.ndjson`, not the manifest's
# original phase-1 path, so operator presentation sees the recovered content.
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
        --codex-present|--cursor-present|--mode|--timeout|--plan-file|--feature-file) shift 2 ;;
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
        phase2_out="${out%.txt}-phase2.txt"
        printf '## Recommendation\nsplit\n' >"$phase2_out"
        printf '%s\n' "$phase2_out" >>"$paths_out"
        first=false
    else
        printf '## Recommendation\nsplit\n' >"$out"
        printf '%s\n' "$out" >>"$paths_out"
    fi
done <"$slots"
printf 'DISPATCH_OK=true\n'
printf 'FALLBACK_COUNT=1\n'
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
first_row=$(sed -n '1p' "$D5/decompose/panel-outputs.ndjson")
first_status=$(printf '%s' "$first_row" | jq -r '.status')
first_output=$(printf '%s' "$first_row" | jq -r '.output')
[[ "$first_status" == "ok" ]] || fail "expected resolved-paths first row status=ok got '$first_status'"
case "$first_output" in
    *-phase2.txt) ;;
    *) fail "expected first row output to point at phase-2 fallback path, got '$first_output'" ;;
esac
[[ -f "$first_output" ]] || fail "resolved phase-2 path does not exist: $first_output"
grep -Fq '## Recommendation' "$first_output" \
    || fail "resolved phase-2 file missing Recommendation heading"

echo "=== DEGRADED_PANEL from COMBINED_FALLBACK_COUNT only (8 slots, half=4) ==="
D6="$TMP/m6"
prep_common "$D6"
STUB6="$TMP/stub6.sh"
make_stub >"$STUB6"
chmod +x "$STUB6"
: >"$D6/wf.log"
DECOMPOSE_PANEL_WATERFALL_SH="$STUB6" \
    WATERFALL_STUB_LOG="$D6/wf.log" \
    WATERFALL_STUB_PATHS_OUT="$D6/paths.out" \
    W_STUB_FALLBACK_COUNT=0 \
    W_STUB_COMBINED_FALLBACK_COUNT=5 \
    W_STUB_STATIC_OK=true \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    "$PANEL" \
    --design-tmpdir "$D6" \
    --codex-present true \
    --cursor-present true \
    --mode plan \
    --plan-file "$D6/plan.txt" \
    --timeout 30 >"$D6/out.kv"
grep -Fq 'DEGRADED_PANEL=true' "$D6/out.kv" || fail "COMBINED_FALLBACK_COUNT=5 with FALLBACK_COUNT=0 should degrade on 8 slots"

echo "PASS: test-decompose-panel-dispatch.sh"
