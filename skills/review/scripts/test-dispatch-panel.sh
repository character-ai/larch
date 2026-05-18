#!/usr/bin/env bash
# Regression harness for dispatch-panel.sh waterfall wiring.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)
SCRIPT="$REPO_ROOT/skills/review/scripts/dispatch-panel.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-dispatch-panel.XXXXXX")
trap 'rm -rf "$TMP"' EXIT
unset CLAUDE_PLUGIN_ROOT

STUB_BIN="$TMP/bin"
mkdir -p "$STUB_BIN"
cat > "$STUB_BIN/codex" <<'STUB'
#!/usr/bin/env bash
out=""; last=""
for arg in "$@"; do [[ "$last" == "--output-last-message" ]] && out="$arg"; last="$arg"; done
[[ -n "$out" ]] || exit 9
printf 'codex review\n' > "$out"
STUB
cat > "$STUB_BIN/cursor" <<'STUB'
#!/usr/bin/env bash
printf '{"result":"cursor review","usage":{"inputTokens":1,"outputTokens":1,"cacheReadTokens":0,"cacheWriteTokens":0}}\n'
STUB
cat > "$STUB_BIN/claude" <<'STUB'
#!/usr/bin/env bash
cat >/dev/null
printf 'claude review\n'
STUB
chmod +x "$STUB_BIN/codex" "$STUB_BIN/cursor" "$STUB_BIN/claude"

plan_file="$TMP/plan.md"
diff_file="$TMP/review.diff"
printf '# plan\n' > "$plan_file"
printf 'diff --git a/scripts/foo.sh b/scripts/foo.sh\n' > "$diff_file"

scout_launch="$TMP/scout-launch-stub.sh"
cat > "$scout_launch" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
out=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output-file) out="$2"; shift 2 ;;
        *) shift ;;
    esac
done
[[ -n "$out" ]] || exit 2
if [[ "${SCOUT_LAUNCH_FAIL:-false}" == "true" ]]; then
    printf 'STATUS=ERROR\nOUTPUT_FILE=%s\nELAPSED=0\n' "$out"
    exit 7
fi
cat "${SCOUT_LAUNCH_JSON_FILE:?SCOUT_LAUNCH_JSON_FILE required}" > "$out"
printf 'STATUS=OK\nOUTPUT_FILE=%s\nELAPSED=0\n' "$out"
STUB
chmod +x "$scout_launch"

cat > "$TMP/scout-valid4.json" <<'JSON'
{"archetypes":[
  {"name":"api-contract","focus_area":"correctness","weight":4,"rationale":"API changes are central.","prompt_body":"Check API contract compatibility."},
  {"name":"cli-flow","focus_area":"risk-integration","weight":3,"rationale":"CLI behavior changed.","prompt_body":"Check command flow and user-visible behavior."},
  {"name":"state-model","focus_area":"architecture","weight":5,"rationale":"State is shared across scripts.","prompt_body":"Check state transitions."},
  {"name":"error-paths","focus_area":"code-quality","weight":2,"rationale":"Many shell exits exist.","prompt_body":"Check error handling."}
]}
JSON
printf '{"archetypes":[]}\n' > "$TMP/scout-empty.json"

out=$(PATH="$STUB_BIN:$PATH" "$SCRIPT" \
    --mode diff \
    --review-tmpdir "$TMP/simple" \
    --codex-available true \
    --cursor-available true \
    --panel simple \
    --plan-file "$plan_file")
grep -Fq 'PANEL_MODE=waterfall' <<< "$out"
grep -Fq 'PANEL_SHAPE=simple' <<< "$out"
grep -Fq 'SLOT_COUNT=7' <<< "$out"
grep -Fq 'DISPATCH_OK=true' <<< "$out"
[[ -s "$TMP/simple/cursor-specialist-structure-output.txt" ]]
[[ -s "$TMP/simple/codex-generalist-output.txt" ]]

out=$(PATH="$STUB_BIN:$PATH" "$SCRIPT" \
    --mode diff \
    --review-tmpdir "$TMP/hard" \
    --codex-available true \
    --cursor-available true \
    --panel hard \
    --plan-file "$plan_file")
grep -Fq 'PANEL_SHAPE=hard' <<< "$out"
grep -Fq 'SLOT_COUNT=12' <<< "$out"
[[ -s "$TMP/hard/cursor-specialist-structure-output.txt" ]]
[[ -s "$TMP/hard/codex-specialist-structure-output.txt" ]]

out=$(PATH="$STUB_BIN:$PATH" SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH="$scout_launch" SCOUT_LAUNCH_JSON_FILE="$TMP/scout-valid4.json" "$SCRIPT" \
    --mode diff \
    --diff-file "$diff_file" \
    --review-tmpdir "$TMP/dynamic4" \
    --codex-available true \
    --cursor-available true \
    --panel hard \
    --plan-file "$plan_file" \
    --dynamic-archetypes 4)
grep -Fq 'SCOUT_STATUS=ok' <<< "$out"
grep -Fq 'DYNAMIC_SLOTS=4' <<< "$out"
grep -Fq 'STATIC_SLOT_COUNT=12' <<< "$out"
grep -Fq 'SLOT_COUNT=16' <<< "$out"
dyn_prompt_slots=$(grep -c '"prompt_file"' "$TMP/dynamic4/panel-manifest.ndjson")
[[ "$dyn_prompt_slots" = "4" ]] || { echo "FAIL: expected 4 dynamic prompt_file slots" >&2; exit 1; }
[[ -s "$TMP/dynamic4/dyn-api-contract-output.txt" ]]

out=$(PATH="$STUB_BIN:$PATH" SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH="$scout_launch" SCOUT_LAUNCH_JSON_FILE="$TMP/scout-empty.json" "$SCRIPT" \
    --mode diff \
    --diff-file "$diff_file" \
    --review-tmpdir "$TMP/dynamic-empty" \
    --codex-available true \
    --cursor-available true \
    --panel hard \
    --plan-file "$plan_file" \
    --dynamic-archetypes 4)
grep -Fq 'SCOUT_STATUS=empty' <<< "$out"
grep -Fq 'DYNAMIC_SLOTS=0' <<< "$out"
grep -Fq 'SLOT_COUNT=12' <<< "$out"

out=$(PATH="$STUB_BIN:$PATH" SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH="$scout_launch" SCOUT_LAUNCH_FAIL=true SCOUT_LAUNCH_JSON_FILE="$TMP/scout-valid4.json" "$SCRIPT" \
    --mode diff \
    --diff-file "$diff_file" \
    --review-tmpdir "$TMP/dynamic-fail" \
    --codex-available true \
    --cursor-available true \
    --panel hard \
    --plan-file "$plan_file" \
    --dynamic-archetypes 4)
grep -Fq 'SCOUT_STATUS=claude-failed' <<< "$out"
grep -Fq 'DYNAMIC_SLOTS=0' <<< "$out"
grep -Fq 'SLOT_COUNT=12' <<< "$out"

for bad in 5 -1 abc; do
    set +e
    PATH="$STUB_BIN:$PATH" "$SCRIPT" \
        --mode diff \
        --review-tmpdir "$TMP/bad-$bad" \
        --codex-available true \
        --cursor-available true \
        --panel hard \
        --plan-file "$plan_file" \
        --dynamic-archetypes "$bad" >/dev/null 2>/dev/null
    rc=$?
    set -e
    if [[ "$rc" -ne 2 ]]; then
        echo "FAIL: accepted invalid --dynamic-archetypes $bad" >&2
        exit 1
    fi
done

out=$(PATH="$STUB_BIN:$PATH" "$SCRIPT" \
    --mode diff \
    --review-tmpdir "$TMP/both-down" \
    --codex-available false \
    --cursor-available false \
    --panel simple \
    --plan-file "$plan_file")
grep -Fq 'DISPATCH_OK=true' <<< "$out"
claude_count=$(find "$TMP/both-down" -name '*phase3.txt' | wc -l | tr -d ' ')
[[ "$claude_count" -ge 7 ]] || { echo "FAIL: expected Claude phase3 outputs for both-down panel" >&2; exit 1; }

echo "All assertions passed."
