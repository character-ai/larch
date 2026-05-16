#!/usr/bin/env bash
# test-dispatch-code-voters.sh — smoke harness for scripts/dispatch-code-voters.sh.
#
# Validates argument handling, voter-slot wiring, and Claude replacement
# behavior when external vendors are marked unavailable. Stubs every external
# binary so the test runs offline.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SCRIPT="$REPO_ROOT/scripts/dispatch-code-voters.sh"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-dispatch-code-voters.XXXXXX")"
unset LARCH_EXECUTION_ISSUES_LOG SESSION_ENV_PATH IMPLEMENT_TMPDIR REVIEW_TMPDIR || true
trap 'rm -rf "$TMP"' EXIT

FAIL=0
assert_eq() {
    local name="$1" got="$2" want="$3"
    if [[ "$got" == "$want" ]]; then
        printf '  ok   %s\n' "$name"
    else
        printf '  FAIL %s — got %q want %q\n' "$name" "$got" "$want"
        FAIL=1
    fi
}

PLUGIN="$TMP/plugin"
mkdir -p "$PLUGIN/scripts"

# Stub lib-quiet so larch_quiet_init / emit_kv work in stubs.
cp "$REPO_ROOT/scripts/lib-quiet.sh" "$PLUGIN/scripts/lib-quiet.sh"

cat > "$PLUGIN/scripts/agent-model-args.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
tool=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tool) tool="$2"; shift 2 ;;
        --with-effort) shift ;;
        *) shift ;;
    esac
done
case "$tool" in
    codex) printf '%s\n' -m stub-codex ;;
    cursor) printf '%s\n' --model stub-cursor ;;
    *) exit 1 ;;
esac
STUB
chmod +x "$PLUGIN/scripts/agent-model-args.sh"

cat > "$PLUGIN/scripts/cursor-auth-flags.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' --api-key stub-key
STUB
chmod +x "$PLUGIN/scripts/cursor-auth-flags.sh"

cat > "$PLUGIN/scripts/cursor-wrap-prompt.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf 'wrapped: %s' "$1"
STUB
chmod +x "$PLUGIN/scripts/cursor-wrap-prompt.sh"

cat > "$PLUGIN/scripts/append-tool-failure.sh" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB
chmod +x "$PLUGIN/scripts/append-tool-failure.sh"

# wait-for-reviewers stub: waits for each sentinel briefly and prints DONE/TIMEOUT.
cat > "$PLUGIN/scripts/wait-for-reviewers.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "--timeout" ]]; then shift 2; fi
for sentinel in "$@"; do
    for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
        [[ -f "$sentinel" ]] && break
        sleep 0.05
    done
done
STUB
chmod +x "$PLUGIN/scripts/wait-for-reviewers.sh"

# run-external-agent stub: writes a vote-output file with synthetic votes and
# sentinel.
cat > "$PLUGIN/scripts/run-external-agent.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
tool=""; output=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tool) tool="$2"; shift 2 ;;
        --output) output="$2"; shift 2 ;;
        --timeout) shift 2 ;;
        --capture-stdout|--capture-stdout-only) shift ;;
        --) shift; break ;;
        *) shift ;;
    esac
done
printf 'FINDING_1: YES\nFINDING_2: NO -- stub %s\n' "$tool" > "$output"
printf '0\n' > "$output.done"
STUB
chmod +x "$PLUGIN/scripts/run-external-agent.sh"

# launch-claude-subprocess stub: writes a vote-output file with synthetic
# claude votes.
cat > "$PLUGIN/scripts/launch-claude-subprocess.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
output=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output-file) output="$2"; shift 2 ;;
        --prompt-file|--model|--timeout|--timing-task-kind) shift 2 ;;
        --context-files) shift; while [[ $# -gt 0 && "$1" != --* ]]; do shift; done ;;
        *) shift ;;
    esac
done
printf 'FINDING_1: YES\nFINDING_2: YES\n' > "$output"
STUB
chmod +x "$PLUGIN/scripts/launch-claude-subprocess.sh"

# Copy the script under test into the stub plugin root so its PLUGIN_ROOT
# resolution finds the stubbed siblings.
cp "$SCRIPT" "$PLUGIN/scripts/dispatch-code-voters.sh"
chmod +x "$PLUGIN/scripts/dispatch-code-voters.sh"

# Build a minimal ballot file.
mkdir -p "$TMP/review"
cat > "$TMP/review/ballot.md" <<'EOF'
### FINDING_1: First
- **Reviewer**: stub
- **Concern**: c1
- **Suggested revision**: r1

### FINDING_2: Second
- **Reviewer**: stub
- **Concern**: c2
- **Suggested revision**: r2
EOF

echo "# Case A: argument validation"
if "$PLUGIN/scripts/dispatch-code-voters.sh" >/dev/null 2>&1; then
    FAIL=1; printf '  FAIL no-args should exit 2\n'
else
    printf '  ok   no-args → non-zero exit\n'
fi

echo "# Case B: all voters available → 3 launches, all OK"
out=$(CLAUDE_PLUGIN_ROOT="$PLUGIN" "$PLUGIN/scripts/dispatch-code-voters.sh" \
    --ballot-file "$TMP/review/ballot.md" \
    --review-tmpdir "$TMP/review" \
    --codex-available true \
    --cursor-available true 2>/dev/null)
got=$(printf '%s\n' "$out" | awk -F= '$1=="VOTER_1_TOOL"{print $2}'); assert_eq "VOTER_1_TOOL=claude" "$got" "claude"
got=$(printf '%s\n' "$out" | awk -F= '$1=="VOTER_2_TOOL"{print $2}'); assert_eq "VOTER_2_TOOL=codex (all available)" "$got" "codex"
got=$(printf '%s\n' "$out" | awk -F= '$1=="VOTER_3_TOOL"{print $2}'); assert_eq "VOTER_3_TOOL=cursor (all available)" "$got" "cursor"
got=$(printf '%s\n' "$out" | awk -F= '$1=="VOTER_1_STATUS"{print $2}'); assert_eq "VOTER_1_STATUS=launched" "$got" "launched"
got=$(printf '%s\n' "$out" | awk -F= '$1=="VOTER_2_STATUS"{print $2}'); assert_eq "VOTER_2_STATUS=launched" "$got" "launched"
got=$(printf '%s\n' "$out" | awk -F= '$1=="VOTER_3_STATUS"{print $2}'); assert_eq "VOTER_3_STATUS=launched" "$got" "launched"
got=$(printf '%s\n' "$out" | awk -F= '$1=="DISPATCH_OK"{print $2}'); assert_eq "DISPATCH_OK=true" "$got" "true"
if [[ -s "$TMP/review/claude-vote-output.txt" ]]; then printf '  ok   claude-vote-output.txt written\n'; else FAIL=1; printf '  FAIL claude-vote-output.txt missing/empty\n'; fi
if [[ -s "$TMP/review/codex-vote-output.txt" ]]; then printf '  ok   codex-vote-output.txt written\n'; else FAIL=1; printf '  FAIL codex-vote-output.txt missing/empty\n'; fi
if [[ -s "$TMP/review/cursor-vote-output.txt" ]]; then printf '  ok   cursor-vote-output.txt written\n'; else FAIL=1; printf '  FAIL cursor-vote-output.txt missing/empty\n'; fi

echo "# Case C: codex unavailable → Voter 2 falls back to claude replacement"
rm -rf "$TMP/review"; mkdir -p "$TMP/review"
cat > "$TMP/review/ballot.md" <<'EOF'
### FINDING_1: First
- **Reviewer**: stub
- **Concern**: c1
- **Suggested revision**: r1
EOF
out=$(CLAUDE_PLUGIN_ROOT="$PLUGIN" "$PLUGIN/scripts/dispatch-code-voters.sh" \
    --ballot-file "$TMP/review/ballot.md" \
    --review-tmpdir "$TMP/review" \
    --codex-available false \
    --cursor-available true 2>/dev/null)
got=$(printf '%s\n' "$out" | awk -F= '$1=="VOTER_2_TOOL"{print $2}'); assert_eq "VOTER_2_TOOL=claude (codex unavail)" "$got" "claude"
got=$(printf '%s\n' "$out" | awk -F= '$1=="VOTER_2_STATUS"{print $2}'); assert_eq "VOTER_2_STATUS=fallback" "$got" "fallback"
got=$(printf '%s\n' "$out" | awk -F= '$1=="VOTER_3_TOOL"{print $2}'); assert_eq "VOTER_3_TOOL=cursor" "$got" "cursor"

echo "# Case D: cursor unavailable → Voter 3 falls back to claude replacement"
rm -rf "$TMP/review"; mkdir -p "$TMP/review"
cat > "$TMP/review/ballot.md" <<'EOF'
### FINDING_1: First
- **Reviewer**: stub
- **Concern**: c1
- **Suggested revision**: r1
EOF
out=$(CLAUDE_PLUGIN_ROOT="$PLUGIN" "$PLUGIN/scripts/dispatch-code-voters.sh" \
    --ballot-file "$TMP/review/ballot.md" \
    --review-tmpdir "$TMP/review" \
    --codex-available true \
    --cursor-available false 2>/dev/null)
got=$(printf '%s\n' "$out" | awk -F= '$1=="VOTER_3_TOOL"{print $2}'); assert_eq "VOTER_3_TOOL=claude (cursor unavail)" "$got" "claude"
got=$(printf '%s\n' "$out" | awk -F= '$1=="VOTER_3_STATUS"{print $2}'); assert_eq "VOTER_3_STATUS=fallback" "$got" "fallback"

echo "# Case E: both externals unavailable → both slots filled by claude"
rm -rf "$TMP/review"; mkdir -p "$TMP/review"
cat > "$TMP/review/ballot.md" <<'EOF'
### FINDING_1: First
- **Reviewer**: stub
- **Concern**: c1
- **Suggested revision**: r1
EOF
out=$(CLAUDE_PLUGIN_ROOT="$PLUGIN" "$PLUGIN/scripts/dispatch-code-voters.sh" \
    --ballot-file "$TMP/review/ballot.md" \
    --review-tmpdir "$TMP/review" \
    --codex-available false \
    --cursor-available false 2>/dev/null)
got=$(printf '%s\n' "$out" | awk -F= '$1=="VOTER_2_TOOL"{print $2}'); assert_eq "both-down V2=claude" "$got" "claude"
got=$(printf '%s\n' "$out" | awk -F= '$1=="VOTER_3_TOOL"{print $2}'); assert_eq "both-down V3=claude" "$got" "claude"

if [[ "$FAIL" -eq 0 ]]; then
    printf 'PASS: test-dispatch-code-voters.sh\n'
    exit 0
else
    printf 'FAIL: test-dispatch-code-voters.sh\n'
    exit 1
fi
