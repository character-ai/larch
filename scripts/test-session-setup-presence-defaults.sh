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

ENV3="$SANDBOX/env3.txt"
OUT_ENV3="$SANDBOX/session-env3.txt"
cat > "$ENV3" <<'EOF'
CODEX_PRESENT=true
CURSOR_PRESENT=false
LARCH_DYNAMIC_ARCHETYPES_MAX=3
EOF
output=$(PATH="$STUB_BIN:/usr/bin:/bin" "$SCRIPT" \
    --prefix test-presence-3 \
    --skip-preflight \
    --skip-repo-check \
    --caller-env "$ENV3" \
    --check-reviewers \
    --write-session-env "$OUT_ENV3")
assert_file_value "$OUT_ENV3" LARCH_DYNAMIC_ARCHETYPES_MAX 3 "caller dynamic archetypes forwarded to session-env"

ENV4="$SANDBOX/env4.txt"
OUT_ENV4="$SANDBOX/session-env4.txt"
ERR4="$SANDBOX/session-env4.err"
cat > "$ENV4" <<'EOF'
CODEX_PRESENT=true
CURSOR_PRESENT=false
LARCH_DYNAMIC_ARCHETYPES_MAX=9
EOF
output=$(PATH="$STUB_BIN:/usr/bin:/bin" "$SCRIPT" \
    --prefix test-presence-4 \
    --skip-preflight \
    --skip-repo-check \
    --caller-env "$ENV4" \
    --check-reviewers \
    --write-session-env "$OUT_ENV4" \
    2>"$ERR4")
assert_file_value "$OUT_ENV4" LARCH_DYNAMIC_ARCHETYPES_MAX "" "invalid caller dynamic archetypes omitted from session-env"
grep -Fq "session-setup.sh: warning: ignoring invalid LARCH_DYNAMIC_ARCHETYPES_MAX from caller-env (must be 0..4)" "$ERR4" \
    || { FAIL=$((FAIL + 1)); echo "FAIL: invalid caller dynamic archetypes warning missing"; }

echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] || exit 1
