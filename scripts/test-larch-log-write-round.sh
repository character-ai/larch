#!/usr/bin/env bash
# test-larch-log-write-round.sh — regression harness for larch-log write-round.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
LARCH_LOG="$SCRIPT_DIR/larch-log.sh"

TMP_BASE="${TMPDIR:-/tmp}"
TMP_BASE="${TMP_BASE%/}"
TMP="$(mktemp -d "$TMP_BASE/larch-implement-write-round.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

assert_file() {
    local path="$1" label="$2"
    [[ -f "$path" ]] || fail "$label missing: $path"
}

assert_not_file() {
    local path="$1" label="$2"
    [[ ! -e "$path" ]] || fail "$label should not exist: $path"
}

assert_grep() {
    local pattern="$1" path="$2" label="$3"
    grep -Eq "$pattern" "$path" || fail "$label"
}

assert_not_grep() {
    local pattern="$1" path="$2" label="$3"
    if grep -Eq "$pattern" "$path"; then
        fail "$label"
    fi
}

log_root="$TMP/larch-logs"
source_dir="$TMP/round-1"
mkdir -p "$source_dir"

cat > "$source_dir/findings.md" <<EOF
### FINDING_1:
path: $TMP/round-1/private-file
token sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD
EOF

cat > "$source_dir/codex-specialist-security-output.txt.meta" <<'EOF'
TOOL=codex
TIMEOUT=1200
CMD_JSON=["codex","exec","secret argv"]
OUTPUT_FILE=/tmp/source/codex-specialist-security-output.txt
EOF

cat > "$source_dir/cursor-specialist-security-output-phase2.txt.meta" <<'EOF'
TOOL=cursor
CMD_JSON=["cursor","agent","secret argv"]
OUTPUT_FILE=/tmp/source/cursor-specialist-security-output-phase2.txt
EOF

cat > "$source_dir/cursor-vote-output.txt.json" <<'EOF'
{"result":"large raw cursor payload","usage":{"inputTokens":10},"status":"ok"}
EOF

cat > "$source_dir/codex-vote-output.txt.json" <<'EOF'
{"result":"large raw codex payload","status":"ok"}
EOF

printf '# Round summary\n' > "$source_dir/review-round-summary.md"
printf 'CODER_STATUS=skipped\n' > "$source_dir/coder.env"
printf 'excluded\n' > "$source_dir/random-notes.txt"
printf 'excluded\n' > "$source_dir/session-env.sh"
printf 'excluded\n' > "$source_dir/coder-output.log"
printf 'excluded\n' > "$source_dir/coder-codex.log"
printf 'excluded\n' > "$source_dir/codex-specialist-security-output.txt.done"
printf 'excluded\n' > "$source_dir/codex-specialist-security-output.txt.inner.done"
printf 'excluded\n' > "$source_dir/codex-specialist-security-output.txt.diag"
printf 'excluded\n' > "$source_dir/codex-specialist-security-output.txt.prompt"
printf 'excluded\n' > "$source_dir/codex-specialist-security-output.txt.sidecar"
printf 'excluded\n' > "$source_dir/codex-specialist-security-output.txt.dirty-tree"
printf 'excluded\n' > "$source_dir/codex-specialist-security-output.txt.untracked-baseline"

out="$("$LARCH_LOG" write-round --log-root "$log_root" --skill implement --run-id run123 --round 1 --source-dir "$source_dir")"
[[ "$out" == *"LOG_WRITTEN=true"* ]] || fail "write-round should report write: $out"

round_dir="$log_root/implement/run123/round-1"
assert_file "$round_dir/findings.md" "findings"
assert_file "$round_dir/codex-specialist-security-output.txt.meta" "meta sidecar"
assert_file "$round_dir/cursor-specialist-security-output-phase2.txt.meta" "phase sidecar"
assert_file "$round_dir/cursor-vote-output.txt.json" "cursor json sidecar"
assert_file "$round_dir/codex-vote-output.txt.json" "codex json sidecar"
assert_file "$round_dir/review-round-summary.md" "summary"
assert_file "$round_dir/coder.env" "optional coder env"
assert_not_file "$round_dir/random-notes.txt" "unregistered file"
assert_not_file "$round_dir/session-env.sh" "session env"
assert_not_file "$round_dir/coder-output.log" "excluded coder transcript"
assert_not_file "$round_dir/coder-codex.log" "excluded coder codex transcript"
assert_not_file "$round_dir/codex-specialist-security-output.txt.done" "excluded done sentinel"
assert_not_file "$round_dir/codex-specialist-security-output.txt.inner.done" "excluded inner done sentinel"
assert_not_file "$round_dir/codex-specialist-security-output.txt.diag" "excluded diag sidecar"
assert_not_file "$round_dir/codex-specialist-security-output.txt.prompt" "excluded prompt sidecar"
assert_not_file "$round_dir/codex-specialist-security-output.txt.sidecar" "excluded sidecar"
assert_not_file "$round_dir/codex-specialist-security-output.txt.dirty-tree" "excluded dirty tree sidecar"
assert_not_file "$round_dir/codex-specialist-security-output.txt.untracked-baseline" "excluded untracked baseline sidecar"

assert_grep '<TMPDIR>' "$round_dir/findings.md" "tmpdir path redacted"
assert_grep '<REDACTED-TOKEN>' "$round_dir/findings.md" "secret redacted"
assert_not_grep '^CMD_JSON=' "$round_dir/codex-specialist-security-output.txt.meta" "CMD_JSON stripped"
assert_not_grep '^CMD_JSON=' "$round_dir/cursor-specialist-security-output-phase2.txt.meta" "phase CMD_JSON stripped"
if command -v jq >/dev/null 2>&1; then
    jq -e 'has("result") | not' "$round_dir/cursor-vote-output.txt.json" >/dev/null \
        || fail "cursor .result field should be stripped"
    jq -e 'has("result") | not' "$round_dir/codex-vote-output.txt.json" >/dev/null \
        || fail "codex .result field should be stripped"
fi

out="$("$LARCH_LOG" write-round --log-root "$log_root" --skill implement --run-id run123 --round 1 --source-dir "$source_dir")"
[[ "$out" == *"UNCHANGED=true"* ]] || fail "write-round retry should be unchanged: $out"

"$LARCH_LOG" write-round --log-root "$log_root" --skill implement --run-id run123 --round 2 --source-dir "$source_dir" >/dev/null
assert_file "$log_root/implement/run123/round-2/findings.md" "round-2 findings"

echo "PASS: test-larch-log-write-round.sh"
