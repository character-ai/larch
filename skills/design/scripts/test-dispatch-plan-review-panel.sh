#!/usr/bin/env bash
# test-dispatch-plan-review-panel.sh — regression harness for dispatch-plan-review-panel.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
PANEL="$REPO_ROOT/skills/design/scripts/dispatch-plan-review-panel.sh"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-dispatch-plan-review.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

[[ -x "$PANEL" ]] || fail "dispatch-plan-review-panel not executable"

STUB="$TMP/waterfall.sh"
cat >"$STUB" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
log="${WATERFALL_STUB_LOG:?}"
printf '%s\n' "$0 $*" >>"$log"
slots=""
plan=""
feature=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --slots-file) slots="${2:?}"; shift 2 ;;
        --plan-file) plan="${2:?}"; shift 2 ;;
        --feature-file) shift 2 ;;
        --codex-present|--cursor-present|--mode|--timeout|--require-first-line-pattern) shift 2 ;;
        *) shift 1 ;;
    esac
done
[[ -n "$slots" ]] || exit 2
n=$(grep -c . "$slots" || echo 0)
case "$n" in ''|*[!0-9]*) n=0 ;; esac
fc="${W_STUB_FALLBACK_COUNT:-0}"
case "$fc" in ''|*[!0-9]*) fc=0 ;; esac
cfc="${W_STUB_COMBINED_FALLBACK_COUNT:-$fc}"
case "$cfc" in ''|*[!0-9]*) cfc="$fc" ;; esac
p2="${W_STUB_PHASE2_RELAUNCH_COUNT:-0}"
case "$p2" in ''|*[!0-9]*) p2=0 ;; esac
half=$((n / 2))
static_ok="${W_STUB_STATIC_OK:-true}"
printf 'DISPATCH_OK=true\n'
printf 'FALLBACK_COUNT=%s\n' "$fc"
printf 'PHASE2_RELAUNCH_COUNT=%s\n' "$p2"
printf 'COMBINED_FALLBACK_COUNT=%s\n' "$cfc"
printf 'STATIC_DISPATCH_OK=%s\n' "$static_ok"
printf 'DYNAMIC_DISPATCH_OK=true\n'
printf 'ALL_OUTPUT_FILES=%s/a.txt\n' "$(dirname "$log")"
printf 'ALL_OUTPUT_TOOLS=cursor\n'
printf 'ALL_OUTPUT_FILES_PATH=%s\n' "${WATERFALL_STUB_PATHS_OUT:?}"
STUB
chmod +x "$STUB"

prep() {
    local d="$1"
    mkdir -p "$d"
    printf 'Plan body.\n' >"$d/plan.txt"
    printf 'feat\n' >"$d/feature-description.txt"
}

echo "=== static slots only (empty scout manifest) ==="
D1="$TMP/s1"
prep "$D1"
printf '{"archetypes":[]}\n' >"$D1/scout-plan-manifest.json"
log1="$D1/wf.log"
: >"$log1"
DISPATCH_PLAN_REVIEW_WATERFALL_SH="$STUB" \
    WATERFALL_STUB_LOG="$log1" \
    WATERFALL_STUB_PATHS_OUT="$D1/paths.out" \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    "$PANEL" \
    --design-tmpdir "$D1" \
    --codex-present true \
    --cursor-present true \
    --plan-file "$D1/plan.txt" \
    --feature-file "$D1/feature-description.txt" \
    --timeout 60 >"$D1/out.env"
grep -Fq 'PANEL_PATHS_FILE=' "$D1/out.env" || fail "missing PANEL_PATHS_FILE"
grep -Fq 'DYNAMIC_SLOT_COUNT=0' "$D1/out.env" || fail "expected zero dynamic slots"
grep -Fq -- '--feature-file' "$log1" || fail "feature-file not forwarded"
grep -Fq -- '--require-first-line-pattern ^[[:space:]]*(schema_version|\{"no_issues_found)' "$log1" \
    || fail "plan-review first-line pattern not forwarded"
manifest_line_count=$(grep -c . "$D1/plan-review-slots.ndjson" || true)
[[ "$manifest_line_count" == "10" ]] || fail "expected 10 ndjson lines, got $manifest_line_count"
jq -s -e 'all(.[]; .fallback_group != null)' "$D1/plan-review-slots.ndjson" >/dev/null \
    || fail "every static plan-review row must include fallback_group"
for archetype in arch edge innovation pragmatic requirements; do
    expected="plan-${archetype}"
    got_count=$(jq -r --arg fg "$expected" 'select(.fallback_group == $fg) | .slot' "$D1/plan-review-slots.ndjson" | wc -l | tr -d ' ')
    [[ "$got_count" == "2" ]] || fail "expected static fallback_group $expected on two rows, got $got_count"
    jq -s -e --arg a "$archetype" --arg fg "$expected" '
        [.[] | select(.slot == ("cursor-plan-" + $a) or .slot == ("codex-plan-" + $a))]
        | length == 2 and all(.[]; .fallback_group == $fg)
    ' "$D1/plan-review-slots.ndjson" >/dev/null \
        || fail "static fallback_group pairing mismatch for $archetype"
done

echo "=== two dynamic archetypes => 14 slots ==="
D2="$TMP/s2"
prep "$D2"
cat >"$D2/scout-plan-manifest.json" <<'JSON'
{"archetypes":[
  {"name":"alpha","focus_area":"correctness","weight":2,"rationale":"r1","prompt_body":"Check contracts."},
  {"name":"beta","focus_area":"architecture","weight":2,"rationale":"r2","prompt_body":"Check layering."}
]}
JSON
log2="$D2/wf.log"
: >"$log2"
DISPATCH_PLAN_REVIEW_WATERFALL_SH="$STUB" \
    WATERFALL_STUB_LOG="$log2" \
    WATERFALL_STUB_PATHS_OUT="$D2/paths.out" \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    "$PANEL" \
    --design-tmpdir "$D2" \
    --codex-present true \
    --cursor-present true \
    --plan-file "$D2/plan.txt" \
    --feature-file "$D2/feature-description.txt" \
    --timeout 60 >"$D2/out.env"
grep -Fq 'DYNAMIC_SLOT_COUNT=4' "$D2/out.env" || fail "expected 4 dynamic slot rows"
[[ "$(grep -c . "$D2/plan-review-slots.ndjson")" == "14" ]] || fail "expected 14 ndjson lines"
grep -Fq 'dyn-cursor-plan-alpha' "$D2/plan-review-slots.ndjson" || fail "dyn cursor alpha"
grep -Fq 'dyn-codex-plan-beta' "$D2/plan-review-slots.ndjson" || fail "dyn codex beta"
jq -e . "$D2/plan-review-slots.ndjson" >/dev/null || fail "manifest must remain valid ndjson"
jq -s -e 'all(.[]; .fallback_group != null)' "$D2/plan-review-slots.ndjson" >/dev/null \
    || fail "every static+dynamic plan-review row must include fallback_group"
for slug in alpha beta; do
    expected="plan-dyn-${slug}"
    jq -s -e --arg s "$slug" --arg fg "$expected" '
        [.[] | select(.slot == ("dyn-cursor-plan-" + $s) or .slot == ("dyn-codex-plan-" + $s))]
        | length == 2 and all(.[]; .fallback_group == $fg)
    ' "$D2/plan-review-slots.ndjson" >/dev/null \
        || fail "dynamic fallback_group pairing mismatch for $slug"
done

echo "=== prompts must not demand **Reviewer** attribution line ==="
if grep -Rq '\*\*Reviewer\*\*' "$D2"/render-plan-*.prompt "$D2"/render-plan-cursor-dyn-*.prompt 2>/dev/null; then
    fail "unexpected **Reviewer** instruction in rendered prompts"
fi

echo "=== DEGRADED_ROUND boundary (14 slots, half=7) ==="
D3="$TMP/s3"
prep "$D3"
cp "$D2/scout-plan-manifest.json" "$D3/scout-plan-manifest.json"
log3="$D3/wf.log"
: >"$log3"
DISPATCH_PLAN_REVIEW_WATERFALL_SH="$STUB" \
    WATERFALL_STUB_LOG="$log3" \
    WATERFALL_STUB_PATHS_OUT="$D3/paths.out" \
    W_STUB_FALLBACK_COUNT=7 \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    "$PANEL" \
    --design-tmpdir "$D3" \
    --codex-present true \
    --cursor-present true \
    --plan-file "$D3/plan.txt" \
    --timeout 60 >"$D3/out.env"
grep -Fq 'DEGRADED_ROUND=false' "$D3/out.env" || fail "7 fallbacks on 14 slots should not degrade"

D4="$TMP/s4"
prep "$D4"
cp "$D2/scout-plan-manifest.json" "$D4/scout-plan-manifest.json"
log4="$D4/wf.log"
: >"$log4"
DISPATCH_PLAN_REVIEW_WATERFALL_SH="$STUB" \
    WATERFALL_STUB_LOG="$log4" \
    WATERFALL_STUB_PATHS_OUT="$D4/paths.out" \
    W_STUB_FALLBACK_COUNT=8 \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    "$PANEL" \
    --design-tmpdir "$D4" \
    --codex-present true \
    --cursor-present true \
    --plan-file "$D4/plan.txt" \
    --timeout 60 >"$D4/out.env"
grep -Fq 'DEGRADED_ROUND=true' "$D4/out.env" || fail "8 fallbacks on 14 slots should degrade"

D5="$TMP/s5"
prep "$D5"
cp "$D2/scout-plan-manifest.json" "$D5/scout-plan-manifest.json"
log5="$D5/wf.log"
: >"$log5"
DISPATCH_PLAN_REVIEW_WATERFALL_SH="$STUB" \
    WATERFALL_STUB_LOG="$log5" \
    WATERFALL_STUB_PATHS_OUT="$D5/paths.out" \
    W_STUB_STATIC_OK=false \
    W_STUB_FALLBACK_COUNT=0 \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    "$PANEL" \
    --design-tmpdir "$D5" \
    --codex-present true \
    --cursor-present true \
    --plan-file "$D5/plan.txt" \
    --timeout 60 >"$D5/out.env"
grep -Fq 'DEGRADED_ROUND=true' "$D5/out.env" || fail "static dispatch false should degrade"

echo "=== DEGRADED_ROUND from COMBINED_FALLBACK_COUNT only (14 slots, half=7) ==="
D7="$TMP/s7"
prep "$D7"
cp "$D2/scout-plan-manifest.json" "$D7/scout-plan-manifest.json"
log7="$D7/wf.log"
: >"$log7"
DISPATCH_PLAN_REVIEW_WATERFALL_SH="$STUB" \
    WATERFALL_STUB_LOG="$log7" \
    WATERFALL_STUB_PATHS_OUT="$D7/paths.out" \
    W_STUB_FALLBACK_COUNT=0 \
    W_STUB_COMBINED_FALLBACK_COUNT=8 \
    W_STUB_STATIC_OK=true \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    "$PANEL" \
    --design-tmpdir "$D7" \
    --codex-present true \
    --cursor-present true \
    --plan-file "$D7/plan.txt" \
    --timeout 60 >"$D7/out.env"
grep -Fq 'DEGRADED_ROUND=true' "$D7/out.env" || fail "COMBINED_FALLBACK_COUNT=8 with FALLBACK_COUNT=0 should degrade on 14 slots"

echo "=== quoted tmpdir path keeps ndjson valid ==="
D6="$TMP/quote\"dir"
prep "$D6"
printf '{"archetypes":[]}\n' >"$D6/scout-plan-manifest.json"
log6="$D6/wf.log"
: >"$log6"
DISPATCH_PLAN_REVIEW_WATERFALL_SH="$STUB" \
    WATERFALL_STUB_LOG="$log6" \
    WATERFALL_STUB_PATHS_OUT="$D6/paths.out" \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    "$PANEL" \
    --design-tmpdir "$D6" \
    --codex-present true \
    --cursor-present true \
    --plan-file "$D6/plan.txt" \
    --timeout 60 >"$D6/out.env"
jq -e . "$D6/plan-review-slots.ndjson" >/dev/null || fail "quoted tmpdir path must not corrupt ndjson"

echo "All dispatch-plan-review-panel harness assertions passed."
