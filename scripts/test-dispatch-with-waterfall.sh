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
if [[ "${CODEX_STUB_RESULT_INCLUDE_BASENAME:-false}" == "true" ]]; then
    printf '## Recommendation\nfresh %s\n' "$(basename "$out")" > "$out"
    exit 0
fi
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
# CURSOR_STUB_OUTPUT_TOKENS: override outputTokens (default 1); use >1000
# to exercise launch-review.sh's CURSOR_DEGRADED_RESPONSE heuristic.
jq -nc --arg r "${CURSOR_STUB_RESULT_CONTENT:-cursor ok}" \
    --argjson ot "${CURSOR_STUB_OUTPUT_TOKENS:-1}" \
    '{result:$r,usage:{inputTokens:1,outputTokens:$ot,cacheReadTokens:0,cacheWriteTokens:0}}'
STUB
cat > "$STUB_BIN/claude" <<'STUB'
#!/usr/bin/env bash
cat >/dev/null
if [[ "${CLAUDE_STUB_FAIL:-false}" == "true" ]]; then
    exit 9
fi
printf 'claude ok\n'
STUB
cat > "$STUB_BIN/cp" <<'STUB'
#!/usr/bin/env bash
real_cp="${LARCH_TEST_REAL_CP:-/bin/cp}"
counter="${CP_STUB_FAIL_COUNTER:-}"
target_contains="${CP_STUB_FAIL_TARGET_CONTAINS:-}"
fail_max=1
case "${CP_STUB_FAIL_COUNT:-}" in
    ''|*[!0-9]*) ;;
    *) fail_max="$CP_STUB_FAIL_COUNT" ;;
esac
if [[ "${1:-}" == "-p" && -n "$counter" && -n "$target_contains" && "$*" == *"$target_contains"* ]]; then
    n=0
    [[ -f "$counter" ]] && n=$(cat "$counter" 2>/dev/null || echo 0)
    case "$n" in ''|*[!0-9]*) n=0 ;; esac
    printf '%s\n' "$((n + 1))" > "$counter"
    if [[ "$n" -lt "$fail_max" ]]; then
        exit 73
    fi
fi
exec "$real_cp" "$@"
STUB
chmod +x "$STUB_BIN/codex" "$STUB_BIN/cursor" "$STUB_BIN/claude" "$STUB_BIN/cp"

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
[[ -f "$TMPROOT/hardfail-slot-phase3.txt.launch-stderr" ]] \
    || { echo "FAIL: phase-3 launcher stderr sidecar missing" >&2; exit 1; }

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
assert_line "COMBINED_FALLBACK_COUNT=2" "$out"
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
# launch-review.sh expands --agent-file before invoking Codex, so this harness
# validates the prompt sidecar plus rendered prompt body instead of a literal
# --agent-file argv token in CODEX_STUB_LOG.
grep -Fq 'AGENT_FILE=' "$TMPROOT/competition-slot.txt.prompt" || { echo "FAIL: competition-notice prompt sidecar missing AGENT_FILE (launch-review --agent-file)" >&2; exit 1; }
grep -Fq 'agents/reviewer-structure.md' "$TMPROOT/competition-slot.txt.prompt" || { echo "FAIL: competition-notice prompt sidecar missing agent path" >&2; cat "$TMPROOT/competition-slot.txt.prompt" >&2; exit 1; }
grep -Fq 'Structure, KISS, and Maintainability' "$codex_log" || { echo "FAIL: competition-notice codex prompt missing rendered agent body" >&2; cat "$codex_log" >&2; exit 1; }
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

# --- --require-first-line-pattern tests ---

# Case D: first non-blank line match settles on the primary tool.
manifest="$TMPROOT/slots-first-line-match.ndjson"
printf '{"slot":"s1","tool":"cursor","output":"%s","prompt_file":"%s"}\n' \
    "$TMPROOT/first-line-match-slot.txt" "$prompt" > "$manifest"
out=$(PATH="$STUB_BIN:$PATH" \
    CURSOR_STUB_RESULT_CONTENT=$'schema_version\tscope\tseverity\n1\tplan\timportant' \
    "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --codex-present true \
    --cursor-present true \
    --mode description \
    --require-first-line-pattern '^[[:space:]]*schema_version' \
    --timeout 5)
assert_line "FALLBACK_COUNT=0" "$out"
assert_line "ALL_OUTPUT_TOOLS=cursor" "$out"
assert_line "DISPATCH_OK=true" "$out"

# Case E: first-line miss falls through even when a matching TSV header appears later.
manifest="$TMPROOT/slots-first-line-fallback.ndjson"
printf '{"slot":"s1","tool":"cursor","output":"%s","prompt_file":"%s"}\n' \
    "$TMPROOT/first-line-fallback-slot.txt" "$prompt" > "$manifest"
out=$(PATH="$STUB_BIN:$PATH" \
    CURSOR_STUB_RESULT_CONTENT=$'operational narration first\nschema_version\tscope\tseverity\n1\tplan\timportant' \
    CODEX_STUB_RESULT_CONTENT=$'schema_version\tscope\tseverity\n1\tplan\timportant' \
    "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --codex-present true \
    --cursor-present true \
    --mode description \
    --require-first-line-pattern '^[[:space:]]*schema_version' \
    --timeout 5)
assert_line "FALLBACK_COUNT=0" "$out"
assert_line "ALL_OUTPUT_TOOLS=codex" "$out"
assert_line "DISPATCH_OK=true" "$out"
grep -Fxq 'operational narration first' "$TMPROOT/first-line-fallback-slot.txt" \
    || { echo "FAIL: phase1 first-line miss fixture missing" >&2; exit 1; }
grep -Fq 'schema_version' "$TMPROOT/first-line-fallback-slot-phase2.txt" \
    || { echo "FAIL: phase2 first-line fallback did not produce schema header" >&2; exit 1; }

# Case F: invalid first-line ERE exits 2 before any slot launches.
manifest="$TMPROOT/slots-first-line-invalid.ndjson"
printf '{"slot":"s1","tool":"codex","output":"%s","prompt_file":"%s"}\n' \
    "$TMPROOT/first-line-invalid-slot.txt" "$prompt" > "$manifest"
codex_first_line_invalid_log="$TMPROOT/codex-first-line-invalid.log"
cursor_first_line_invalid_log="$TMPROOT/cursor-first-line-invalid.log"
: >"$codex_first_line_invalid_log"
: >"$cursor_first_line_invalid_log"
set +e
PATH="$STUB_BIN:$PATH" \
    CODEX_STUB_LOG="$codex_first_line_invalid_log" \
    CURSOR_STUB_LOG="$cursor_first_line_invalid_log" \
    "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --codex-present true \
    --cursor-present true \
    --mode description \
    --require-first-line-pattern '[' \
    --timeout 5 >/dev/null 2>"$TMPROOT/first-line-invalid.stderr"
rc_first_line_pat=$?
set -e
[[ "$rc_first_line_pat" -eq 2 ]] || { echo "FAIL: invalid first-line ERE pattern exit=$rc_first_line_pat" >&2; exit 1; }
grep -Fq -- '--require-first-line-pattern is not a valid ERE' "$TMPROOT/first-line-invalid.stderr" \
    || { echo "FAIL: invalid first-line ERE stderr message" >&2; cat "$TMPROOT/first-line-invalid.stderr" >&2; exit 1; }
[[ ! -s "$codex_first_line_invalid_log" ]] || { echo "FAIL: invalid first-line ERE must not launch codex" >&2; exit 1; }
[[ ! -s "$cursor_first_line_invalid_log" ]] || { echo "FAIL: invalid first-line ERE must not launch cursor" >&2; exit 1; }

# --- --no-fallback single-phase tests ---

manifest="$TMPROOT/slots-no-fallback-drop.ndjson"
printf '{"slot":"drop-me","tool":"codex","output":"%s","prompt_file":"%s"}\n' \
    "$TMPROOT/no-fallback-drop.txt" "$prompt" >"$manifest"
out=$(PATH="$STUB_BIN:$PATH" CODEX_STUB_FAIL=true \
    "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --codex-present true \
    --cursor-present false \
    --no-fallback \
    --mode description \
    --timeout 5)
assert_line "DISPATCH_OK=true" "$out"
assert_line "STATIC_DISPATCH_OK=true" "$out"
assert_line "ALL_SLOTS_DROPPED=true" "$out"
assert_line "FALLBACK_COUNT=0" "$out"
assert_line "ALL_OUTPUT_FILES=" "$out"
[[ ! -s "${manifest}.output-files" ]] || { echo "FAIL: no-fallback drop should emit empty paths-file" >&2; cat "${manifest}.output-files" >&2; exit 1; }
[[ ! -f "$TMPROOT/no-fallback-drop-phase2.txt" ]] || { echo "FAIL: no-fallback drop must not create phase2 output" >&2; exit 1; }
[[ ! -f "$TMPROOT/no-fallback-drop-phase3.txt" ]] || { echo "FAIL: no-fallback drop must not create phase3 output" >&2; exit 1; }

manifest="$TMPROOT/slots-no-fallback-keep.ndjson"
printf '{"slot":"keep-me","tool":"codex","output":"%s","prompt_file":"%s"}\n' \
    "$TMPROOT/no-fallback-keep.txt" "$prompt" >"$manifest"
out=$(PATH="$STUB_BIN:$PATH" \
    "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --codex-present true \
    --cursor-present false \
    --no-fallback \
    --mode description \
    --timeout 5)
assert_line "DISPATCH_OK=true" "$out"
assert_line "ALL_OUTPUT_TOOLS=codex" "$out"
grep -Fxq "$TMPROOT/no-fallback-keep.txt" "${manifest}.output-files" \
    || { echo "FAIL: no-fallback keep should list succeeded path" >&2; exit 1; }
[[ -f "$TMPROOT/no-fallback-keep.txt.done" ]] || { echo "FAIL: no-fallback keep missing .done sentinel" >&2; exit 1; }

_collect_paths="${manifest}.output-files"
_collect_start=$(date +%s)
_collect_out=$(LARCH_QUIET_DISABLE=1 bash "$REPO_ROOT/scripts/collect-agent-results.sh" \
    --timeout 5 \
    --paths-file "$_collect_paths" 2>&1) || true
_collect_elapsed=$(( $(date +%s) - _collect_start ))
[[ "$_collect_elapsed" -lt 4 ]] || { echo "FAIL: real collect on no-fallback keep took too long (${_collect_elapsed}s)" >&2; exit 1; }
if grep -Fq 'STATUS=SENTINEL_TIMEOUT' <<<"$_collect_out"; then
    echo "FAIL: real collect on no-fallback keep must not SENTINEL_TIMEOUT" >&2
    printf '%s\n' "$_collect_out" >&2
    exit 1
fi

manifest="$TMPROOT/slots-no-fallback-absent.ndjson"
printf '{"slot":"absent-codex","tool":"codex","output":"%s","prompt_file":"%s"}\n' \
    "$TMPROOT/no-fallback-absent.txt" "$prompt" >"$manifest"
_start=$(date +%s)
out=$(PATH="$STUB_BIN:$PATH" \
    "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --codex-present false \
    --cursor-present false \
    --no-fallback \
    --mode description \
    --timeout 5)
_elapsed=$(( $(date +%s) - _start ))
assert_line "DISPATCH_OK=true" "$out"
assert_line "STATIC_DISPATCH_OK=true" "$out"
assert_line "ALL_SLOTS_DROPPED=true" "$out"
[[ "$_elapsed" -lt 4 ]] || { echo "FAIL: no-fallback absent slot took too long (${_elapsed}s)" >&2; exit 1; }
if grep -Fq 'SENTINEL_TIMEOUT' <<<"$out"; then
    echo "FAIL: no-fallback absent must not emit SENTINEL_TIMEOUT" >&2
    exit 1
fi
_absent_paths="${manifest}.output-files"
_collect_absent_start=$(date +%s)
_collect_absent_out=$(LARCH_QUIET_DISABLE=1 bash "$REPO_ROOT/scripts/collect-agent-results.sh" \
    --timeout 5 \
    --paths-file "$_absent_paths" 2>&1) || true
_collect_absent_elapsed=$(( $(date +%s) - _collect_absent_start ))
[[ "$_collect_absent_elapsed" -lt 4 ]] || { echo "FAIL: collect on no-fallback absent took too long (${_collect_absent_elapsed}s)" >&2; exit 1; }
if grep -Fq 'STATUS=SENTINEL_TIMEOUT' <<<"$_collect_absent_out"; then
    echo "FAIL: collect on no-fallback absent must not SENTINEL_TIMEOUT" >&2
    printf '%s\n' "$_collect_absent_out" >&2
    exit 1
fi

# --- legacy multi-phase fallback (ungrouped; default path without --no-fallback) ---

persist_counter="$TMPROOT/persist.count"
printf '3\n' >"$persist_counter"
manifest="$TMPROOT/slots-fallback-counter-persist.ndjson"
jq -cn --arg out "$TMPROOT/persist-p3.txt" --arg pf "$prompt" \
    '{slot:"persist-p3",tool:"cursor",output:$out,prompt_file:$pf}' >"$manifest"
out=$(PATH="$STUB_BIN:$PATH" \
    CURSOR_STUB_FAIL_OUTPUT_CONTAINS='persist-p3.txt' \
    CODEX_STUB_RESULT_INCLUDE_BASENAME=true \
    CODEX_STUB_FAIL_OUTPUT_CONTAINS='persist-p3-phase2.txt' \
    "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --fallback-counter-file "$persist_counter" \
    --codex-present true \
    --cursor-present true \
    --mode description \
    --require-result-pattern '^[[:space:]]*## Recommendation' \
    --timeout 5)
assert_line "FALLBACK_COUNT=1" "$out"
assert_line "COMBINED_FALLBACK_COUNT=1" "$out"
fb=$(grep -E '^FALLBACK_COUNT=' <<<"$out" | head -1 | cut -d= -f2-)
case "$fb" in ''|*[!0-9]*) fb=0 ;; esac
expected_persist=$((3 + fb))
[[ "$(cat "$persist_counter")" == "$expected_persist" ]] || {
    echo "FAIL: fallback-counter-file should persist prior + phase-3 fallback ($expected_persist)" >&2
    printf 'file=%s fb=%s\n' "$(cat "$persist_counter")" "$fb" >&2
    exit 1
}

manifest="$TMPROOT/slots-ungrouped-warn.ndjson"
jq -cn --arg out "$TMPROOT/ungrouped-warn.txt" --arg pf "$prompt" \
    '{slot:"ungrouped-warn",tool:"cursor",output:$out,prompt_file:$pf}' >"$manifest"
out=$(PATH="$STUB_BIN:$PATH" \
    LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD=0 \
    CURSOR_STUB_FAIL=true \
    "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --codex-present false \
    --cursor-present false \
    --mode description \
    --timeout 5)
assert_line "FALLBACK_COUNT=1" "$out"
assert_line "WARN=cost-fallback-exceeded-threshold" "$out"
assert_line "DISPATCH_OK=true" "$out"

# --- Degraded Cursor output integration: high-token narration triggers fallback ---
# Cursor stub returns outputTokens=5000 with a short narration result (<500 bytes).
# launch-review.sh writes CURSOR_DEGRADED_RESPONSE; collect-agent-results.sh maps
# it to STATUS=CURSOR_EMPTY_RESPONSE; dispatch-with-waterfall.sh falls back to Claude.
manifest_deg="$TMPROOT/slots-degraded.ndjson"
printf '{"slot":"s1","tool":"cursor","output":"%s","prompt_file":"%s"}\n' \
    "$TMPROOT/cursor-deg.txt" "$prompt" > "$manifest_deg"
narration="Exploring the design skill...Creating the architectural review plan from codebase alignment."
deg_out=$(PATH="$STUB_BIN:$PATH" \
    CURSOR_STUB_OUTPUT_TOKENS=5000 \
    CURSOR_STUB_RESULT_CONTENT="$narration" \
    CLAUDE_STUB_FAIL=false \
    "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest_deg" \
    --codex-present false \
    --cursor-present true \
    --mode description \
    --timeout 30 2>/dev/null)
grep -Fxq 'DISPATCH_OK=true' <<<"$deg_out" || { echo "FAIL: degraded-cursor: expected DISPATCH_OK=true after claude fallback" >&2; printf '%s\n' "$deg_out" >&2; exit 1; }
grep -Fxq 'ALL_OUTPUT_TOOLS=claude' <<<"$deg_out" || { echo "FAIL: degraded-cursor: expected claude final tool after fallback" >&2; printf '%s\n' "$deg_out" >&2; exit 1; }
grep -Fxq 'FALLBACK_COUNT=1' <<<"$deg_out" || { echo "FAIL: degraded-cursor: expected one Claude fallback" >&2; printf '%s\n' "$deg_out" >&2; exit 1; }
grep -Fq 'claude ok' "$TMPROOT/cursor-deg-phase3.txt" \
    || { echo "FAIL: degraded-cursor: Claude fallback output missing" >&2; printf '%s\n' "$deg_out" >&2; exit 1; }

echo "PASS: test-dispatch-with-waterfall.sh"
