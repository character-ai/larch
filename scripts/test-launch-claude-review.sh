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

echo "PASS: test-launch-claude-review.sh"
