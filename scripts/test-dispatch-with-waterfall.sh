#!/usr/bin/env bash
# Regression harness for dispatch-with-waterfall.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
TMPROOT="$(mktemp -d /tmp/larch-test-dispatch-waterfall-XXXXXX)"
trap 'rm -rf "$TMPROOT"' EXIT
export WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.05
export RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05
# Suppress launch-review.sh transient-retry backoffs (#2357 added 2/4/8s
# default jittered backoff). Tests not exercising retry timing set this to
# 0 to skip the sleep and avoid gating the harness on backoff wall time.
export LARCH_TRANSIENT_RETRY_DELAY=0

STUB_BIN="$TMPROOT/bin"
mkdir -p "$STUB_BIN"
cat > "$STUB_BIN/codex" <<'STUB'
#!/usr/bin/env bash
out=""
last=""
log="${CODEX_STUB_LOG:-}"
for arg in "$@"; do
    if [[ "$last" == "--output-last-message" ]]; then out="$arg"; fi
    last="$arg"
done
[[ -n "$out" ]] || exit 9
[[ -n "$log" ]] && printf '%s\n' "$*" >> "$log"
if [[ -n "${CODEX_STUB_COUNTER:-}" ]]; then
    n=0
    [[ -f "$CODEX_STUB_COUNTER" ]] && n=$(cat "$CODEX_STUB_COUNTER" 2>/dev/null || echo 0)
    case "$n" in ''|*[!0-9]*) n=0 ;; esac
    printf '%s\n' "$((n + 1))" > "$CODEX_STUB_COUNTER"
fi
if [[ -n "${CODEX_STUB_FAIL_OUTPUT_CONTAINS:-}" && "$out" == *"${CODEX_STUB_FAIL_OUTPUT_CONTAINS}"* ]]; then
    exit 7
fi
if [[ "${CODEX_STUB_FAIL:-false}" == "true" ]]; then
    exit 7
fi
# Default preserves prior `codex ok\n` byte-identically; callers can pass
# CODEX_STUB_RESULT_CONTENT (no trailing newline) to inject other content.
printf '%s\n' "${CODEX_STUB_RESULT_CONTENT:-codex ok}" > "$out"
STUB
cat > "$STUB_BIN/cursor" <<'STUB'
#!/usr/bin/env bash
log="${CURSOR_STUB_LOG:-}"
[[ -n "$log" ]] && printf '%s\n' "$*" >> "$log"
if [[ -n "${CURSOR_STUB_FAIL_OUTPUT_CONTAINS:-}" && "$*" == *"${CURSOR_STUB_FAIL_OUTPUT_CONTAINS}"* ]]; then
    exit 8
fi
if [[ "${CURSOR_STUB_FAIL:-false}" == "true" ]]; then
    exit 8
fi
# Build the JSON envelope with jq so metacharacters in caller-supplied
# CURSOR_STUB_RESULT_CONTENT are safely escaped. Default preserves the
# prior `cursor ok` .result value byte-identically.
jq -nc --arg r "${CURSOR_STUB_RESULT_CONTENT:-cursor ok}" \
    '{result:$r,usage:{inputTokens:1,outputTokens:1,cacheReadTokens:0,cacheWriteTokens:0}}'
STUB
cat > "$STUB_BIN/claude" <<'STUB'
#!/usr/bin/env bash
cat >/dev/null
if [[ "${CLAUDE_STUB_FAIL:-false}" == "true" ]]; then
    exit 9
fi
printf 'claude ok\n'
STUB
chmod +x "$STUB_BIN/codex" "$STUB_BIN/cursor" "$STUB_BIN/claude"

prompt="$TMPROOT/prompt.txt"
printf 'vote\n' > "$prompt"

assert_line() {
    local expected="$1" output="$2"
    grep -Fxq "$expected" <<< "$output" || { echo "FAIL: missing $expected" >&2; printf '%s\n' "$output" >&2; exit 1; }
}

manifest="$TMPROOT/slots.ndjson"
printf '{"slot":"s1","tool":"codex","output":"%s","prompt_file":"%s"}\n' "$TMPROOT/codex-slot.txt" "$prompt" > "$manifest"
out=$(PATH="$STUB_BIN:$PATH" CODEX_STUB_FAIL=true "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --codex-present true \
    --cursor-present true \
    --mode description \
    --timeout 5)
assert_line "FALLBACK_COUNT=0" "$out"
assert_line "ALL_OUTPUT_TOOLS=cursor" "$out"
grep -Fq "cursor ok" "$TMPROOT/codex-slot-phase2.txt" || { echo "FAIL: phase2 cursor output" >&2; exit 1; }

manifest="$TMPROOT/slots-phase1-ok.ndjson"
{
    printf '{"slot":"s1","tool":"codex","output":"%s","prompt_file":"%s"}\n' "$TMPROOT/phase1-codex.txt" "$prompt"
    printf '{"slot":"s2","tool":"cursor","output":"%s","prompt_file":"%s"}\n' "$TMPROOT/phase1-cursor.txt" "$prompt"
} > "$manifest"
out=$(PATH="$STUB_BIN:$PATH" "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --codex-present true \
    --cursor-present true \
    --mode description \
    --timeout 5)
assert_line "FALLBACK_COUNT=0" "$out"
assert_line "DISPATCH_OK=true" "$out"
assert_line "ALL_OUTPUT_TOOLS=codex cursor" "$out"
twoslot_list="${manifest}.output-files"
[[ -f "$twoslot_list" ]] || { echo "FAIL: two-slot default paths-file missing" >&2; exit 1; }
[[ $(wc -l < "$twoslot_list" | tr -d ' ') -eq 2 ]] || { echo "FAIL: two-slot paths-file line count" >&2; exit 1; }
grep -Fxq "$TMPROOT/phase1-codex.txt" <<< "$(sed -n '1p' "$twoslot_list")" || { echo "FAIL: two-slot paths-file slot1 order" >&2; exit 1; }
grep -Fxq "$TMPROOT/phase1-cursor.txt" <<< "$(sed -n '2p' "$twoslot_list")" || { echo "FAIL: two-slot paths-file slot2 order" >&2; exit 1; }
assert_line "ALL_OUTPUT_FILES_PATH=$twoslot_list" "$out"

manifest="$TMPROOT/slots-optional-metadata.ndjson"
printf '{"slot":"dyn-extra","tool":"cursor","output":"%s","prompt_file":"%s","weight":4,"focus_area":"architecture"}\n' "$TMPROOT/optional-metadata.txt" "$prompt" > "$manifest"
out=$(PATH="$STUB_BIN:$PATH" "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --codex-present true \
    --cursor-present true \
    --mode description \
    --timeout 5)
assert_line "FALLBACK_COUNT=0" "$out"
assert_line "DISPATCH_OK=true" "$out"
assert_line "ALL_OUTPUT_TOOLS=cursor" "$out"
grep -Fq "cursor ok" "$TMPROOT/optional-metadata.txt" || { echo "FAIL: optional metadata slot output" >&2; exit 1; }

manifest="$TMPROOT/slots-claude.ndjson"
printf '{"slot":"s1","tool":"codex","output":"%s","prompt_file":"%s"}\n' "$TMPROOT/claude-slot.txt" "$prompt" > "$manifest"
out=$(PATH="$STUB_BIN:$PATH" CODEX_STUB_FAIL=true CURSOR_STUB_FAIL=true "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --codex-present true \
    --cursor-present true \
    --mode description \
    --timeout 5)
assert_line "FALLBACK_COUNT=1" "$out"
assert_line "ALL_OUTPUT_TOOLS=claude" "$out"
grep -Fq "claude ok" "$TMPROOT/claude-slot-phase3.txt" || { echo "FAIL: phase3 claude output" >&2; exit 1; }

manifest="$TMPROOT/slots-absent.ndjson"
printf '{"slot":"s1","tool":"codex","output":"%s","prompt_file":"%s"}\n' "$TMPROOT/absent-slot.txt" "$prompt" > "$manifest"
out=$(PATH="$STUB_BIN:$PATH" "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --codex-present false \
    --cursor-present false \
    --mode description \
    --timeout 5)
assert_line "FALLBACK_COUNT=1" "$out"
assert_line "ALL_OUTPUT_TOOLS=claude" "$out"

# Test: Phase-3 hard failure — both external tools absent and Claude stub fails.
# DISPATCH_OK must be false when Phase 3 Claude slot fails.
manifest="$TMPROOT/slots-hardfail.ndjson"
printf '{"slot":"s1","tool":"codex","output":"%s","prompt_file":"%s"}\n' "$TMPROOT/hardfail-slot.txt" "$prompt" > "$manifest"
out=$(PATH="$STUB_BIN:$PATH" CLAUDE_STUB_FAIL=true "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --codex-present false \
    --cursor-present false \
    --mode description \
    --timeout 5)
assert_line "DISPATCH_OK=false" "$out"
assert_line "FALLBACK_COUNT=1" "$out"

# Test: WARN threshold — fallback count exceeds LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD.
# With threshold=1 and 2 slots both falling through to Claude, WARN must be emitted.
manifest="$TMPROOT/slots-warn.ndjson"
{
    printf '{"slot":"s1","tool":"codex","output":"%s","prompt_file":"%s"}\n' "$TMPROOT/warn-slot1.txt" "$prompt"
    printf '{"slot":"s2","tool":"cursor","output":"%s","prompt_file":"%s"}\n' "$TMPROOT/warn-slot2.txt" "$prompt"
} > "$manifest"
out=$(PATH="$STUB_BIN:$PATH" LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD=1 "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --codex-present false \
    --cursor-present false \
    --mode description \
    --timeout 5)
assert_line "FALLBACK_COUNT=2" "$out"
grep -Fq "WARN=cost-fallback-exceeded-threshold" <<< "$out" || { echo "FAIL: missing WARN=cost-fallback-exceeded-threshold" >&2; printf '%s\n' "$out" >&2; exit 1; }
assert_line "DISPATCH_OK=true" "$out"

manifest="$TMPROOT/slots-invalid.ndjson"
printf '{"slot":"bad","tool":"codex","output":"%s","agent":1}\n' "$TMPROOT/invalid.txt" > "$manifest"
set +e
PATH="$STUB_BIN:$PATH" "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --codex-present true \
    --cursor-present true \
    --mode description \
    --timeout 5 >/dev/null 2>"$TMPROOT/invalid.stderr"
rc=$?
set -e
[[ "$rc" -eq 2 ]] || { echo "FAIL: invalid slot schema exit=$rc" >&2; exit 1; }
grep -Fq 'invalid slot row' "$TMPROOT/invalid.stderr" || { echo "FAIL: invalid slot schema stderr" >&2; exit 1; }

notice="$TMPROOT/competition-notice.md"
printf 'Custom notice text\n' > "$notice"
manifest="$TMPROOT/slots-competition.ndjson"
printf '{"slot":"s1","tool":"codex","output":"%s","agent":"%s"}\n' \
    "$TMPROOT/competition-slot.txt" "$REPO_ROOT/agents/reviewer-structure.md" > "$manifest"
codex_log="$TMPROOT/codex-competition.log"
out=$(PATH="$STUB_BIN:$PATH" CODEX_STUB_LOG="$codex_log" "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --codex-present true \
    --cursor-present true \
    --mode diff \
    --diff-file "$prompt" \
    --competition-notice \
    --competition-notice-file "$notice" \
    --timeout 5)
assert_line "DISPATCH_OK=true" "$out"
grep -Fq 'Competition notice' "$codex_log" || { echo "FAIL: missing competition notice block" >&2; exit 1; }
grep -Fq 'Custom notice text' "$codex_log" || { echo "FAIL: missing competition notice file contents" >&2; exit 1; }

manifest="$TMPROOT/slots-pathsfile.ndjson"
printf '{"slot":"s1","tool":"codex","output":"%s","prompt_file":"%s"}\n' "$TMPROOT/pf-codex.txt" "$prompt" > "$manifest"
override="$TMPROOT/override-output-files.list"
out=$(PATH="$STUB_BIN:$PATH" "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --paths-file "$override" \
    --codex-present true \
    --cursor-present true \
    --mode description \
    --timeout 5)
assert_line "ALL_OUTPUT_FILES_PATH=$override" "$out"
[[ -f "$override" ]] || { echo "FAIL: override paths-file missing" >&2; exit 1; }
grep -Fxq "$TMPROOT/pf-codex.txt" "$override" || { echo "FAIL: override paths-file content" >&2; exit 1; }

manifest="$TMPROOT/slots-default-paths.ndjson"
printf '{"slot":"s1","tool":"codex","output":"%s","prompt_file":"%s"}\n' "$TMPROOT/dp-codex.txt" "$prompt" > "$manifest"
out=$(PATH="$STUB_BIN:$PATH" "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --codex-present true \
    --cursor-present true \
    --mode description \
    --timeout 5)
default_list="${manifest}.output-files"
[[ -f "$default_list" ]] || { echo "FAIL: default paths-file missing at $default_list" >&2; exit 1; }
assert_line "ALL_OUTPUT_FILES_PATH=$default_list" "$out"
grep -Fxq "$TMPROOT/dp-codex.txt" "$default_list" || { echo "FAIL: default paths-file line" >&2; exit 1; }

manifest_space="$TMPROOT/slots space.ndjson"
space_out="$TMPROOT/with space out.txt"
command -v jq >/dev/null 2>&1 || { echo "FAIL: jq required for paths-file shape tests" >&2; exit 1; }
jq -cn --arg slot "s-space" --arg out "$space_out" --arg pf "$prompt" \
    '{slot:$slot, tool:"cursor", output:$out, prompt_file:$pf}' > "$manifest_space"
out=$(PATH="$STUB_BIN:$PATH" "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest_space" \
    --codex-present true \
    --cursor-present true \
    --mode description \
    --timeout 5)
paths_line=$(printf '%s\n' "$out" | grep '^ALL_OUTPUT_FILES=' || true)
paths_kv=$(printf '%s\n' "$out" | grep '^ALL_OUTPUT_FILES_PATH=' || true)
[[ -n "$paths_kv" ]] || { echo "FAIL: missing ALL_OUTPUT_FILES_PATH" >&2; exit 1; }
list_path="${paths_kv#ALL_OUTPUT_FILES_PATH=}"
[[ -f "$list_path" ]] || { echo "FAIL: paths list file" >&2; exit 1; }
expected_final=$(printf '%s\n' "$out" | awk -F= '$1=="ALL_OUTPUT_FILES"{print substr($0,index($0,"=")+1);exit}')
grep -Fxq "$expected_final" "$list_path" || { echo "FAIL: paths-file line must match ALL_OUTPUT_FILES final path" >&2; exit 1; }
[[ $(wc -l < "$list_path" | tr -d ' ') -eq 1 ]] || { echo "FAIL: paths-file must be exactly one line" >&2; exit 1; }
case "$paths_line" in
    *"$expected_final"*) ;;
    *)
        echo "FAIL: ALL_OUTPUT_FILES KV should preserve embedded-space final path" >&2
        printf '%s\n' "$paths_line" >&2
        exit 1
        ;;
esac

manifest_empty="$TMPROOT/empty-slots.ndjson"
: > "$manifest_empty"
set +e
PATH="$STUB_BIN:$PATH" "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest_empty" \
    --codex-present true \
    --cursor-present true \
    --mode description \
    --timeout 5 >/dev/null 2>"$TMPROOT/empty-slots.stderr"
rc_empty=$?
set -e
[[ "$rc_empty" -eq 2 ]] || { echo "FAIL: empty slots exit=$rc_empty" >&2; exit 1; }
grep -Fq 'no slot rows' "$TMPROOT/empty-slots.stderr" || { echo "FAIL: empty slots stderr" >&2; exit 1; }
[[ ! -f "${manifest_empty}.output-files" ]] || { echo "FAIL: empty slots must not write paths-file" >&2; exit 1; }

bad_nl_out="$TMPROOT/bad-newline-out.txt"
manifest_nl="$TMPROOT/slots-newline.ndjson"
jq -cn --arg out "$bad_nl_out" --arg pf "$prompt" \
    '{slot:"s-bad", tool:"codex", output: ($out + "\nBAD"), prompt_file:$pf}' > "$manifest_nl"
set +e
PATH="$STUB_BIN:$PATH" "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest_nl" \
    --codex-present true \
    --cursor-present true \
    --mode description \
    --timeout 5 >/dev/null 2>"$TMPROOT/newline.stderr"
rc_nl=$?
set -e
[[ "$rc_nl" -eq 2 ]] || { echo "FAIL: newline in output path exit=$rc_nl" >&2; exit 1; }
grep -Fq 'newline or carriage return' "$TMPROOT/newline.stderr" || { echo "FAIL: newline stderr" >&2; exit 1; }

manifest_cr="$TMPROOT/slots-cr.ndjson"
jq -cn --arg out "$(printf 'x\ry')" --arg pf "$prompt" \
    '{slot:"s-cr", tool:"codex", output:$out, prompt_file:$pf}' > "$manifest_cr"
set +e
PATH="$STUB_BIN:$PATH" "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest_cr" \
    --codex-present true \
    --cursor-present true \
    --mode description \
    --timeout 5 >/dev/null 2>"$TMPROOT/cr.stderr"
rc_cr=$?
set -e
[[ "$rc_cr" -eq 2 ]] || { echo "FAIL: CR in output path exit=$rc_cr" >&2; exit 1; }
grep -Fq 'newline or carriage return' "$TMPROOT/cr.stderr" || { echo "FAIL: CR-in-path stderr" >&2; exit 1; }

# --- --require-result-pattern tests ---

# Case A: pattern-mismatch on the primary tool falls through to phase 2.
# Cursor's `STATUS=OK` returns narration only; codex (phase 2) returns a
# valid `## Recommendation` heading. Final tool must be codex, no phase-3
# Claude fallback fires, and the dispatcher reports DISPATCH_OK=true.
manifest="$TMPROOT/slots-pattern-fallback.ndjson"
printf '{"slot":"s1","tool":"cursor","output":"%s","prompt_file":"%s"}\n' \
    "$TMPROOT/pattern-fallback-slot.txt" "$prompt" > "$manifest"
out=$(PATH="$STUB_BIN:$PATH" \
    CURSOR_STUB_RESULT_CONTENT='narration only, no heading' \
    CODEX_STUB_RESULT_CONTENT=$'## Recommendation\nsplit' \
    "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --codex-present true \
    --cursor-present true \
    --mode description \
    --require-result-pattern '^[[:space:]]*## Recommendation' \
    --timeout 5)
assert_line "FALLBACK_COUNT=0" "$out"
assert_line "ALL_OUTPUT_TOOLS=codex" "$out"
assert_line "DISPATCH_OK=true" "$out"
grep -Fq '## Recommendation' "$TMPROOT/pattern-fallback-slot-phase2.txt" \
    || { echo "FAIL: phase2 codex did not produce Recommendation heading" >&2; exit 1; }

# Case B: STATUS=cap_hit bypasses the pattern gate (token-budget skip is
# terminal). Cursor returns `STATUS=cap_hit\n...` as its `.result`, which
# collect-agent-results.sh promotes to STATUS=cap_hit. Slot settles on the
# assigned primary tool; no phase-2 launch occurs.
manifest="$TMPROOT/slots-pattern-caphit.ndjson"
printf '{"slot":"s1","tool":"cursor","output":"%s","prompt_file":"%s"}\n' \
    "$TMPROOT/pattern-caphit-slot.txt" "$prompt" > "$manifest"
codex_caphit_log="$TMPROOT/codex-caphit.log"
: >"$codex_caphit_log"
out=$(PATH="$STUB_BIN:$PATH" \
    CURSOR_STUB_RESULT_CONTENT=$'STATUS=cap_hit\nbudget exceeded' \
    CODEX_STUB_LOG="$codex_caphit_log" \
    "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --codex-present true \
    --cursor-present true \
    --mode description \
    --require-result-pattern '^[[:space:]]*## Recommendation' \
    --timeout 5)
assert_line "FALLBACK_COUNT=0" "$out"
assert_line "ALL_OUTPUT_TOOLS=cursor" "$out"
assert_line "DISPATCH_OK=true" "$out"
[[ ! -s "$codex_caphit_log" ]] || { echo "FAIL: cap_hit must not advance to phase 2 (codex stub ran)" >&2; cat "$codex_caphit_log" >&2; exit 1; }

# Case C: invalid ERE exits 2 before any slot launches.
manifest="$TMPROOT/slots-pattern-invalid.ndjson"
printf '{"slot":"s1","tool":"codex","output":"%s","prompt_file":"%s"}\n' \
    "$TMPROOT/pattern-invalid-slot.txt" "$prompt" > "$manifest"
codex_invalid_log="$TMPROOT/codex-invalid.log"
cursor_invalid_log="$TMPROOT/cursor-invalid.log"
: >"$codex_invalid_log"
: >"$cursor_invalid_log"
set +e
PATH="$STUB_BIN:$PATH" \
    CODEX_STUB_LOG="$codex_invalid_log" \
    CURSOR_STUB_LOG="$cursor_invalid_log" \
    "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --codex-present true \
    --cursor-present true \
    --mode description \
    --require-result-pattern '[' \
    --timeout 5 >/dev/null 2>"$TMPROOT/pattern-invalid.stderr"
rc_pat=$?
set -e
[[ "$rc_pat" -eq 2 ]] || { echo "FAIL: invalid ERE pattern exit=$rc_pat" >&2; exit 1; }
grep -Fq 'is not a valid ERE' "$TMPROOT/pattern-invalid.stderr" \
    || { echo "FAIL: invalid ERE stderr message" >&2; cat "$TMPROOT/pattern-invalid.stderr" >&2; exit 1; }
[[ ! -s "$codex_invalid_log" ]] || { echo "FAIL: invalid ERE must not launch codex" >&2; exit 1; }
[[ ! -s "$cursor_invalid_log" ]] || { echo "FAIL: invalid ERE must not launch cursor" >&2; exit 1; }

# --- fallback_group dedup tests ---

counter_value() {
    local file="$1"
    [[ -f "$file" ]] || { printf '0\n'; return; }
    cat "$file"
}

manifest="$TMPROOT/slots-dedup-two-cursor.ndjson"
{
    jq -cn --arg out "$TMPROOT/dedup-a.txt" --arg pf "$prompt" \
        '{slot:"dedup-a",tool:"cursor",output:$out,prompt_file:$pf,fallback_group:"dedup-g"}'
    jq -cn --arg out "$TMPROOT/dedup-b.txt" --arg pf "$prompt" \
        '{slot:"dedup-b",tool:"cursor",output:$out,prompt_file:$pf,fallback_group:"dedup-g"}'
} >"$manifest"
codex_dedup_log="$TMPROOT/codex-dedup.log"
codex_dedup_counter="$TMPROOT/codex-dedup.count"
out=$(PATH="$STUB_BIN:$PATH" \
    CURSOR_STUB_RESULT_CONTENT='narration only' \
    CODEX_STUB_RESULT_CONTENT=$'## Recommendation\nsplit' \
    CODEX_STUB_LOG="$codex_dedup_log" \
    CODEX_STUB_COUNTER="$codex_dedup_counter" \
    "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --codex-present true \
    --cursor-present true \
    --mode description \
    --require-result-pattern '^[[:space:]]*## Recommendation' \
    --timeout 5)
assert_line "FALLBACK_COUNT=0" "$out"
assert_line "ALL_OUTPUT_TOOLS=codex codex" "$out"
[[ "$(counter_value "$codex_dedup_counter")" == "1" ]] || { echo "FAIL: grouped phase2 dedup should launch codex once" >&2; cat "$codex_dedup_log" >&2; exit 1; }
[[ -f "$TMPROOT/dedup-b.txt.dedup" ]] || { echo "FAIL: reused slot sidecar missing" >&2; exit 1; }
grep -Fxq 'DEDUPE_REUSED_FROM=dedup-a' "$TMPROOT/dedup-b.txt.dedup" || { echo "FAIL: reused-from sidecar" >&2; cat "$TMPROOT/dedup-b.txt.dedup" >&2; exit 1; }
grep -Fxq 'DEDUPE_REUSED_TOOL=codex' "$TMPROOT/dedup-b.txt.dedup" || { echo "FAIL: reused-tool sidecar" >&2; cat "$TMPROOT/dedup-b.txt.dedup" >&2; exit 1; }
grep -Fq '## Recommendation' "$TMPROOT/dedup-b.txt" || { echo "FAIL: reused slot output not copied" >&2; exit 1; }
grep -Fxq "$TMPROOT/dedup-b.txt" "${manifest}.output-files" || { echo "FAIL: reused slot not settled in output files list" >&2; exit 1; }
[[ ! -f "$TMPROOT/dedup-b-phase3.txt" ]] || { echo "FAIL: reused slot must not enter phase3" >&2; exit 1; }
first_run_group_ledger="$TMPROOT/waterfall-group-results.tsv"
[[ -s "$first_run_group_ledger" ]] || { echo "FAIL: first grouped run should write group ledger" >&2; exit 1; }
rm -f "$TMPROOT/dedup-a.txt" "$TMPROOT/dedup-a.txt.dedup" "$TMPROOT/dedup-b.txt" "$TMPROOT/dedup-b.txt.dedup" "${manifest}.output-files"
codex_dedup_second_log="$TMPROOT/codex-dedup-second.log"
codex_dedup_second_counter="$TMPROOT/codex-dedup-second.count"
out=$(PATH="$STUB_BIN:$PATH" \
    CURSOR_STUB_RESULT_CONTENT='narration only' \
    CODEX_STUB_RESULT_CONTENT=$'## Recommendation\nsecond split' \
    CODEX_STUB_LOG="$codex_dedup_second_log" \
    CODEX_STUB_COUNTER="$codex_dedup_second_counter" \
    "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --codex-present true \
    --cursor-present true \
    --mode description \
    --require-result-pattern '^[[:space:]]*## Recommendation' \
    --timeout 5)
assert_line "FALLBACK_COUNT=0" "$out"
assert_line "DISPATCH_OK=true" "$out"
assert_line "ALL_OUTPUT_TOOLS=codex codex" "$out"
[[ "$(counter_value "$codex_dedup_second_counter")" == "1" ]] || { echo "FAIL: grouped rerun should launch fresh codex once" >&2; cat "$codex_dedup_second_log" >&2; exit 1; }
grep -Fq 'second split' "$TMPROOT/dedup-b.txt" || { echo "FAIL: rerun reused stale grouped output" >&2; exit 1; }

manifest="$TMPROOT/slots-dedup-phase1-ok.ndjson"
{
    jq -cn --arg out "$TMPROOT/phase1-ok-codex.txt" --arg pf "$prompt" \
        '{slot:"phase1-codex",tool:"codex",output:$out,prompt_file:$pf,fallback_group:"phase1-g"}'
    jq -cn --arg out "$TMPROOT/phase1-bad-cursor.txt" --arg pf "$prompt" \
        '{slot:"phase1-cursor",tool:"cursor",output:$out,prompt_file:$pf,fallback_group:"phase1-g"}'
} >"$manifest"
codex_phase1_log="$TMPROOT/codex-phase1-ok.log"
codex_phase1_counter="$TMPROOT/codex-phase1-ok.count"
out=$(PATH="$STUB_BIN:$PATH" \
    CURSOR_STUB_RESULT_CONTENT='narration only' \
    CODEX_STUB_RESULT_CONTENT=$'## Recommendation\nsplit' \
    CODEX_STUB_LOG="$codex_phase1_log" \
    CODEX_STUB_COUNTER="$codex_phase1_counter" \
    "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --codex-present true \
    --cursor-present true \
    --mode description \
    --require-result-pattern '^[[:space:]]*## Recommendation' \
    --timeout 5)
assert_line "FALLBACK_COUNT=0" "$out"
assert_line "DISPATCH_OK=true" "$out"
assert_line "ALL_OUTPUT_TOOLS=codex codex" "$out"
[[ "$(counter_value "$codex_phase1_counter")" == "1" ]] || { echo "FAIL: phase1 OK peer should avoid phase2 codex launch" >&2; cat "$codex_phase1_log" >&2; exit 1; }
[[ ! -f "$TMPROOT/phase1-bad-cursor-phase2.txt" ]] || { echo "FAIL: phase1 peer reuse should not create phase2 output" >&2; exit 1; }
grep -Fxq 'DEDUPE_REUSED_FROM=phase1-codex' "$TMPROOT/phase1-bad-cursor.txt.dedup" || { echo "FAIL: phase1 OK reuse sidecar" >&2; exit 1; }
grep -Fq '## Recommendation' "$TMPROOT/phase1-bad-cursor.txt" || { echo "FAIL: phase1 reused output not copied" >&2; exit 1; }

manifest="$TMPROOT/slots-dedup-caphit.ndjson"
{
    jq -cn --arg out "$TMPROOT/caphit-codex.txt" --arg pf "$prompt" \
        '{slot:"caphit-codex",tool:"codex",output:$out,prompt_file:$pf,fallback_group:"caphit-g"}'
    jq -cn --arg out "$TMPROOT/caphit-cursor.txt" --arg pf "$prompt" \
        '{slot:"caphit-cursor",tool:"cursor",output:$out,prompt_file:$pf,fallback_group:"caphit-g"}'
} >"$manifest"
codex_caphit_dedup_log="$TMPROOT/codex-caphit-dedup.log"
codex_caphit_dedup_counter="$TMPROOT/codex-caphit-dedup.count"
out=$(PATH="$STUB_BIN:$PATH" \
    CURSOR_STUB_RESULT_CONTENT='narration only' \
    CODEX_STUB_RESULT_CONTENT=$'STATUS=cap_hit\n## Recommendation\ncap hit split' \
    CODEX_STUB_LOG="$codex_caphit_dedup_log" \
    CODEX_STUB_COUNTER="$codex_caphit_dedup_counter" \
    "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --codex-present true \
    --cursor-present true \
    --mode description \
    --require-result-pattern '^[[:space:]]*## Recommendation' \
    --timeout 5)
assert_line "FALLBACK_COUNT=0" "$out"
assert_line "DISPATCH_OK=true" "$out"
assert_line "ALL_OUTPUT_TOOLS=codex codex" "$out"
[[ "$(counter_value "$codex_caphit_dedup_counter")" == "1" ]] || { echo "FAIL: cap_hit grouped peer should reuse codex result" >&2; cat "$codex_caphit_dedup_log" >&2; exit 1; }
[[ -f "$TMPROOT/caphit-cursor.txt.dedup" ]] || { echo "FAIL: cap_hit reused slot sidecar missing" >&2; exit 1; }
grep -Fxq 'DEDUPE_REUSED_FROM=caphit-codex' "$TMPROOT/caphit-cursor.txt.dedup" || { echo "FAIL: cap_hit reused-from sidecar" >&2; cat "$TMPROOT/caphit-cursor.txt.dedup" >&2; exit 1; }
grep -Fxq 'DEDUPE_REUSED_TOOL=codex' "$TMPROOT/caphit-cursor.txt.dedup" || { echo "FAIL: cap_hit reused-tool sidecar" >&2; cat "$TMPROOT/caphit-cursor.txt.dedup" >&2; exit 1; }
grep -Fq '## Recommendation' "$TMPROOT/caphit-cursor.txt" || { echo "FAIL: cap_hit reused output not copied" >&2; exit 1; }
grep -Fq $'caphit-g\tcaphit-codex\tcodex\t' "$TMPROOT/waterfall-group-results.tsv" || { echo "FAIL: cap_hit ledger ok row missing" >&2; cat "$TMPROOT/waterfall-group-results.tsv" >&2; exit 1; }

manifest="$TMPROOT/slots-cross-group.ndjson"
{
    jq -cn --arg out "$TMPROOT/cross-a.txt" --arg pf "$prompt" \
        '{slot:"cross-a",tool:"cursor",output:$out,prompt_file:$pf,fallback_group:"cross-a"}'
    jq -cn --arg out "$TMPROOT/cross-b.txt" --arg pf "$prompt" \
        '{slot:"cross-b",tool:"cursor",output:$out,prompt_file:$pf,fallback_group:"cross-b"}'
} >"$manifest"
codex_cross_log="$TMPROOT/codex-cross.log"
codex_cross_counter="$TMPROOT/codex-cross.count"
out=$(PATH="$STUB_BIN:$PATH" \
    CURSOR_STUB_RESULT_CONTENT='narration only' \
    CODEX_STUB_RESULT_CONTENT=$'## Recommendation\nsplit' \
    CODEX_STUB_LOG="$codex_cross_log" \
    CODEX_STUB_COUNTER="$codex_cross_counter" \
    "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --codex-present true \
    --cursor-present true \
    --mode description \
    --require-result-pattern '^[[:space:]]*## Recommendation' \
    --timeout 5)
assert_line "FALLBACK_COUNT=0" "$out"
[[ "$(counter_value "$codex_cross_counter")" == "2" ]] || { echo "FAIL: cross-group slots should each launch codex" >&2; cat "$codex_cross_log" >&2; exit 1; }

manifest="$TMPROOT/slots-mixed-group.ndjson"
{
    jq -cn --arg out "$TMPROOT/mixed-a.txt" --arg pf "$prompt" \
        '{slot:"mixed-a",tool:"cursor",output:$out,prompt_file:$pf,fallback_group:"mixed-g"}'
    jq -cn --arg out "$TMPROOT/mixed-b.txt" --arg pf "$prompt" \
        '{slot:"mixed-b",tool:"cursor",output:$out,prompt_file:$pf,fallback_group:"mixed-g"}'
    jq -cn --arg out "$TMPROOT/mixed-ungrouped.txt" --arg pf "$prompt" \
        '{slot:"mixed-ungrouped",tool:"cursor",output:$out,prompt_file:$pf}'
} >"$manifest"
codex_mixed_log="$TMPROOT/codex-mixed.log"
codex_mixed_counter="$TMPROOT/codex-mixed.count"
out=$(PATH="$STUB_BIN:$PATH" \
    CURSOR_STUB_RESULT_CONTENT='narration only' \
    CODEX_STUB_RESULT_CONTENT=$'## Recommendation\nsplit' \
    CODEX_STUB_LOG="$codex_mixed_log" \
    CODEX_STUB_COUNTER="$codex_mixed_counter" \
    "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --codex-present true \
    --cursor-present true \
    --mode description \
    --require-result-pattern '^[[:space:]]*## Recommendation' \
    --timeout 5)
assert_line "FALLBACK_COUNT=0" "$out"
[[ "$(counter_value "$codex_mixed_counter")" == "2" ]] || { echo "FAIL: mixed grouped+ungrouped codex count" >&2; cat "$codex_mixed_log" >&2; exit 1; }
[[ -f "$TMPROOT/mixed-ungrouped-phase2.txt" ]] || { echo "FAIL: ungrouped legacy phase2 output missing" >&2; exit 1; }
[[ -f "$TMPROOT/mixed-b.txt.dedup" ]] || { echo "FAIL: grouped mixed reuse sidecar missing" >&2; exit 1; }

manifest="$TMPROOT/slots-invalid-fallback-group.ndjson"
jq -cn --arg out "$TMPROOT/bad-group.txt" --arg pf "$prompt" --arg fg $'bad\tgroup' \
    '{slot:"bad-group",tool:"cursor",output:$out,prompt_file:$pf,fallback_group:$fg}' >"$manifest"
set +e
bad_group_out=$(PATH="$STUB_BIN:$PATH" "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --codex-present true \
    --cursor-present true \
    --mode description \
    --timeout 5 2>"$TMPROOT/bad-group.stderr")
rc_group=$?
set -e
[[ "$rc_group" -ne 0 ]] || { echo "FAIL: invalid fallback_group should fail" >&2; exit 1; }
grep -Fxq 'STEP_FAILED=MANIFEST_VALIDATION' <<<"$bad_group_out" || { echo "FAIL: missing manifest validation stdout" >&2; printf '%s\n' "$bad_group_out" >&2; exit 1; }
grep -Fq 'fallback_group contains a tab' "$TMPROOT/bad-group.stderr" || { echo "FAIL: missing fallback_group validation stderr" >&2; cat "$TMPROOT/bad-group.stderr" >&2; exit 1; }

echo "PASS: test-dispatch-with-waterfall.sh"
