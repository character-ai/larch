#!/usr/bin/env bash
# Regression harness for launch-claude-review.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
TMPROOT="$(mktemp -d /tmp/larch-test-launch-claude-review-XXXXXX)"
trap 'rm -rf "$TMPROOT"' EXIT

STUB_BIN="$TMPROOT/bin"
mkdir -p "$STUB_BIN"
cat > "$STUB_BIN/claude" <<'STUB'
#!/usr/bin/env bash
cat >/dev/null
printf 'claude review ok\n'
STUB
chmod +x "$STUB_BIN/claude"

prompt="$TMPROOT/prompt.txt"
output="$TMPROOT/out.txt"
printf 'review this\n' > "$prompt"

PATH="$STUB_BIN:$PATH" "$REPO_ROOT/scripts/launch-claude-review.sh" \
    --output "$output" \
    --prompt-file "$prompt" \
    --mode description \
    --timeout 5 >/dev/null

[[ "$(cat "$output")" == "claude review ok" ]] || { echo "FAIL: output passthrough" >&2; exit 1; }
[[ "$(cat "$output.done")" == "0" ]] || { echo "FAIL: done sentinel" >&2; exit 1; }
grep -Fq "TOOL=claude" "$output.meta" || { echo "FAIL: claude metadata" >&2; exit 1; }

set +e
"$REPO_ROOT/scripts/launch-claude-review.sh" --output "$TMPROOT/bad.txt" --prompt-file "$prompt" --mode description --timeout 0 >/dev/null 2>"$TMPROOT/bad.stderr"
rc=$?
set -e
[[ "$rc" -eq 2 ]] || { echo "FAIL: bad timeout exit=$rc" >&2; exit 1; }

# Test --agent-file path: render-specialist-prompt.sh is invoked; output still reaches caller.
# Use a real agent file from the repo (code-reviewer.md is always present).
agent_file="$REPO_ROOT/agents/code-reviewer.md"
agent_output="$TMPROOT/agent-out.txt"
diff_file="$TMPROOT/agent-diff.txt"
printf 'test diff content\n' > "$diff_file"
PATH="$STUB_BIN:$PATH" "$REPO_ROOT/scripts/launch-claude-review.sh" \
    --output "$agent_output" \
    --agent-file "$agent_file" \
    --mode diff \
    --diff-file "$diff_file" \
    --timeout 5 >/dev/null
[[ "$(cat "$agent_output")" == "claude review ok" ]] || { echo "FAIL: agent-file output passthrough" >&2; exit 1; }
[[ -f "$agent_output.done" ]] || { echo "FAIL: agent-file done sentinel" >&2; exit 1; }

echo "PASS: test-launch-claude-review.sh"
