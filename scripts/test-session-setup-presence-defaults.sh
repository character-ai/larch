#!/usr/bin/env bash
# test-session-setup-presence-defaults.sh — regression harness for
# session-setup.sh reviewer presence propagation.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SCRIPT="$REPO_ROOT/scripts/session-setup.sh"

[[ -x "$SCRIPT" ]] || { echo "FAIL: $SCRIPT not executable" >&2; exit 1; }

PASS=0
FAIL=0
SANDBOX=$(mktemp -d /tmp/larch-session-setup-presence-test.XXXXXX)
trap 'rm -rf "$SANDBOX"' EXIT

assert_output_value() {
    local output=$1 key=$2 expected=$3 label=$4
    local actual
    actual=$(printf '%s\n' "$output" | awk -F= -v k="$key" '$1==k{print $2; exit}')
    if [[ "$actual" == "$expected" ]]; then
        PASS=$((PASS + 1))
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: $label (expected $key=$expected, got ${actual:-<missing>})"
    fi
}

assert_file_value() {
    local file=$1 key=$2 expected=$3 label=$4
    local actual
    actual=$(awk -F= -v k="$key" '$1==k{print $2; exit}' "$file" 2>/dev/null || true)
    if [[ "$actual" == "$expected" ]]; then
        PASS=$((PASS + 1))
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: $label (expected $key=$expected, got ${actual:-<missing>})"
    fi
}

STUB_BIN="$SANDBOX/bin"
mkdir -p "$STUB_BIN"
cat > "$STUB_BIN/codex" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB
cat > "$STUB_BIN/cursor" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB
chmod +x "$STUB_BIN/codex" "$STUB_BIN/cursor"

ENV1="$SANDBOX/env1.txt"
OUT_ENV1="$SANDBOX/session-env1.txt"
: > "$ENV1"
output=$(PATH="$STUB_BIN:/usr/bin:/bin" "$SCRIPT" \
    --prefix test-presence-1 \
    --skip-preflight \
    --skip-repo-check \
    --caller-env "$ENV1" \
    --check-reviewers \
    --write-session-env "$OUT_ENV1")
assert_output_value "$output" CODEX_PRESENT true "stub codex present on stdout"
assert_output_value "$output" CURSOR_PRESENT true "stub cursor present on stdout"
assert_output_value "$output" CODEX_AVAILABLE true "codex alias on stdout"
assert_output_value "$output" CURSOR_AVAILABLE true "cursor alias on stdout"
assert_file_value "$OUT_ENV1" CODEX_PRESENT true "stub codex present in session-env"
assert_file_value "$OUT_ENV1" CURSOR_PRESENT true "stub cursor present in session-env"
assert_file_value "$OUT_ENV1" CODEX_AVAILABLE true "codex alias in session-env"
assert_file_value "$OUT_ENV1" CURSOR_AVAILABLE true "cursor alias in session-env"

ENV2="$SANDBOX/env2.txt"
OUT_ENV2="$SANDBOX/session-env2.txt"
cat > "$ENV2" <<'EOF'
CODEX_PRESENT=false
CURSOR_PRESENT=true
EOF
output=$(PATH="$STUB_BIN:/usr/bin:/bin" "$SCRIPT" \
    --prefix test-presence-2 \
    --skip-preflight \
    --skip-repo-check \
    --caller-env "$ENV2" \
    --check-reviewers \
    --write-session-env "$OUT_ENV2")
assert_output_value "$output" CODEX_PRESENT false "caller codex false on stdout"
assert_output_value "$output" CURSOR_PRESENT true "caller cursor true on stdout"
assert_file_value "$OUT_ENV2" CODEX_PRESENT false "caller codex false in session-env"
assert_file_value "$OUT_ENV2" CURSOR_PRESENT true "caller cursor true in session-env"

echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] || exit 1
