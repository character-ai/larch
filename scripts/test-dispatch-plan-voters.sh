#!/usr/bin/env bash
# Regression harness for scripts/dispatch-plan-voters.sh waterfall wiring.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SCRIPT="$REPO_ROOT/scripts/dispatch-plan-voters.sh"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-dispatch-plan-voters.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
unset CLAUDE_PLUGIN_ROOT

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
prompt="$(cat)"
if grep -Fq 'previous attempt produced narrative output' <<< "$prompt"; then
printf 'FINDING_1: YES\nOOS_1: NO -- claude retry ok\n'
else
printf 'Narrative output that should trigger retry.\n'
fi
STUB
chmod +x "$STUB_BIN/codex" "$STUB_BIN/cursor" "$STUB_BIN/claude"

BALLOT="$TMP/ballot.txt"
printf 'FINDING_1: example\nOOS_1: out of scope example\n' > "$BALLOT"

out=$(PATH="$STUB_BIN:$PATH" "$SCRIPT" --ballot-file "$BALLOT" --design-tmpdir "$TMP/absent" --codex-available false --cursor-available false)
grep -Fq 'VOTER_2_STATUS=fallback' <<< "$out"
grep -Fq 'VOTER_3_STATUS=fallback' <<< "$out"
grep -Fq 'VOTER_2_TOOL=claude' <<< "$out"
grep -Fq 'VOTER_3_TOOL=claude' <<< "$out"
grep -Fq 'DISPATCH_OK=true' <<< "$out"
voter2_path=$(printf '%s\n' "$out" | awk -F= '$1=="VOTER_2_PATH"{print $2; exit}')
grep -Fq 'OOS_N:' "$TMP/absent/codex-plan-voter-prompt.txt" || { echo "FAIL: plan-voter prompt missing OOS rows" >&2; exit 1; }
grep -Fq 'FINDING_N: or OOS_N:' "$TMP/absent/claude-plan-voter-prompt-retry.txt" || { echo "FAIL: retry prompt missing FINDING/OOS directive" >&2; exit 1; }
grep -Fq 'OOS_1: NO -- claude retry ok' "$voter2_path" || { echo "FAIL: claude fallback retry path missing final vote output" >&2; exit 1; }
test -f "${voter2_path%.txt}-first-pass.txt" || { echo "FAIL: claude fallback first-pass sidecar missing" >&2; exit 1; }
grep -Fq 'VOTER_PATHS_FILE=' <<< "$out" || { echo "FAIL: absent-tools dispatch missing VOTER_PATHS_FILE" >&2; exit 1; }
pv_abs=$(printf '%s\n' "$out" | awk -F= '$1=="VOTER_PATHS_FILE"{print substr($0,index($0,"=")+1);exit}')
[[ -f "$pv_abs" ]] || { echo "FAIL: plan voter paths file missing" >&2; exit 1; }

PLUGIN_ROOT_STUB="$TMP/plugin-root"
mkdir -p "$PLUGIN_ROOT_STUB/scripts"
cat > "$PLUGIN_ROOT_STUB/scripts/dispatch-with-waterfall.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
slots_file=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --slots-file) slots_file="$2"; shift 2 ;;
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
    case "$mode:$slot" in
        healthy:*)
            if [[ "$tool" == "codex" ]]; then
                printf 'FINDING_1: YES\nOOS_1: NO -- codex primary ok\n' > "$output"
            else
                printf 'FINDING_1: NO -- cursor\nOOS_1: NO -- cursor\n' > "$output"
            fi
            all_outputs+=("$output")
            all_tools+=("$tool")
            ;;
        retry-waterfall:voter-2)
            printf 'Narrative output that should trigger retry.\n' > "$output"
            all_outputs+=("$output")
            all_tools+=("$tool")
            ;;
        retry-waterfall:voter-3)
            printf 'FINDING_1: NO -- cursor\nOOS_1: NO -- cursor\n' > "$output"
            all_outputs+=("$output")
            all_tools+=("$tool")
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
            all_tools+=("$tool")
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
            all_tools+=("$tool")
            ;;
    esac
    printf '%s\t%s\t%s\t%s\n' "$slot" "$tool" "$output" "$prompt_file" >> "${PLAN_VOTER_STUB_LOG:?}"
done < "$slots_file"
printf 'ALL_OUTPUT_FILES=%s\n' "${all_outputs[*]}"
printf 'ALL_OUTPUT_TOOLS=%s\n' "${all_tools[*]}"
printf 'DISPATCH_OK=true\n'
STUB
chmod +x "$PLUGIN_ROOT_STUB/scripts/dispatch-with-waterfall.sh"

stub_log="$TMP/dispatch-with-waterfall.log"
out=$(PATH="$STUB_BIN:$PATH" CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT_STUB" PLAN_VOTER_STUB_LOG="$stub_log" \
    "$SCRIPT" --ballot-file "$BALLOT" --design-tmpdir "$TMP/healthy" --codex-available true --cursor-available true)
grep -Fq 'VOTER_2_TOOL=codex' <<< "$out" || { echo "FAIL: healthy path did not keep codex primary" >&2; exit 1; }
grep -Fq 'VOTER_3_TOOL=cursor' <<< "$out" || { echo "FAIL: healthy path did not keep cursor primary" >&2; exit 1; }
grep -Fq 'OOS_N:' "$TMP/healthy/codex-plan-voter-prompt.txt" || { echo "FAIL: healthy codex prompt missing OOS rows" >&2; exit 1; }
grep -Fq 'OOS_N:' "$TMP/healthy/cursor-plan-voter-prompt.txt" || { echo "FAIL: healthy cursor prompt missing OOS rows" >&2; exit 1; }
grep -Fq $'voter-2\tcodex' "$stub_log" || { echo "FAIL: healthy stub log missing codex slot wiring" >&2; exit 1; }
grep -Fq $'voter-3\tcursor' "$stub_log" || { echo "FAIL: healthy stub log missing cursor slot wiring" >&2; exit 1; }
grep -Fq 'VOTER_PATHS_FILE=' <<< "$out" || { echo "FAIL: healthy stub missing VOTER_PATHS_FILE" >&2; exit 1; }
pv_h=$(printf '%s\n' "$out" | awk -F= '$1=="VOTER_PATHS_FILE"{print substr($0,index($0,"=")+1);exit}')
[[ -f "$pv_h" && $(wc -l < "$pv_h" | tr -d ' ') -eq 2 ]] || { echo "FAIL: healthy plan-voter paths file" >&2; exit 1; }

stub_log_retry="$TMP/dispatch-with-waterfall-retry.log"
out=$(PATH="$STUB_BIN:$PATH" CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT_STUB" PLAN_VOTER_STUB_MODE=retry-waterfall PLAN_VOTER_STUB_LOG="$stub_log_retry" \
    "$SCRIPT" --ballot-file "$BALLOT" --design-tmpdir "$TMP/retry-waterfall" --codex-available true --cursor-available true)
voter2_path=$(printf '%s\n' "$out" | awk -F= '$1=="VOTER_2_PATH"{print $2; exit}')
grep -Fq 'codex-vote-output.txt' <<< "$voter2_path" || { echo "FAIL: retry waterfall should preserve canonical voter output path" >&2; exit 1; }
grep -Fq 'FINDING_1: NO -- cursor' "$voter2_path" || { echo "FAIL: retry waterfall did not promote phase2 cursor output" >&2; exit 1; }
test -f "$TMP/retry-waterfall/codex-vote-output-first-pass.txt" || { echo "FAIL: retry waterfall first-pass sidecar missing" >&2; exit 1; }
test ! -f "$TMP/retry-waterfall/codex-vote-output-parse-retry-phase2.txt" || { echo "FAIL: retry waterfall phase2 artifact should have been moved into canonical path" >&2; exit 1; }
grep -Fq $'voter-2-retry\tcodex' "$stub_log_retry" || { echo "FAIL: retry stub log missing retry slot wiring" >&2; exit 1; }

stub_log_not_substantive="$TMP/dispatch-with-waterfall-not-substantive.log"
out=$(PATH="$STUB_BIN:$PATH" CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT_STUB" PLAN_VOTER_STUB_MODE=retry-fails-substantive PLAN_VOTER_STUB_LOG="$stub_log_not_substantive" \
    "$SCRIPT" --ballot-file "$BALLOT" --design-tmpdir "$TMP/retry-fails-substantive" --codex-available true --cursor-available true)
grep -Fq 'VOTER_2_STATUS=failed' <<< "$out" || { echo "FAIL: narrative-only retry output should mark voter 2 failed" >&2; exit 1; }
grep -Fq 'DEGRADED_PANEL_WARNING=' <<< "$out" || { echo "FAIL: narrative-only retry output should emit degraded warning" >&2; exit 1; }

echo "PASS: test-dispatch-plan-voters.sh"
