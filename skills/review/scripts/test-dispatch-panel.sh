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

seed_case_inputs() {
    local out_dir="$1"
    mkdir -p "$out_dir"
    cp "$plan_file" "$out_dir/plan.md"
    cp "$diff_file" "$out_dir/review.diff"
}

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

classifier_stub="$TMP/classify-diff-mode-stub.sh"
cat > "$classifier_stub" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf 'DIFF_MODE=%s\n' "${TEST_DIFF_MODE:-generic}"
STUB
chmod +x "$classifier_stub"

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

seed_case_inputs "$TMP/dynamic4"
out=$(PATH="$STUB_BIN:$PATH" SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH="$scout_launch" SCOUT_LAUNCH_JSON_FILE="$TMP/scout-valid4.json" "$SCRIPT" \
    --mode diff \
    --diff-file "$TMP/dynamic4/review.diff" \
    --review-tmpdir "$TMP/dynamic4" \
    --codex-available true \
    --cursor-available true \
    --panel hard \
    --plan-file "$TMP/dynamic4/plan.md" \
    --dynamic-archetypes 4)
grep -Fq 'SCOUT_STATUS=ok' <<< "$out"
grep -Fq 'DYNAMIC_SLOTS=4' <<< "$out"
grep -Fq 'STATIC_SLOT_COUNT=12' <<< "$out"
grep -Fq 'SLOT_COUNT=16' <<< "$out"
dyn_prompt_slots=$(grep -c '"prompt_file"' "$TMP/dynamic4/panel-manifest.ndjson")
[[ "$dyn_prompt_slots" = "4" ]] || { echo "FAIL: expected 4 dynamic prompt_file slots" >&2; exit 1; }
[[ -s "$TMP/dynamic4/dyn-api-contract-output.txt" ]]

seed_case_inputs "$TMP/dynamic-empty"
out=$(PATH="$STUB_BIN:$PATH" SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH="$scout_launch" SCOUT_LAUNCH_JSON_FILE="$TMP/scout-empty.json" "$SCRIPT" \
    --mode diff \
    --diff-file "$TMP/dynamic-empty/review.diff" \
    --review-tmpdir "$TMP/dynamic-empty" \
    --codex-available true \
    --cursor-available true \
    --panel hard \
    --plan-file "$TMP/dynamic-empty/plan.md" \
    --dynamic-archetypes 4)
grep -Fq 'SCOUT_STATUS=empty' <<< "$out"
grep -Fq 'DYNAMIC_SLOTS=0' <<< "$out"
grep -Fq 'SLOT_COUNT=12' <<< "$out"

seed_case_inputs "$TMP/dynamic-fail"
out=$(PATH="$STUB_BIN:$PATH" SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH="$scout_launch" SCOUT_LAUNCH_FAIL=true SCOUT_LAUNCH_JSON_FILE="$TMP/scout-valid4.json" "$SCRIPT" \
    --mode diff \
    --diff-file "$TMP/dynamic-fail/review.diff" \
    --review-tmpdir "$TMP/dynamic-fail" \
    --codex-available true \
    --cursor-available true \
    --panel hard \
    --plan-file "$TMP/dynamic-fail/plan.md" \
    --dynamic-archetypes 4)
grep -Fq 'SCOUT_STATUS=claude-failed' <<< "$out"
grep -Fq 'DYNAMIC_SLOTS=0' <<< "$out"
grep -Fq 'SLOT_COUNT=12' <<< "$out"
grep -Fq 'SCOUT_STATUS=claude-failed' "$TMP/dynamic-fail/scout-round1-status.env"

for mode in docs-only test-only generated-only; do
    seed_case_inputs "$TMP/skip-$mode"
    out=$(PATH="$STUB_BIN:$PATH" TEST_DIFF_MODE="$mode" SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH="$scout_launch" SCOUT_LAUNCH_JSON_FILE="$TMP/scout-valid4.json" \
        SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH="$scout_launch" CLASSIFY_DIFF_MODE_SH="$classifier_stub" "$SCRIPT" \
        --mode diff \
        --diff-file "$TMP/skip-$mode/review.diff" \
        --review-tmpdir "$TMP/skip-$mode" \
        --codex-available true \
        --cursor-available true \
        --panel hard \
        --plan-file "$TMP/skip-$mode/plan.md" \
        --dynamic-archetypes 4)
    grep -Fq "SCOUT_STATUS=skipped-$mode" <<< "$out"
    grep -Fq 'DYNAMIC_SLOTS=0' <<< "$out"
done

mkdir -p "$TMP/missing-diff"
cp "$plan_file" "$TMP/missing-diff/plan.md"
out=$(PATH="$STUB_BIN:$PATH" "$SCRIPT" \
    --mode diff \
    --diff-file "$TMP/missing-diff/review.diff" \
    --review-tmpdir "$TMP/missing-diff" \
    --codex-available true \
    --cursor-available true \
    --panel hard \
    --plan-file "$TMP/missing-diff/plan.md" \
    --dynamic-archetypes 4)
grep -Fq 'SCOUT_STATUS=missing-diff-file' <<< "$out"
grep -Fq 'DYNAMIC_SLOTS=0' <<< "$out"
[[ "$(jq '.archetypes | length' "$TMP/missing-diff/scout-round1-manifest.json")" = "0" ]] || { echo "FAIL: expected missing-diff scout manifest to be empty" >&2; exit 1; }

seed_case_inputs "$TMP/round-reuse"
out=$(PATH="$STUB_BIN:$PATH" SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH="$scout_launch" SCOUT_LAUNCH_JSON_FILE="$TMP/scout-valid4.json" "$SCRIPT" \
    --mode diff \
    --diff-file "$TMP/round-reuse/review.diff" \
    --review-tmpdir "$TMP/round-reuse" \
    --codex-available true \
    --cursor-available true \
    --panel hard \
    --plan-file "$TMP/round-reuse/plan.md" \
    --dynamic-archetypes 4 \
    --round-num 2)
grep -Fq "SCOUT_MANIFEST=$TMP/round-reuse/scout-round2-manifest.json" <<< "$out"
[[ -f "$TMP/round-reuse/scout-round2-manifest.json" ]] || { echo "FAIL: expected round-scoped scout manifest" >&2; exit 1; }

mkdir -p "$TMP/reuse-manifest-no-status"
seed_case_inputs "$TMP/reuse-manifest-no-status"
cp "$TMP/scout-valid4.json" "$TMP/reuse-manifest-no-status/scout-round3-manifest.json"
out=$(PATH="$STUB_BIN:$PATH" "$SCRIPT" \
    --mode diff \
    --diff-file "$TMP/reuse-manifest-no-status/review.diff" \
    --review-tmpdir "$TMP/reuse-manifest-no-status" \
    --codex-available true \
    --cursor-available true \
    --panel hard \
    --plan-file "$TMP/reuse-manifest-no-status/plan.md" \
    --dynamic-archetypes 4 \
    --round-num 3)
grep -Fq 'SCOUT_STATUS=ok' <<< "$out"
grep -Fq 'DYNAMIC_SLOTS=4' <<< "$out"

mkdir -p "$TMP/reuse-empty-no-status"
seed_case_inputs "$TMP/reuse-empty-no-status"
printf '{"archetypes":[]}\n' > "$TMP/reuse-empty-no-status/scout-round4-manifest.json"
out=$(PATH="$STUB_BIN:$PATH" "$SCRIPT" \
    --mode diff \
    --diff-file "$TMP/reuse-empty-no-status/review.diff" \
    --review-tmpdir "$TMP/reuse-empty-no-status" \
    --codex-available true \
    --cursor-available true \
    --panel hard \
    --plan-file "$TMP/reuse-empty-no-status/plan.md" \
    --dynamic-archetypes 4 \
    --round-num 4)
grep -Fq 'SCOUT_STATUS=empty' <<< "$out"
grep -Fq 'DYNAMIC_SLOTS=0' <<< "$out"

mkdir -p "$TMP/reuse-empty-with-status"
seed_case_inputs "$TMP/reuse-empty-with-status"
printf '{"archetypes":[]}\n' > "$TMP/reuse-empty-with-status/scout-round5-manifest.json"
cat > "$TMP/reuse-empty-with-status/scout-round5-status.env" <<'EOF'
SCOUT_STATUS=parse-failed
SCOUT_MANIFEST=/tmp/ignored.json
EOF
out=$(PATH="$STUB_BIN:$PATH" "$SCRIPT" \
    --mode diff \
    --diff-file "$TMP/reuse-empty-with-status/review.diff" \
    --review-tmpdir "$TMP/reuse-empty-with-status" \
    --codex-available true \
    --cursor-available true \
    --panel hard \
    --plan-file "$TMP/reuse-empty-with-status/plan.md" \
    --dynamic-archetypes 4 \
    --round-num 5)
grep -Fq 'SCOUT_STATUS=parse-failed' <<< "$out"
grep -Fq 'DYNAMIC_SLOTS=0' <<< "$out"

mkdir -p "$TMP/reuse-invalid-manifest"
seed_case_inputs "$TMP/reuse-invalid-manifest"
cat > "$TMP/reuse-invalid-manifest/scout-round6-manifest.json" <<'JSON'
{"archetypes":[{"name":"bad","focus_area":"performance","weight":1,"rationale":"r","prompt_body":"p"}]}
JSON
cat > "$TMP/reuse-invalid-manifest/scout-round6-status.env" <<'EOF'
SCOUT_STATUS=ok
SCOUT_MANIFEST=/tmp/ignored.json
EOF
out=$(PATH="$STUB_BIN:$PATH" "$SCRIPT" \
    --mode diff \
    --diff-file "$TMP/reuse-invalid-manifest/review.diff" \
    --review-tmpdir "$TMP/reuse-invalid-manifest" \
    --codex-available true \
    --cursor-available true \
    --panel hard \
    --plan-file "$TMP/reuse-invalid-manifest/plan.md" \
    --dynamic-archetypes 4 \
    --round-num 6)
grep -Fq 'SCOUT_STATUS=parse-failed' <<< "$out"
grep -Fq 'DYNAMIC_SLOTS=0' <<< "$out"
if grep -q '"prompt_file"' "$TMP/reuse-invalid-manifest/panel-manifest.ndjson"; then
    echo "FAIL: invalid cached scout manifest should not synthesize dynamic slots" >&2
    exit 1
fi

seed_case_inputs "$TMP/oversized-diff"
python3 - <<'PY' > "$TMP/oversized-diff/review.diff"
print("diff --git a/a b/a")
print("+" + "x" * 270000)
PY
out=$(PATH="$STUB_BIN:$PATH" "$SCRIPT" \
    --mode diff \
    --diff-file "$TMP/oversized-diff/review.diff" \
    --review-tmpdir "$TMP/oversized-diff" \
    --codex-available true \
    --cursor-available true \
    --panel hard \
    --plan-file "$TMP/oversized-diff/plan.md" \
    --dynamic-archetypes 4)
grep -Fq 'SCOUT_STATUS=validation-failed' <<< "$out"
grep -Fq 'DYNAMIC_SLOTS=0' <<< "$out"
grep -Fq 'STATIC_SLOT_COUNT=12' <<< "$out"
[[ -s "$TMP/oversized-diff/cursor-specialist-structure-output.txt" ]]

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
