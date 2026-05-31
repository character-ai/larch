#!/usr/bin/env bash
# Regression harness for scripts/dispatch-plan-voters.sh waterfall wiring.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SCRIPT="$REPO_ROOT/scripts/dispatch-plan-voters.sh"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-dispatch-plan-voters.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
unset CLAUDE_PLUGIN_ROOT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

stdout_key_order() {
    awk -F= '/^[A-Z0-9_]+=/{if ($1 != "WARN") print $1}'
}

assert_key_order() {
    local label="$1" actual="$2" expected="$3"
    if [[ "$actual" != "$expected" ]]; then
        {
            printf 'FAIL: %s key order drifted\n' "$label"
            printf -- '--- expected ---\n%s\n' "$expected"
            printf -- '--- actual ---\n%s\n' "$actual"
        } >&2
        exit 1
    fi
}

STUB_BIN="$TMP/bin"
mkdir -p "$STUB_BIN"
cat > "$STUB_BIN/codex" <<'STUB'
#!/usr/bin/env bash
log="${CODEX_STUB_LOG:-}"
output=""
last=""
for arg in "$@"; do
    [[ -n "$log" ]] && printf '%s\n' "$arg" >> "$log"
    if [[ "$last" == "--output-last-message" ]]; then
        output="$arg"
    fi
    last="$arg"
done
[[ -n "$output" ]] || exit 2
if [[ "${CODEX_STUB_MODE:-primary}" == "narrative" ]]; then
    printf 'Narrative output that should trigger retry.\n' > "$output"
else
    printf 'FINDING_1: YES\nOOS_1: NO -- codex primary ok\n' > "$output"
fi
printf '0\n' > "${output}.done"
STUB
cat > "$STUB_BIN/cursor" <<'STUB'
#!/usr/bin/env bash
log="${CURSOR_STUB_LOG:-}"
for arg in "$@"; do
    [[ -n "$log" ]] && printf '%s\n' "$arg" >> "$log"
done
printf '{"result":"FINDING_1: NO -- cursor","usage":{"inputTokens":1,"outputTokens":1,"cacheReadTokens":0,"cacheWriteTokens":0}}\n'
STUB
cat > "$STUB_BIN/claude" <<'STUB'
#!/usr/bin/env bash
[[ "${CLAUDE_STUB_MODE:-ok}" == "fail" ]] && exit 77
prompt="$(cat)"
if grep -Fq 'previous attempt produced narrative output' <<< "$prompt"; then
printf 'FINDING_1: YES\nOOS_1: NO -- claude retry ok\n'
else
printf 'Narrative output that should trigger retry.\n'
fi
STUB
chmod +x "$STUB_BIN/codex" "$STUB_BIN/cursor" "$STUB_BIN/claude"

PLUGIN_ROOT_STUB="$TMP/plugin-root"
mkdir -p "$PLUGIN_ROOT_STUB/scripts" "$PLUGIN_ROOT_STUB/skills/shared/scripts"
cp "$REPO_ROOT/skills/shared/scripts/render-voter-prompt.sh" "$PLUGIN_ROOT_STUB/skills/shared/scripts/render-voter-prompt.sh"
chmod +x "$PLUGIN_ROOT_STUB/skills/shared/scripts/render-voter-prompt.sh"

cat > "$PLUGIN_ROOT_STUB/scripts/launch-claude-review.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
OUTPUT=""
PROMPT_FILE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output|--output-file) OUTPUT="${2:?}"; shift 2 ;;
        --prompt-file) PROMPT_FILE="${2:?}"; shift 2 ;;
        --mode|--role|--timeout|--timing-task-kind) shift 2 ;;
        *) shift ;;
    esac
done
[[ -n "$OUTPUT" ]] || exit 2
mkdir -p "$(dirname "$OUTPUT")"
case "${LAUNCH_CLAUDE_REVIEW_STUB_MODE:-ok}" in
    ok) printf 'FINDING_1: YES\nOOS_1: NO -- claude voter1 ok\n' > "$OUTPUT" ;;
    fail) exit 99 ;;
    empty) : > "$OUTPUT" ;;
    narrative_then_ok)
        if [[ -n "$PROMPT_FILE" ]] && grep -Fq 'previous attempt produced narrative output' "$PROMPT_FILE" 2>/dev/null; then
            printf 'FINDING_1: YES\nOOS_1: NO -- claude voter1 retry ok\n' > "$OUTPUT"
        else
            printf 'Narrative output that should trigger retry.\n' > "$OUTPUT"
        fi
        ;;
    *) printf 'FINDING_1: YES\nOOS_1: NO -- claude voter1 ok\n' > "$OUTPUT" ;;
esac
printf '0\n' > "${OUTPUT}.done"
exit 0
STUB
chmod +x "$PLUGIN_ROOT_STUB/scripts/launch-claude-review.sh"

cat > "$PLUGIN_ROOT_STUB/scripts/dispatch-with-waterfall.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
slots_file=""
CODEX_PRESENT="true"
CURSOR_PRESENT="true"
while [[ $# -gt 0 ]]; do
    [[ -n "${PLAN_VOTER_ARGV_LOG:-}" ]] && printf '%s\n' "$1" >> "$PLAN_VOTER_ARGV_LOG"
    case "$1" in
        --slots-file) [[ -n "${PLAN_VOTER_ARGV_LOG:-}" ]] && printf '%s\n' "$2" >> "$PLAN_VOTER_ARGV_LOG"; slots_file="$2"; shift 2 ;;
        --codex-present) [[ -n "${PLAN_VOTER_ARGV_LOG:-}" ]] && printf '%s\n' "$2" >> "$PLAN_VOTER_ARGV_LOG"; CODEX_PRESENT="$2"; shift 2 ;;
        --cursor-present) [[ -n "${PLAN_VOTER_ARGV_LOG:-}" ]] && printf '%s\n' "$2" >> "$PLAN_VOTER_ARGV_LOG"; CURSOR_PRESENT="$2"; shift 2 ;;
        --no-fallback) shift ;;
        --mode|--timeout) [[ -n "${PLAN_VOTER_ARGV_LOG:-}" ]] && printf '%s\n' "$2" >> "$PLAN_VOTER_ARGV_LOG"; shift 2 ;;
        *) shift ;;
    esac
done
[[ -n "$slots_file" ]] || exit 2
mode="${PLAN_VOTER_STUB_MODE:-healthy}"
all_outputs=()
all_tools=()
while IFS= read -r row || [[ -n "$row" ]]; do
    [[ -n "$row" ]] || continue
    slot=$(printf '%s' "$row" | jq -r '.slot')
    tool=$(printf '%s' "$row" | jq -r '.tool')
    output=$(printf '%s' "$row" | jq -r '.output')
    prompt_file=$(printf '%s' "$row" | jq -r '.prompt_file')
    effective_tool="$tool"
    if [[ "$tool" == "codex" && "$CODEX_PRESENT" != "true" ]]; then
        effective_tool="claude"
    fi
    if [[ "$tool" == "cursor" && "$CURSOR_PRESENT" != "true" ]]; then
        effective_tool="claude"
    fi
    requested_status=""
    case "$slot" in
        voter-2) requested_status="${PLAN_VOTER_SLOT_2_STATUS:-}" ;;
        voter-3) requested_status="${PLAN_VOTER_SLOT_3_STATUS:-}" ;;
    esac
    if [[ -n "$requested_status" ]]; then
        case "$requested_status" in
            launched)
                printf 'FINDING_1: YES\nOOS_1: NO -- %s launched\n' "$tool" > "$output"
                effective_tool="$tool"
                ;;
            fallback)
                printf 'FINDING_1: YES\nOOS_1: NO -- claude fallback\n' > "$output"
                effective_tool="claude"
                ;;
            failed)
                rm -f "$output"
                ;;
            *) echo "unknown requested status: $requested_status" >&2; exit 2 ;;
        esac
        all_outputs+=("$output")
        all_tools+=("$effective_tool")
    else
        case "$mode:$slot" in
        healthy:*)
            if [[ "$effective_tool" == "codex" ]]; then
                printf 'FINDING_1: YES\nOOS_1: NO -- codex primary ok\n' > "$output"
            elif [[ "$effective_tool" == "cursor" ]]; then
                printf 'FINDING_1: NO -- cursor\nOOS_1: NO -- cursor\n' > "$output"
            else
                prompt_body=""
                [[ -f "$prompt_file" ]] && prompt_body=$(cat "$prompt_file")
                if grep -Fq 'previous attempt produced narrative output' <<< "$prompt_body"; then
                    printf 'FINDING_1: YES\nOOS_1: NO -- claude retry ok\n' > "$output"
                else
                    printf 'Narrative output that should trigger retry.\n' > "$output"
                fi
            fi
            all_outputs+=("$output")
            all_tools+=("$effective_tool")
            ;;
        retry-waterfall:voter-2)
            # Historical harness name: keep substantive output so parse-rate does not
            # depend on the unused voter-2-retry stub branch (manifest has only two slots).
            printf 'FINDING_1: YES\nOOS_1: NO -- codex primary ok\n' > "$output"
            all_outputs+=("$output")
            all_tools+=("$effective_tool")
            ;;
        retry-waterfall:voter-3)
            printf 'FINDING_1: NO -- cursor\nOOS_1: NO -- cursor\n' > "$output"
            all_outputs+=("$output")
            all_tools+=("$effective_tool")
            ;;
        retry-waterfall:voter-2-retry)
            phase2_output="${output%.txt}-phase2.txt"
            printf 'FINDING_1: NO -- cursor\nOOS_1: NO -- cursor\n' > "$phase2_output"
            all_outputs+=("$phase2_output")
            all_tools+=("cursor")
            ;;
        retry-fails-substantive:voter-2)
            printf 'Narrative output that should trigger retry.\n' > "$output"
            all_outputs+=("$output")
            all_tools+=("$effective_tool")
            ;;
        retry-fails-substantive:voter-2-retry)
            phase2_output="${output%.txt}-phase2.txt"
            printf 'Narrative output that should still fail substantive validation.\n' > "$phase2_output"
            all_outputs+=("$phase2_output")
            all_tools+=("cursor")
            ;;
        *)
            printf 'FINDING_1: YES\nOOS_1: NO -- fallback\n' > "$output"
            all_outputs+=("$output")
            all_tools+=("$effective_tool")
            ;;
        esac
    fi
    printf '%s\t%s\t%s\t%s\n' "$slot" "$tool" "$output" "$prompt_file" >> "${PLAN_VOTER_STUB_LOG:?}"
done < "$slots_file"
printf 'ALL_OUTPUT_FILES=%s\n' "${all_outputs[*]}"
printf 'ALL_OUTPUT_TOOLS=%s\n' "${all_tools[*]}"
printf 'DISPATCH_OK=true\n'
STUB
chmod +x "$PLUGIN_ROOT_STUB/scripts/dispatch-with-waterfall.sh"

BALLOT="$TMP/ballot.txt"
printf 'FINDING_1: example\nOOS_1: out of scope example\n' > "$BALLOT"
BALLOT_PARSE_IDS="$TMP/ballot-parse-ids.txt"
printf '%s\n' '### FINDING_1:' 'example' '### OOS_1:' 'out of scope example' > "$BALLOT_PARSE_IDS"
EXPECTED_ORDER_WITH_PATHS=$(cat <<'EOF'
VOTER_1_PATH
VOTER_1_TOOL
VOTER_1_STATUS
VOTER_1_PARSE_RATE_STATUS
VOTER_2_PATH
VOTER_3_PATH
VOTER_PATHS_FILE
VOTER_2_TOOL
VOTER_3_TOOL
VOTER_2_STATUS
VOTER_3_STATUS
VOTER_2_PARSE_RATE_STATUS
VOTER_3_PARSE_RATE_STATUS
DISPATCH_OK
EOF
)
EXPECTED_ORDER_NO_PATHS=$(cat <<'EOF'
VOTER_1_PATH
VOTER_1_TOOL
VOTER_1_STATUS
VOTER_1_PARSE_RATE_STATUS
VOTER_2_PATH
VOTER_3_PATH
VOTER_2_TOOL
VOTER_3_TOOL
VOTER_2_STATUS
VOTER_3_STATUS
VOTER_2_PARSE_RATE_STATUS
VOTER_3_PARSE_RATE_STATUS
DISPATCH_OK
EOF
)

out=$(PATH="$STUB_BIN:$PATH" CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT_STUB" PLAN_VOTER_STUB_LOG="$TMP/stub-absent.log" \
    "$SCRIPT" --ballot-file "$BALLOT_PARSE_IDS" --design-tmpdir "$TMP/absent" --codex-available false --cursor-available false)
grep -Fq 'VOTER_1_STATUS=launched' <<< "$out" || { echo "FAIL: absent-tools path missing VOTER_1 launched" >&2; exit 1; }
grep -Fq 'VOTER_1_TOOL=claude' <<< "$out" || { echo "FAIL: absent-tools path missing VOTER_1_TOOL" >&2; exit 1; }
grep -Fq 'VOTER_1_PARSE_RATE_STATUS=OK' <<< "$out" || { echo "FAIL: absent-tools path missing VOTER_1 parse-rate OK" >&2; exit 1; }
grep -Fq 'VOTER_2_STATUS=failed' <<< "$out" || { echo "FAIL: absent-tools VOTER_2 should be failed" >&2; exit 1; }
grep -Fq 'VOTER_3_STATUS=failed' <<< "$out" || { echo "FAIL: absent-tools VOTER_3 should be failed" >&2; exit 1; }
grep -Fq 'DISPATCH_OK=true' <<< "$out" || { echo "FAIL: absent-tools DISPATCH_OK" >&2; exit 1; }
grep -Fq 'VOTER_PATHS_FILE=' <<< "$out" || { echo "FAIL: absent-tools dispatch missing VOTER_PATHS_FILE" >&2; exit 1; }
pv_abs=$(printf '%s\n' "$out" | awk -F= '$1=="VOTER_PATHS_FILE"{print substr($0,index($0,"=")+1);exit}')
[[ -f "$pv_abs" ]] || { echo "FAIL: plan voter paths file missing" >&2; exit 1; }
[[ $(wc -l < "$pv_abs" | tr -d ' ') -eq 1 ]] || { echo "FAIL: absent-tools plan-voter paths should list Claude only" >&2; exit 1; }

stub_log="$TMP/dispatch-with-waterfall.log"
argv_log="$TMP/dispatch-with-waterfall.argv"
out_healthy=$(PATH="$STUB_BIN:$PATH" CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT_STUB" PLAN_VOTER_STUB_LOG="$stub_log" PLAN_VOTER_ARGV_LOG="$argv_log" \
    "$SCRIPT" --ballot-file "$BALLOT_PARSE_IDS" --design-tmpdir "$TMP/healthy" --codex-available true --cursor-available true)
out="$out_healthy"
grep -Fq 'VOTER_1_STATUS=launched' <<< "$out_healthy" || { echo "FAIL: healthy path missing VOTER_1 launched" >&2; exit 1; }
grep -Fq 'VOTER_2_TOOL=codex' <<< "$out" || { echo "FAIL: healthy path did not keep codex primary" >&2; exit 1; }
grep -Fq 'VOTER_3_TOOL=cursor' <<< "$out" || { echo "FAIL: healthy path did not keep cursor primary" >&2; exit 1; }
assert_key_order "healthy dispatcher stdout" "$(printf '%s\n' "$out" | stdout_key_order)" "$EXPECTED_ORDER_WITH_PATHS"
tr '\n' ' ' < "$argv_log" | grep -Fq -- '--timeout 1860' || fail "waterfall timeout should be 1860"
grep -Fq -- '--no-fallback' "$argv_log" || fail "plan-voter waterfall must pass --no-fallback"
manifest_healthy="$TMP/healthy/plan-voter-slots.ndjson"
[[ -s "$manifest_healthy" ]] || fail "healthy run missing voter manifest"
jq -s -e 'all(.[]; has("fallback_group") | not)' "$manifest_healthy" >/dev/null \
    || fail "voter manifest must not include fallback_group"
[[ "$(jq -s 'length' "$manifest_healthy")" == "2" ]] || fail "healthy run expected two external voter rows"

out=$(PATH="$STUB_BIN:$PATH" CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT_STUB" PLAN_VOTER_STUB_LOG="$TMP/stub-codex-only.log" \
    "$SCRIPT" --ballot-file "$BALLOT" --design-tmpdir "$TMP/codex-only" --codex-available true --cursor-available false)
grep -Fq 'VOTER_2_TOOL=codex' <<< "$out" || fail "codex-only missing voter 2 codex"
grep -Fq 'VOTER_3_STATUS=failed' <<< "$out" || fail "codex-only voter 3 should be failed/absent"

out=$(PATH="$STUB_BIN:$PATH" CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT_STUB" PLAN_VOTER_STUB_LOG="$TMP/stub-cursor-only.log" \
    "$SCRIPT" --ballot-file "$BALLOT" --design-tmpdir "$TMP/cursor-only" --codex-available false --cursor-available true)
grep -Fq 'VOTER_3_TOOL=cursor' <<< "$out" || fail "cursor-only missing voter 3 cursor"
grep -Fq 'VOTER_2_STATUS=failed' <<< "$out" || fail "cursor-only voter 2 should be failed/absent"
grep -Fq 'OOS_N:' "$TMP/healthy/codex-plan-voter-prompt.txt" || { echo "FAIL: healthy codex prompt missing OOS rows" >&2; exit 1; }
grep -Fq 'OOS_N:' "$TMP/healthy/cursor-plan-voter-prompt.txt" || { echo "FAIL: healthy cursor prompt missing OOS rows" >&2; exit 1; }
grep -Fq 'OOS_N:' "$TMP/healthy/claude-plan-voter-prompt.txt" || { echo "FAIL: healthy claude voter1 prompt missing OOS rows" >&2; exit 1; }
CANONICAL_YES_EXON_PHRASE='When in doubt between YES and EXONERATE, prefer EXONERATE'
for _pv_prompt in "$TMP/healthy/codex-plan-voter-prompt.txt" "$TMP/healthy/cursor-plan-voter-prompt.txt" "$TMP/healthy/claude-plan-voter-prompt.txt"; do
    grep -Fq "For \`OOS_N:\` items in plan review (or items prefixed with \`[OUT_OF_SCOPE]\` in code review):" "$_pv_prompt" \
        || { echo "FAIL: $(basename "$_pv_prompt") missing canonical finding-oos OOS clause" >&2; exit 1; }
    grep -Fq 'fix proposals are informational; the coder decides the exact change' "$_pv_prompt" \
        || { echo "FAIL: $(basename "$_pv_prompt") missing informational-fix voter guardrail" >&2; exit 1; }
    grep -Fq "$CANONICAL_YES_EXON_PHRASE" "$_pv_prompt" \
        || { echo "FAIL: $(basename "$_pv_prompt") missing YES↔EXONERATE anchor phrase (rendered voter prompt)" >&2; exit 1; }
    if ! grep -Fq '  FINDING_N: YES' "$_pv_prompt"; then
        echo "FAIL: $(basename "$_pv_prompt") missing FINDING_N example line" >&2
        exit 1
    fi
    if ! grep -Fq '  OOS_N: YES' "$_pv_prompt"; then
        echo "FAIL: $(basename "$_pv_prompt") missing OOS_N example line" >&2
        exit 1
    fi
done
grep -Fq $'voter-2\tcodex' "$stub_log" || { echo "FAIL: healthy stub log missing codex slot wiring" >&2; exit 1; }
grep -Fq $'voter-3\tcursor' "$stub_log" || { echo "FAIL: healthy stub log missing cursor slot wiring" >&2; exit 1; }
grep -Fq 'VOTER_PATHS_FILE=' <<< "$out_healthy" || { echo "FAIL: healthy stub missing VOTER_PATHS_FILE" >&2; exit 1; }
pv_h=$(printf '%s\n' "$out_healthy" | awk -F= '$1=="VOTER_PATHS_FILE"{print substr($0,index($0,"=")+1);exit}')
pv_lines=$(wc -l < "$pv_h" | tr -d ' ')
VOTER_1_STATUS=$(printf '%s\n' "$out_healthy" | awk -F= '$1=="VOTER_1_STATUS"{print $2;exit}')
VOTER_2_STATUS=$(printf '%s\n' "$out_healthy" | awk -F= '$1=="VOTER_2_STATUS"{print $2;exit}')
VOTER_3_STATUS=$(printf '%s\n' "$out_healthy" | awk -F= '$1=="VOTER_3_STATUS"{print $2;exit}')
effective_paths=0
for st in "$VOTER_1_STATUS" "$VOTER_2_STATUS" "$VOTER_3_STATUS"; do
    [[ "$st" != "failed" ]] && effective_paths=$((effective_paths + 1))
done
[[ -f "$pv_h" && "$pv_lines" -eq "$effective_paths" ]] || {
    echo "FAIL: healthy plan-voter paths file (lines=$pv_lines expected=$effective_paths)" >&2
    grep -E '^VOTER_[123]_(STATUS|PATH|PARSE)=' <<<"$out" >&2 || true
    exit 1
}

out_all_failed=$(PATH="$STUB_BIN:$PATH" CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT_STUB" CLAUDE_STUB_MODE=fail PLAN_VOTER_SLOT_2_STATUS=failed PLAN_VOTER_SLOT_3_STATUS=failed PLAN_VOTER_STUB_LOG="$TMP/all-failed.log" \
    "$SCRIPT" --ballot-file "$BALLOT" --design-tmpdir "$TMP/all-failed" --codex-available true --cursor-available true)
grep -Fq 'VOTER_1_STATUS=failed' <<< "$out_all_failed" || fail "all-failed path missing VOTER_1 failed"
grep -Fq 'VOTER_2_STATUS=failed' <<< "$out_all_failed" || fail "all-failed path missing VOTER_2 failed"
grep -Fq 'VOTER_3_STATUS=failed' <<< "$out_all_failed" || fail "all-failed path missing VOTER_3 failed"
if grep -Fq 'VOTER_PATHS_FILE=' <<< "$out_all_failed"; then
    fail "all-failed path should omit VOTER_PATHS_FILE"
fi
assert_key_order "all-failed dispatcher stdout" "$(printf '%s\n' "$out_all_failed" | stdout_key_order | grep -v '^DEGRADED_PANEL_WARNING$' || true)" "$EXPECTED_ORDER_NO_PATHS"
grep -Fq 'DEGRADED_PANEL_WARNING=' <<< "$out_all_failed" || fail "all-failed path should emit degraded warning"

set +e
out_invalid_tmpdir=$(PATH="$STUB_BIN:$PATH" CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT_STUB" PLAN_VOTER_STUB_LOG="$TMP/invalid-tmpdir.log" \
    "$SCRIPT" --ballot-file "$BALLOT" --design-tmpdir "$TMP/healthy/../escaped-dotdot" --codex-available true --cursor-available true 2>&1)
rc_invalid_tmpdir=$?
set -e
[[ "$rc_invalid_tmpdir" -eq 2 ]] || fail "dotdot tmpdir should be rejected before launch"
grep -Fq "must not contain '.' or '..' segments" <<< "$out_invalid_tmpdir" || fail "dotdot tmpdir diagnostic missing"

for status2 in launched failed; do
    for status3 in launched failed; do
        case_dir="$TMP/status-${status2}-${status3}"
        out_status=$(PATH="$STUB_BIN:$PATH" CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT_STUB" PLAN_VOTER_SLOT_2_STATUS="$status2" PLAN_VOTER_SLOT_3_STATUS="$status3" PLAN_VOTER_STUB_LOG="$case_dir.log" \
            "$SCRIPT" --ballot-file "$BALLOT" --design-tmpdir "$case_dir" --codex-available true --cursor-available true)
        [[ $(grep -c "^VOTER_2_STATUS=${status2}$" <<< "$out_status" || true) -eq 1 ]] || fail "VOTER_2_STATUS=${status2} should be emitted once"
        [[ $(grep -c "^VOTER_3_STATUS=${status3}$" <<< "$out_status" || true) -eq 1 ]] || fail "VOTER_3_STATUS=${status3} should be emitted once"
        degraded_count=$(grep -c '^DEGRADED_PANEL_WARNING=' <<< "$out_status" || true)
        if [[ "$status2" == "failed" || "$status3" == "failed" ]]; then
            [[ "$degraded_count" -eq 1 ]] || fail "degraded warning missing for $status2/$status3"
        else
            [[ "$degraded_count" -eq 0 ]] || fail "unexpected degraded warning for $status2/$status3"
        fi
    done
done

stub_log_retry="$TMP/dispatch-with-waterfall-retry.log"
out=$(PATH="$STUB_BIN:$PATH" CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT_STUB" PLAN_VOTER_STUB_MODE=retry-waterfall PLAN_VOTER_STUB_LOG="$stub_log_retry" \
    "$SCRIPT" --ballot-file "$BALLOT" --design-tmpdir "$TMP/retry-waterfall" --codex-available true --cursor-available true)
voter2_path=$(printf '%s\n' "$out" | awk -F= '$1=="VOTER_2_PATH"{print $2; exit}')
grep -Fq 'codex-vote-output.txt' <<< "$voter2_path" || { echo "FAIL: retry waterfall should preserve canonical voter output path" >&2; exit 1; }
grep -Fq 'FINDING_1:' "$voter2_path" || { echo "FAIL: retry waterfall voter2 output missing FINDING vote line" >&2; exit 1; }
grep -Fq 'OOS_1:' "$voter2_path" || { echo "FAIL: retry waterfall voter2 output missing OOS vote line" >&2; exit 1; }
grep -Fq $'voter-2\tcodex' "$stub_log_retry" || { echo "FAIL: retry stub log missing codex slot wiring" >&2; exit 1; }
pv_rw=$(printf '%s\n' "$out" | awk -F= '$1=="VOTER_PATHS_FILE"{print substr($0,index($0,"=")+1);exit}')
[[ -f "$pv_rw" ]] || { echo "FAIL: retry waterfall VOTER_PATHS_FILE missing" >&2; exit 1; }
[[ $(wc -l < "$pv_rw" | tr -d ' ') -eq 3 ]] || { echo "FAIL: retry waterfall plan-voter paths line count" >&2; exit 1; }
v1p=$(printf '%s\n' "$out" | awk -F= '$1=="VOTER_1_PATH"{print $2;exit}')
v2p=$(printf '%s\n' "$out" | awk -F= '$1=="VOTER_2_PATH"{print $2;exit}')
v3p=$(printf '%s\n' "$out" | awk -F= '$1=="VOTER_3_PATH"{print $2;exit}')
grep -Fxq "$v1p" "$pv_rw" || { echo "FAIL: retry waterfall paths file missing voter 1 path" >&2; exit 1; }
grep -Fxq "$v2p" "$pv_rw" || { echo "FAIL: retry waterfall paths file missing voter 2 path" >&2; exit 1; }
grep -Fxq "$v3p" "$pv_rw" || { echo "FAIL: retry waterfall paths file missing voter 3 path" >&2; exit 1; }

stub_log_not_substantive="$TMP/dispatch-with-waterfall-not-substantive.log"
out=$(PATH="$STUB_BIN:$PATH" CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT_STUB" CODEX_STUB_MODE=narrative PLAN_VOTER_STUB_MODE=retry-fails-substantive PLAN_VOTER_STUB_LOG="$stub_log_not_substantive" \
    "$SCRIPT" --ballot-file "$BALLOT_PARSE_IDS" --design-tmpdir "$TMP/retry-fails-substantive" --codex-available true --cursor-available true)
grep -Fq 'VOTER_2_STATUS=failed' <<< "$out" || { echo "FAIL: narrative-only retry output should mark voter 2 failed" >&2; exit 1; }
grep -Fq 'DEGRADED_PANEL_WARNING=' <<< "$out" || { echo "FAIL: narrative-only retry output should emit degraded warning" >&2; exit 1; }
pv_ns=$(printf '%s\n' "$out" | awk -F= '$1=="VOTER_PATHS_FILE"{print substr($0,index($0,"=")+1);exit}')
[[ -f "$pv_ns" ]] || { echo "FAIL: substantive-fail VOTER_PATHS_FILE missing" >&2; exit 1; }
[[ $(wc -l < "$pv_ns" | tr -d ' ') -eq 2 ]] || { echo "FAIL: substantive-fail plan-voter paths should list voter 1 + surviving voter 3" >&2; exit 1; }
v1_ok=$(printf '%s\n' "$out" | awk -F= '$1=="VOTER_1_PATH"{print $2;exit}')
v2_failed=$(printf '%s\n' "$out" | awk -F= '$1=="VOTER_2_PATH"{print $2;exit}')
v3_ok=$(printf '%s\n' "$out" | awk -F= '$1=="VOTER_3_PATH"{print $2;exit}')
grep -Fxq "$v1_ok" "$pv_ns" || { echo "FAIL: substantive-fail paths file must list voter 1" >&2; exit 1; }
grep -Fxq "$v3_ok" "$pv_ns" || { echo "FAIL: substantive-fail paths file must list surviving voter 3" >&2; exit 1; }
if grep -Fxq "$v2_failed" "$pv_ns"; then
    echo "FAIL: substantive-fail paths file must omit failed voter 2" >&2
    exit 1
fi

echo "PASS: test-dispatch-plan-voters.sh"
