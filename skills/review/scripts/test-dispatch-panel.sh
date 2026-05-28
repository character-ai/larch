#!/usr/bin/env bash
# Regression harness for dispatch-panel.sh waterfall wiring.

set -euo pipefail

# Do not inherit a parent larch quiet-session/log/tmpdir environment.
# These harness cases create their own temp roots and should not try to write
# breadcrumb or quiet logs into a parent /implement session directory.
unset LARCH_BREADCRUMB_STREAM \
    LARCH_QUIET_BREADCRUMB_FD LARCH_QUIET_PID \
    LARCH_QUIET_ACTIVE LARCH_QUIET_LOG_FILE LARCH_QUIET_LOG \
    LARCH_DONE_SENTINEL LARCH_STATUS_FILE LARCH_PAIRED_PID_FILE \
    LARCH_BREADCRUMBS_SURFACED_FILE LARCH_DONE_OWNER_PID \
    IMPLEMENT_TMPDIR REVIEW_TMPDIR DESIGN_TMPDIR RESEARCH_TMPDIR 2>/dev/null || true

# --section CLI selector (closes #2349): shards the main scenarios into 3 groups.
# The scout parse-failed regression assertions live under `core` so sharded runs
# execute them once instead of once per shard. With no --section, all assertions
# still run sequentially for local-dev backward compatibility.
SECTION=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --section) SECTION="$2"; shift 2 ;;
        *) shift ;;
    esac
done
section_runs() {
    [[ -z "$SECTION" || "$SECTION" == "$1" ]]
}

export WAIT_FOR_REVIEWERS_POLL_INTERVAL="${WAIT_FOR_REVIEWERS_POLL_INTERVAL:-0.05}"
export RUN_EXTERNAL_AGENT_POLL_INTERVAL="${RUN_EXTERNAL_AGENT_POLL_INTERVAL:-0.05}"

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
printf '{not json\n' > "$TMP/scout-malformed.json"

classifier_stub="$TMP/classify-diff-mode-stub.sh"
cat > "$classifier_stub" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf 'DIFF_MODE=%s\n' "${TEST_DIFF_MODE:-generic}"
STUB
chmod +x "$classifier_stub"

if section_runs core; then
out=$(PATH="$STUB_BIN:$PATH" "$SCRIPT" \
    --mode diff \
    --review-tmpdir "$TMP/simple" \
    --codex-available true \
    --cursor-available true \
    --panel simple \
    --plan-file "$plan_file")
grep -Fq 'PANEL_MODE=waterfall' <<< "$out"
grep -Fq 'PANEL_SHAPE=simple' <<< "$out"
grep -Fq 'STATIC_SLOT_COUNT=6' <<< "$out"
grep -Fq 'SLOT_COUNT=6' <<< "$out"
grep -Fq 'DISPATCH_OK=true' <<< "$out"
[[ -s "$TMP/simple/cursor-specialist-structure-output.txt" ]]
[[ ! -e "$TMP/simple/codex-union-output.txt" ]] \
    || { echo "FAIL: simple panel must not create codex-union-output.txt" >&2; exit 1; }

simple_breadcrumbs_err="$TMP/simple-breadcrumbs.stderr"
out=$(PATH="$STUB_BIN:$PATH" "$SCRIPT" \
    --mode diff \
    --review-tmpdir "$TMP/simple-breadcrumbs" \
    --codex-available true \
    --cursor-available true \
    --panel simple \
    --plan-file "$plan_file" 2>"$simple_breadcrumbs_err")
grep -Fq '→ review: launching 6 reviewers (6 Cursor static, 0 dynamic)' "$simple_breadcrumbs_err"

out=$(PATH="$STUB_BIN:$PATH" "$SCRIPT" \
    --mode diff \
    --review-tmpdir "$TMP/hard" \
    --codex-available true \
    --cursor-available true \
    --panel hard \
    --plan-file "$plan_file")
grep -Fq 'PANEL_SHAPE=hard' <<< "$out"
grep -Fq 'STATIC_SLOT_COUNT=6' <<< "$out"
grep -Fq 'SLOT_COUNT=6' <<< "$out"
[[ -s "$TMP/hard/cursor-specialist-structure-output.txt" ]]
[[ ! -e "$TMP/hard/codex-union-output.txt" ]] \
    || { echo "FAIL: hard panel must not create codex-union-output.txt" >&2; exit 1; }

out=$(PATH="$STUB_BIN:$PATH" "$SCRIPT" \
    --mode diff \
    --review-tmpdir "$TMP/simple-round2" \
    --codex-available true \
    --cursor-available true \
    --panel simple \
    --plan-file "$plan_file" \
    --round-num 2)
grep -Fq 'STATIC_SLOT_COUNT=6' <<< "$out"
grep -Fq 'SLOT_COUNT=6' <<< "$out"
[[ ! -e "$TMP/simple-round2/codex-union-output.txt" ]]

out=$(PATH="$STUB_BIN:$PATH" "$SCRIPT" \
    --mode diff \
    --review-tmpdir "$TMP/hard-round2" \
    --codex-available true \
    --cursor-available true \
    --panel hard \
    --plan-file "$plan_file" \
    --round-num 2)
grep -Fq 'STATIC_SLOT_COUNT=6' <<< "$out"
grep -Fq 'SLOT_COUNT=6' <<< "$out"
[[ ! -e "$TMP/hard-round2/codex-union-output.txt" ]]

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
grep -Fq 'STATIC_SLOT_COUNT=6' <<< "$out"
grep -Fq 'SLOT_COUNT=10' <<< "$out"
dyn_prompt_slots=$(grep -c '"prompt_file"' "$TMP/dynamic4/panel-manifest.ndjson")
[[ "$dyn_prompt_slots" = "4" ]] || { echo "FAIL: expected 4 dynamic prompt_file slots" >&2; exit 1; }
[[ -s "$TMP/dynamic4/dyn-api-contract-output.txt" ]]
grep -Fq 'Begin your response with the literal line' \
    "$TMP/dynamic4/dynamic-archetypes/reviewer-dyn-api-contract.md" \
    || { echo "FAIL: dynamic reviewer artifact missing anti-preamble instruction" >&2; exit 1; }

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
grep -Fq 'SLOT_COUNT=6' <<< "$out"

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
grep -Fq 'SLOT_COUNT=6' <<< "$out"
grep -Fq 'SCOUT_STATUS=claude-failed' "$TMP/dynamic-fail/scout-round1-status.env"

cat > "$TMP/scout-valid8.json" <<'JSON'
{"archetypes":[
  {"name":"api-contract","focus_area":"correctness","weight":4,"rationale":"API changes are central.","prompt_body":"Check API contract compatibility."},
  {"name":"cli-flow","focus_area":"risk-integration","weight":3,"rationale":"CLI behavior changed.","prompt_body":"Check command flow and user-visible behavior."},
  {"name":"state-model","focus_area":"architecture","weight":5,"rationale":"State is shared across scripts.","prompt_body":"Check state transitions."},
  {"name":"error-paths","focus_area":"code-quality","weight":2,"rationale":"Many shell exits exist.","prompt_body":"Check error handling."},
  {"name":"auth-edges","focus_area":"security","weight":6,"rationale":"Auth edges changed.","prompt_body":"Check auth boundaries."},
  {"name":"state-recovery","focus_area":"risk-integration","weight":4,"rationale":"Recovery paths changed.","prompt_body":"Check recovery integration."},
  {"name":"migration-order","focus_area":"architecture","weight":5,"rationale":"Ordering matters.","prompt_body":"Check migration ordering."},
  {"name":"result-shape","focus_area":"correctness","weight":3,"rationale":"Result shape is user-visible.","prompt_body":"Check response shape."}
]}
JSON

seed_case_inputs "$TMP/dynamic8"
out=$(PATH="$STUB_BIN:$PATH" SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH="$scout_launch" SCOUT_LAUNCH_JSON_FILE="$TMP/scout-valid8.json" "$SCRIPT" \
    --mode diff \
    --diff-file "$TMP/dynamic8/review.diff" \
    --review-tmpdir "$TMP/dynamic8" \
    --codex-available true \
    --cursor-available true \
    --panel hard \
    --plan-file "$TMP/dynamic8/plan.md" \
    --dynamic-archetypes 8)
grep -Fq 'SCOUT_STATUS=ok' <<< "$out"
grep -Fq 'DYNAMIC_SLOTS=8' <<< "$out"
grep -Fq 'STATIC_SLOT_COUNT=6' <<< "$out"
grep -Fq 'SLOT_COUNT=14' <<< "$out"
dyn_prompt_slots=$(grep -c '"prompt_file"' "$TMP/dynamic8/panel-manifest.ndjson")
[[ "$dyn_prompt_slots" = "8" ]] || { echo "FAIL: expected 8 dynamic prompt_file slots" >&2; exit 1; }

seed_case_inputs "$TMP/dynamic-parse-failed"
issues_log="$TMP/dynamic-parse-failed/execution-issues.md"
out=$(PATH="$STUB_BIN:$PATH" LARCH_EXECUTION_ISSUES_LOG="$issues_log" SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH="$scout_launch" SCOUT_LAUNCH_JSON_FILE="$TMP/scout-malformed.json" "$SCRIPT" \
    --mode diff \
    --diff-file "$TMP/dynamic-parse-failed/review.diff" \
    --review-tmpdir "$TMP/dynamic-parse-failed" \
    --codex-available true \
    --cursor-available true \
    --panel hard \
    --plan-file "$TMP/dynamic-parse-failed/plan.md" \
    --dynamic-archetypes 4)
grep -Fq 'SCOUT_STATUS=parse-failed' <<< "$out"
grep -Fq 'SCOUT_FAIL_REASON=json_parse' <<< "$out"
grep -Fq 'DYNAMIC_SLOTS=0' <<< "$out"
grep -Fq 'SCOUT_FAIL_REASON=json_parse' "$TMP/dynamic-parse-failed/scout-round1-status.env"
[[ -s "$TMP/dynamic-parse-failed/scout-parse-failed-round1-diag.txt" ]]
grep -Fq 'scout_fail_reason=json_parse' "$TMP/dynamic-parse-failed/scout-parse-failed-round1-diag.txt"
if [[ -e "$issues_log" ]]; then
    echo "FAIL: core parse-failed should suppress harness issues-log append" >&2
    exit 1
fi

seed_case_inputs "$TMP/dynamic-parse-failed-warn"
readonly_dir="$TMP/dynamic-parse-failed-warn/readonly"
mkdir -p "$readonly_dir"
chmod 500 "$readonly_dir"
warn_log="$readonly_dir/execution-issues.md"
out=$(PATH="$STUB_BIN:$PATH" LARCH_EXECUTION_ISSUES_LOG="$warn_log" SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH="$scout_launch" SCOUT_LAUNCH_JSON_FILE="$TMP/scout-malformed.json" "$SCRIPT" \
    --mode diff \
    --diff-file "$TMP/dynamic-parse-failed-warn/review.diff" \
    --review-tmpdir "$TMP/dynamic-parse-failed-warn" \
    --codex-available true \
    --cursor-available true \
    --panel hard \
    --plan-file "$TMP/dynamic-parse-failed-warn/plan.md" \
    --dynamic-archetypes 4)
chmod 700 "$readonly_dir"
[[ -s "$TMP/dynamic-parse-failed-warn/scout-parse-failed-round1-diag.txt" ]]
if grep -Fq 'WARN=append-execution-issue failed for scout parse issue:' <<< "$out"; then
    echo "FAIL: harness parse-failed warn path should suppress append-execution-issue" >&2
    exit 1
fi

(
    prod_tmp="$(mktemp -d "${TMPDIR:-/tmp}/review-prod-warn.XXXXXX")"
    trap 'rm -rf "$prod_tmp"' EXIT
    seed_case_inputs "$prod_tmp/review"
    readonly_dir="$prod_tmp/readonly"
    mkdir -p "$readonly_dir"
    chmod 500 "$readonly_dir"
    warn_log="$readonly_dir/execution-issues.md"
    out=$(PATH="$STUB_BIN:$PATH" \
        LARCH_EXECUTION_ISSUES_LOG="$warn_log" \
        SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH="$scout_launch" \
        SCOUT_LAUNCH_JSON_FILE="$TMP/scout-malformed.json" \
        "$SCRIPT" \
        --mode diff \
        --diff-file "$prod_tmp/review/review.diff" \
        --review-tmpdir "$prod_tmp/review" \
        --codex-available true \
        --cursor-available true \
        --panel hard \
        --plan-file "$prod_tmp/review/plan.md" \
        --dynamic-archetypes 4)
    chmod 700 "$readonly_dir"
    [[ -s "$prod_tmp/review/scout-parse-failed-round1-diag.txt" ]] \
        || { echo "FAIL: production parse-failed warn path should still write local diag sidecar" >&2; exit 1; }
    grep -Fq 'WARN=append-execution-issue failed for scout parse issue:' <<< "$out" \
        || { echo "FAIL: production parse-failed warn path should emit append-execution-issue warning" >&2; exit 1; }
)

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
fi  # end section: core

if section_runs reuse; then
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
(
    unset LARCH_EXECUTION_ISSUES_LOG SESSION_ENV_PATH IMPLEMENT_TMPDIR
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
    grep -Fq 'SCOUT_STATUS=parse-failed' <<< "$out"
    grep -Fq 'SCOUT_FAIL_REASON=missing_status_sidecar' <<< "$out"
    grep -Fq 'DYNAMIC_SLOTS=0' <<< "$out"
    [[ "$(jq '.archetypes | length' "$TMP/reuse-manifest-no-status/scout-round3-manifest.json")" = "0" ]] || { echo "FAIL: missing status sidecar should clear cached scout manifest" >&2; exit 1; }
    # Verify local diag sidecar written in test tmpdir (guard suppresses parent execution-issues)
    [[ -s "$TMP/reuse-manifest-no-status/scout-parse-failed-round3-diag.txt" ]] \
        || { echo "FAIL: diag sidecar not written for missing_status_sidecar case" >&2; exit 1; }
    grep -Fq 'scout_fail_reason=missing_status_sidecar' "$TMP/reuse-manifest-no-status/scout-parse-failed-round3-diag.txt"
)

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
grep -Fq 'SCOUT_FAIL_REASON=cached_parse_failed' <<< "$out"
grep -Fq 'DYNAMIC_SLOTS=0' <<< "$out"
grep -Fq 'SCOUT_FAIL_REASON=cached_parse_failed' "$TMP/reuse-empty-with-status/scout-round5-status.env"

mkdir -p "$TMP/reuse-invalid-manifest"
seed_case_inputs "$TMP/reuse-invalid-manifest"
cat > "$TMP/reuse-invalid-manifest/scout-round6-manifest.json" <<'JSON'
{"archetypes":[{"name":"bad","focus_area":"performance","weight":1,"rationale":"r","prompt_body":"p"}]}
JSON
cat > "$TMP/reuse-invalid-manifest/scout-round6-status.env" <<'EOF'
SCOUT_STATUS=ok
SCOUT_MANIFEST=/tmp/ignored.json
EOF
(
    unset LARCH_EXECUTION_ISSUES_LOG SESSION_ENV_PATH IMPLEMENT_TMPDIR
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
    grep -Fq 'SCOUT_FAIL_REASON=dispatch_manifest_validation' <<< "$out"
    grep -Fq 'DYNAMIC_SLOTS=0' <<< "$out"
    if grep -q '"prompt_file"' "$TMP/reuse-invalid-manifest/panel-manifest.ndjson"; then
        echo "FAIL: invalid cached scout manifest should not synthesize dynamic slots" >&2
        exit 1
    fi
    # Verify local diag sidecar written in test tmpdir (guard suppresses parent execution-issues)
    [[ -s "$TMP/reuse-invalid-manifest/scout-parse-failed-round6-diag.txt" ]] \
        || { echo "FAIL: diag sidecar not written for dispatch_manifest_validation case" >&2; exit 1; }
    grep -Fq 'scout_fail_reason=dispatch_manifest_validation' "$TMP/reuse-invalid-manifest/scout-parse-failed-round6-diag.txt"
)

fi  # end section: reuse

if section_runs limits; then
seed_case_inputs "$TMP/oversized-diff"
# Multi-line padding just over the 256 KiB scout context cap (avoids one 270k-line bash read in classify/render paths).
python3 - <<'PY' > "$TMP/oversized-diff/review.diff"
print("diff --git a/a b/a")
line = "+" + ("x" * 71)
need = 262200
written = 0
while written < need:
    print(line)
    written += len(line) + 1
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
grep -Fq 'STATIC_SLOT_COUNT=6' <<< "$out"
[[ -s "$TMP/oversized-diff/cursor-specialist-structure-output.txt" ]]

parent_tmp="$TMP/implement-parent"
round_tmp="$parent_tmp/round-1"
mkdir -p "$parent_tmp/design-export" "$round_tmp"
printf 'PLAN_FILE=%s\n' "$parent_tmp/design-export/plan.txt" > "$parent_tmp/session-env.sh"
printf '# plan from parent tmpdir\n' > "$parent_tmp/design-export/plan.txt"
cp "$diff_file" "$round_tmp/review.diff"
out=$(PATH="$STUB_BIN:$PATH" SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH="$scout_launch" SCOUT_LAUNCH_JSON_FILE="$TMP/scout-valid4.json" "$SCRIPT" \
    --mode diff \
    --diff-file "$round_tmp/review.diff" \
    --review-tmpdir "$round_tmp" \
    --codex-available true \
    --cursor-available true \
    --panel hard \
    --plan-file "$parent_tmp/design-export/plan.txt" \
    --session-env-path "$parent_tmp/session-env.sh" \
    --dynamic-archetypes 4)
grep -Fq 'SCOUT_STATUS=ok' <<< "$out"
grep -Fq 'DYNAMIC_SLOTS=4' <<< "$out"

for bad in 9 -1 abc; do
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

mkdir -p "$TMP/empty-env"
# Empty export is ignored (same semantics as review-and-fix.sh / test-review-and-fix.sh).
set +e
out=$(PATH="$STUB_BIN:$PATH" LARCH_DYNAMIC_ARCHETYPES_MAX='' "$SCRIPT" \
    --mode diff \
    --review-tmpdir "$TMP/empty-env" \
    --codex-available true \
    --cursor-available true \
    --panel hard \
    --plan-file "$plan_file")
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "FAIL: empty LARCH_DYNAMIC_ARCHETYPES_MAX expected exit 0 got $rc" >&2; echo "$out" >&2; exit 1; }
grep -Fq 'DISPATCH_OK=true' <<< "$out"
grep -Fq 'SCOUT_STATUS=na' <<< "$out"
grep -Fq 'DYNAMIC_SLOTS=0' <<< "$out"

out=$(PATH="$STUB_BIN:$PATH" "$SCRIPT" \
    --mode diff \
    --review-tmpdir "$TMP/both-down" \
    --codex-available false \
    --cursor-available false \
    --panel simple \
    --plan-file "$plan_file")
grep -Fq 'DISPATCH_OK=true' <<< "$out"
claude_count=$(find "$TMP/both-down" -name '*phase3.txt' | wc -l | tr -d ' ')
[[ "$claude_count" -ge 6 ]] || { echo "FAIL: expected Claude phase3 outputs for both-down panel" >&2; exit 1; }
fi  # end section: limits

assert_emit_tally_panel() {
    local label="$1" scout_status="$2" dynamic_slots="$3" static_slot_count="$4" total_slot_count="$5"
    local dir="$TMP/emit-tally-$label"
    mkdir -p "$dir"
    printf 'ACCEPTED_COUNT=0\nREJECTED_COUNT=0\nEXONERATED_COUNT=0\nNEUTRAL_COUNT=0\n' > "$dir/tally.env"
    : > "$dir/accepted.md"
    : > "$dir/oos.md"
    "$REPO_ROOT/skills/review/scripts/emit-tally.sh" \
        --tally-file "$dir/tally.env" \
        --accepted-findings-file "$dir/accepted.md" \
        --oos-file "$dir/oos.md" \
        --review-tmpdir "$dir" \
        --round 1 \
        --mode diff \
        --scout-status "$scout_status" \
        --dynamic-slots "$dynamic_slots" \
        --static-slot-count "$static_slot_count" >/dev/null
    jq -e \
        --arg scout_status "$scout_status" \
        --argjson dynamic_slots "$dynamic_slots" \
        --argjson static_slot_count "$static_slot_count" \
        --argjson total_slot_count "$total_slot_count" \
        '.schema_version == 3
            and .panel.scout_status == $scout_status
            and .panel.dynamic_slot_count == $dynamic_slots
            and .panel.static_slot_count == $static_slot_count
            and .panel.total_slot_count == $total_slot_count' \
        "$dir/review-summary.json" >/dev/null || {
            echo "FAIL: emit-tally panel summary mismatch for $label" >&2
            exit 1
        }
}

assert_emit_tally_panel static-na na 0 7 7
assert_emit_tally_panel scout-ok ok 4 7 11
assert_emit_tally_panel scout-skipped skipped-docs-only 0 7 7

if section_runs core; then

# Regression 1: env-isolation — LARCH_EXECUTION_ISSUES_LOG set on invocation but
# REVIEW_TMPDIR lives under a test-dispatch-panel.* ancestor, so the guard must
# suppress the parent issues-log write while still writing the local diag sidecar.
env_isolation_parent="$TMP/env-isolation-parent.md"
rm -f "$env_isolation_parent"
mkdir -p "$TMP/env-isolation-test"
seed_case_inputs "$TMP/env-isolation-test"
cp "$TMP/scout-valid4.json" "$TMP/env-isolation-test/scout-round11-manifest.json"
PATH="$STUB_BIN:$PATH" \
    LARCH_EXECUTION_ISSUES_LOG="$env_isolation_parent" \
    "$SCRIPT" \
    --mode diff \
    --diff-file "$TMP/env-isolation-test/review.diff" \
    --review-tmpdir "$TMP/env-isolation-test" \
    --codex-available true \
    --cursor-available true \
    --panel hard \
    --plan-file "$TMP/env-isolation-test/plan.md" \
    --dynamic-archetypes 4 \
    --round-num 11 >/dev/null
if [[ -s "$env_isolation_parent" ]]; then
    echo "FAIL: regression1 env-isolation — parent LARCH_EXECUTION_ISSUES_LOG was written despite test-tmpdir REVIEW_TMPDIR" >&2
    exit 1
fi
[[ -s "$TMP/env-isolation-test/scout-parse-failed-round11-diag.txt" ]] \
    || { echo "FAIL: regression1 — local diag sidecar not written" >&2; exit 1; }

# Regression 2: path-guard — diag sidecar written locally but the explicit
# parent issues-log remains untouched for REVIEW_TMPDIR nested under test-dispatch-panel.*.
path_guard_issues="$TMP/path-guard-issues.md"
rm -f "$path_guard_issues"
mkdir -p "$TMP/path-guard-review"
seed_case_inputs "$TMP/path-guard-review"
cp "$TMP/scout-valid4.json" "$TMP/path-guard-review/scout-round12-manifest.json"
PATH="$STUB_BIN:$PATH" \
    LARCH_EXECUTION_ISSUES_LOG="$path_guard_issues" \
    "$SCRIPT" \
    --mode diff \
    --diff-file "$TMP/path-guard-review/review.diff" \
    --review-tmpdir "$TMP/path-guard-review" \
    --codex-available true \
    --cursor-available true \
    --panel hard \
    --plan-file "$TMP/path-guard-review/plan.md" \
    --dynamic-archetypes 4 \
    --round-num 12 >/dev/null
[[ -s "$TMP/path-guard-review/scout-parse-failed-round12-diag.txt" ]] \
    || { echo "FAIL: regression2 path-guard — local diag sidecar not written" >&2; exit 1; }
grep -Fq 'scout_fail_reason=missing_status_sidecar' "$TMP/path-guard-review/scout-parse-failed-round12-diag.txt" \
    || { echo "FAIL: regression2 path-guard — diag missing expected fail reason" >&2; exit 1; }
if [[ -s "$path_guard_issues" ]]; then
    echo "FAIL: regression2 path-guard — append-execution-issue.sh was called despite test-tmpdir REVIEW_TMPDIR" >&2
    exit 1
fi

# Regression 3: production-shape — REVIEW_TMPDIR outside any harness ancestry,
# so both the local diag sidecar and the explicit issues-log must be written.
(
    prod_tmp="$(mktemp -d "${TMPDIR:-/tmp}/review-prod-shape.XXXXXX")"
    trap 'rm -rf "$prod_tmp"' EXIT
    mkdir -p "$prod_tmp/review"
    seed_case_inputs "$prod_tmp/review"
    cp "$TMP/scout-valid4.json" "$prod_tmp/review/scout-round13-manifest.json"
    prod_issues="$prod_tmp/prod-issues.md"
    PATH="$STUB_BIN:$PATH" \
        LARCH_EXECUTION_ISSUES_LOG="$prod_issues" \
        "$SCRIPT" \
        --mode diff \
        --diff-file "$prod_tmp/review/review.diff" \
        --review-tmpdir "$prod_tmp/review" \
        --codex-available true \
        --cursor-available true \
        --panel hard \
        --plan-file "$prod_tmp/review/plan.md" \
        --dynamic-archetypes 4 \
        --round-num 13 >/dev/null
    [[ -s "$prod_tmp/review/scout-parse-failed-round13-diag.txt" ]] \
        || { echo "FAIL: regression3 prod-shape — local diag sidecar not written" >&2; exit 1; }
    grep -Fq 'Review scout dynamic archetype parse failed in round 13; reason=missing_status_sidecar' "$prod_issues" \
        || { echo "FAIL: regression3 prod-shape — execution-issues warning not written for production-shape tmpdir" >&2; exit 1; }
)

fi  # end section: core regressions

echo "All assertions passed."
