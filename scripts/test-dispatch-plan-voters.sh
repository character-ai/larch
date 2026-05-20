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
cat > "$STUB_BIN/cursor" <<'STUB'
#!/usr/bin/env bash
log="${CURSOR_STUB_LOG:-}"
[[ -n "$log" ]] && printf '%s\n' "$*" >> "$log"
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
chmod +x "$STUB_BIN/cursor" "$STUB_BIN/claude"

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

echo "PASS: test-dispatch-plan-voters.sh"
