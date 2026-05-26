#!/usr/bin/env bash
# test-decompose-aggregator.sh — offline harness for decompose-aggregator.sh.
# Topology composition: offline aggregator merge harness
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
AGG="$REPO_ROOT/skills/design/scripts/decompose-aggregator.sh"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-decompose-agg.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

[[ -x "$AGG" ]] || fail "decompose-aggregator.sh not executable"

echo "=== aggregator happy path ==="
D="$TMP/a"
mkdir -p "$D"
printf 'Feature ctx\n' >"$D/feature-description.txt"
cat >"$D/panel.ndjson" <<'ND'
{"archetype":"decomposition-specialist","vendor":"cursor","output":"OUT1","status":"ok"}
{"archetype":"decomposition-specialist","vendor":"codex","output":"OUT2","status":"ok"}
ND

printf '## Recommendation\nsplit\n## Pieces\n### Piece 1: A\n' >"$D/OUT1"
printf '## Recommendation\nno-split\n' >"$D/OUT2"

STUB="$D/wf.sh"
cat >"$STUB" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
log="${AGG_STUB_LOG:?}"
paths_out="${AGG_PATHS_OUT:?}"
fail="${AGG_STUB_FAIL:-false}"
printf '%s\n' "$0 $*" >>"$log"
slots=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --slots-file) slots="${2:?}"; shift 2 ;;
        *) shift 1 ;;
    esac
done
out=$(jq -r '.output' "$slots")
mkdir -p "$(dirname "$out")"
if [[ "$fail" == true ]]; then
    printf 'broken\n' >"$out"
    printf 'DISPATCH_OK=false\n'
else
    printf '## Recommendation\nsplit\n## Pieces\n### Piece 1: Merged\n- Scope: x\n- Dependencies: none\n- Diff_lines estimate: 1\n- Why: y\n' >"$out"
    printf 'DISPATCH_OK=true\n'
fi
printf 'ALL_OUTPUT_FILES_PATH=%s\n' "$paths_out"
: >"$paths_out"
printf '%s\n' "$out" >>"$paths_out"
STUB
chmod +x "$STUB"

: >"$D/wf.log"
DECOMPOSE_AGGREGATE_WATERFALL_SH="$STUB" \
    AGG_STUB_LOG="$D/wf.log" \
    AGG_PATHS_OUT="$D/paths.out" \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    "$AGG" \
    --design-tmpdir "$D" \
    --panel-outputs-file "$D/panel.ndjson" \
    --codex-present true \
    --cursor-present true \
    --output "$D/merged.md" \
    --timeout 30 >"$D/out.kv" || true
grep -Fq 'AGGREGATOR_STATUS=ok' "$D/out.kv" || fail "expected AGGREGATOR_STATUS=ok"
grep -Fq '## Recommendation' "$D/merged.md" || fail "merged output missing heading"
grep -Fq '## Panel output' "$D/decompose/aggregator-partition-merge.prompt" \
    || fail "merge prompt missing concatenated panel headers"

# Aggregator's single-slot row is built with tool=codex (Fix 1) so the more
# reliable vendor runs first on the safety-net slot.
agg_tool=$(jq -r '.tool' "$D/decompose/aggregator-slots.ndjson")
[[ "$agg_tool" == "codex" ]] || fail "expected aggregator slot tool=codex got '$agg_tool'"

# Aggregator threads the recommendation-heading gate through the waterfall
# (Fix 2 caller adoption). The stub logs `"$0 $*"` per invocation; both the
# flag and its argument must appear so a future regression that drops either
# half of the pair is caught.
grep -Fq -- '--require-result-pattern' "$D/wf.log" \
    || fail "expected --require-result-pattern threaded to waterfall"
grep -Fq -- '^[[:space:]]*## Recommendation' "$D/wf.log" \
    || fail "expected recommendation-heading regex threaded to waterfall"

echo "=== AGGREGATOR_STATUS=failed when DISPATCH_OK path broken ==="
D2="$TMP/b"
mkdir -p "$D2"
printf 'f\n' >"$D2/feature-description.txt"
cp "$D/panel.ndjson" "$D2/panel.ndjson"
cp "$D/OUT1" "$D2/OUT1"
cp "$D/OUT2" "$D2/OUT2"
: >"$D2/wf.log"
DECOMPOSE_AGGREGATE_WATERFALL_SH="$STUB" \
    AGG_STUB_LOG="$D2/wf.log" \
    AGG_PATHS_OUT="$D2/paths.out" \
    AGG_STUB_FAIL=true \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    "$AGG" \
    --design-tmpdir "$D2" \
    --panel-outputs-file "$D2/panel.ndjson" \
    --codex-present true \
    --cursor-present true \
    --output "$D2/merged.md" \
    --timeout 30 >"$D2/out.kv" || true
grep -Fq 'AGGREGATOR_STATUS=failed' "$D2/out.kv" || fail "expected AGGREGATOR_STATUS=failed"

echo "PASS: test-decompose-aggregator.sh"
