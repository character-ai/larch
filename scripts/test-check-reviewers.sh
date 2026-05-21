#!/usr/bin/env bash
# Regression test for check-reviewers.sh runtime probe + stamp cache.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
CR="$REPO_ROOT/scripts/check-reviewers.sh"
SCRATCH=$(mktemp -d /tmp/larch-test-check-reviewers-XXXXXX)
trap 'rm -rf "$SCRATCH"' EXIT
FAIL=0

fail() {
    echo "FAIL: $1" >&2
    FAIL=1
}

assert_line() {
    local label="$1" expected="$2" output="$3"
    if grep -Fxq "$expected" <<< "$output"; then
        :
    else
        fail "$label: missing $expected in output: $output"
    fi
}

run_cr() {
    local tmp="$1"
    shift
    mkdir -p "$tmp"
    cd "$REPO_ROOT" && TMPDIR="$tmp" LARCH_QUIET_DISABLE=1 "$@"
}

# --- Baseline stubs (exit 0) ---
STUB_BIN="$SCRATCH/bin0"
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

out=$(run_cr "$SCRATCH/t0" env PATH="$STUB_BIN:/usr/bin:/bin" LARCH_PROBE_TTL_SECONDS=0 LARCH_EXTERNAL_AUTH_RETRIES=3 \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux "$CR")
assert_line "codex binary" "CODEX_BINARY_FOUND=true" "$out"
assert_line "cursor binary" "CURSOR_BINARY_FOUND=true" "$out"
assert_line "codex present" "CODEX_PRESENT=true" "$out"
assert_line "cursor present" "CURSOR_PRESENT=true" "$out"

out=$(run_cr "$SCRATCH/t0b" env PATH="/usr/bin:/bin" LARCH_PROBE_TTL_SECONDS=0 "$CR")
assert_line "codex absent binary" "CODEX_BINARY_FOUND=false" "$out"
assert_line "cursor absent binary" "CURSOR_BINARY_FOUND=false" "$out"
assert_line "codex absent" "CODEX_PRESENT=false" "$out"
assert_line "cursor absent" "CURSOR_PRESENT=false" "$out"

out=$(run_cr "$SCRATCH/t0c" env PATH="$STUB_BIN:/usr/bin:/bin" LARCH_PROBE_TTL_SECONDS=0 \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux "$CR" --skip-codex-probe)
assert_line "skip codex present" "CODEX_PRESENT=false" "$out"
assert_line "skip codex bin" "CODEX_BINARY_FOUND=true" "$out"
assert_line "skip codex cursor still present" "CURSOR_PRESENT=true" "$out"

out=$(run_cr "$SCRATCH/t0d" env PATH="$STUB_BIN:/usr/bin:/bin" LARCH_PROBE_TTL_SECONDS=0 \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux "$CR" --skip-cursor-probe)
assert_line "skip cursor" "CURSOR_PRESENT=false" "$out"
assert_line "skip cursor codex still present" "CODEX_PRESENT=true" "$out"

# --- Cursor: probe failure non-auth ---
SB1="$SCRATCH/bin1"
mkdir -p "$SB1"
cat > "$SB1/cursor" <<'STUB'
#!/usr/bin/env bash
echo 'some generic failure' >&2
exit 1
STUB
chmod +x "$SB1/cursor"
out=$(run_cr "$SCRATCH/t1" env PATH="$SB1:/usr/bin:/bin" LARCH_PROBE_TTL_SECONDS=0 \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux LARCH_EXTERNAL_AUTH_RETRIES=3 "$CR")
assert_line "cursor probe fail" "CURSOR_PRESENT=false" "$out"

# --- Cursor: auth retry then success ---
SB2="$SCRATCH/bin2"
mkdir -p "$SB2"
cat > "$SB2/cursor" <<'STUB'
#!/usr/bin/env bash
f="${LARCH_TEST_CURSOR_STATE:?}"
n=$(cat "$f" 2>/dev/null || echo 0)
echo "$((n + 1))" >"$f"
if (( n < 2 )); then
  echo 'authentication failed' >&2
  exit 1
fi
exit 0
STUB
chmod +x "$SB2/cursor"
out=$(run_cr "$SCRATCH/t2" env PATH="$SB2:/usr/bin:/bin" LARCH_PROBE_TTL_SECONDS=0 \
    LARCH_TEST_CURSOR_STATE="$SCRATCH/t2/attempts" \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux LARCH_EXTERNAL_AUTH_RETRIES=5 "$CR")
assert_line "cursor auth retry ok" "CURSOR_PRESENT=true" "$out"

# --- Cursor: auth retry exhausted ---
SB3="$SCRATCH/bin3"
mkdir -p "$SB3"
cat > "$SB3/cursor" <<'STUB'
#!/usr/bin/env bash
echo 'authentication failed' >&2
exit 1
STUB
chmod +x "$SB3/cursor"
out=$(run_cr "$SCRATCH/t3" env PATH="$SB3:/usr/bin:/bin" LARCH_PROBE_TTL_SECONDS=0 \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux LARCH_EXTERNAL_AUTH_RETRIES=2 "$CR")
assert_line "cursor auth exhausted" "CURSOR_PRESENT=false" "$out"

# --- Cursor: stamp cache hit ---
SB4="$SCRATCH/bin4"
mkdir -p "$SB4"
cat > "$SB4/cursor" <<'STUB'
#!/usr/bin/env bash
echo invoked >&2
exit 1
STUB
chmod +x "$SB4/cursor"
mkdir -p "$SCRATCH/t4"
stamp="$SCRATCH/t4/larch-cursor-present-${USER:-larch}.stamp"
printf 'true\n' >"$stamp"
touch "$stamp"
out=$(run_cr "$SCRATCH/t4" env PATH="$SB4:/usr/bin:/bin" LARCH_PROBE_TTL_SECONDS=3600 \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux LARCH_EXTERNAL_AUTH_RETRIES=3 "$CR")
assert_line "cursor stamp hit" "CURSOR_PRESENT=true" "$out"

# --- Cursor: stamp expired re-probe ---
SB5="$SCRATCH/bin5"
mkdir -p "$SB5"
cat > "$SB5/cursor" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB
chmod +x "$SB5/cursor"
mkdir -p "$SCRATCH/t5"
stamp5="$SCRATCH/t5/larch-cursor-present-${USER:-larch}.stamp"
printf 'false\n' >"$stamp5"
touch -t 200001010000 "$stamp5" 2>/dev/null || touch -A "-876000" "$stamp5" 2>/dev/null || true
out=$(run_cr "$SCRATCH/t5" env PATH="$SB5:/usr/bin:/bin" LARCH_PROBE_TTL_SECONDS=60 \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux LARCH_EXTERNAL_AUTH_RETRIES=3 "$CR")
assert_line "cursor stamp expired" "CURSOR_PRESENT=true" "$out"

# --- Codex matrix ---
SB6="$SCRATCH/bin6"
mkdir -p "$SB6"
cat > "$SB6/codex" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB
chmod +x "$SB6/codex"
out=$(run_cr "$SCRATCH/t6" env PATH="$SB6:/usr/bin:/bin" LARCH_PROBE_TTL_SECONDS=0 LARCH_EXTERNAL_AUTH_RETRIES=3 "$CR")
assert_line "codex ok" "CODEX_PRESENT=true" "$out"

SB7="$SCRATCH/bin7"
mkdir -p "$SB7"
cat > "$SB7/codex" <<'STUB'
#!/usr/bin/env bash
echo 'build failed' >&2
exit 1
STUB
chmod +x "$SB7/codex"
out=$(run_cr "$SCRATCH/t7" env PATH="$SB7:/usr/bin:/bin" LARCH_PROBE_TTL_SECONDS=0 LARCH_EXTERNAL_AUTH_RETRIES=3 "$CR")
assert_line "codex non-auth" "CODEX_PRESENT=false" "$out"

SB8="$SCRATCH/bin8"
mkdir -p "$SB8"
cat > "$SB8/codex" <<'STUB'
#!/usr/bin/env bash
f="${LARCH_TEST_CODEX_STATE:?}"
n=$(cat "$f" 2>/dev/null || echo 0)
echo "$((n + 1))" >"$f"
if (( n < 2 )); then
  echo 'login required' >&2
  exit 1
fi
exit 0
STUB
chmod +x "$SB8/codex"
out=$(run_cr "$SCRATCH/t8" env PATH="$SB8:/usr/bin:/bin" LARCH_PROBE_TTL_SECONDS=0 \
    LARCH_TEST_CODEX_STATE="$SCRATCH/t8/c" LARCH_EXTERNAL_AUTH_RETRIES=5 "$CR")
assert_line "codex auth retry" "CODEX_PRESENT=true" "$out"

SB9="$SCRATCH/bin9"
mkdir -p "$SB9"
cat > "$SB9/codex" <<'STUB'
#!/usr/bin/env bash
echo 'login required' >&2
exit 1
STUB
chmod +x "$SB9/codex"
out=$(run_cr "$SCRATCH/t9" env PATH="$SB9:/usr/bin:/bin" LARCH_PROBE_TTL_SECONDS=0 LARCH_EXTERNAL_AUTH_RETRIES=2 "$CR")
assert_line "codex auth exhaust" "CODEX_PRESENT=false" "$out"

mkdir -p "$SCRATCH/t10"
SB10="$SCRATCH/bin10"
mkdir -p "$SB10"
cat > "$SB10/codex" <<'STUB'
#!/usr/bin/env bash
exit 1
STUB
chmod +x "$SB10/codex"
st10="$SCRATCH/t10/larch-codex-present-${USER:-larch}.stamp"
printf 'true\n' >"$st10"
touch "$st10"
out=$(run_cr "$SCRATCH/t10" env PATH="$SB10:/usr/bin:/bin" LARCH_PROBE_TTL_SECONDS=3600 LARCH_EXTERNAL_AUTH_RETRIES=3 "$CR")
assert_line "codex stamp hit" "CODEX_PRESENT=true" "$out"

mkdir -p "$SCRATCH/t11"
SB11="$SCRATCH/bin11"
mkdir -p "$SB11"
cat > "$SB11/codex" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB
chmod +x "$SB11/codex"
st11="$SCRATCH/t11/larch-codex-present-${USER:-larch}.stamp"
printf 'false\n' >"$st11"
touch -t 200001010000 "$st11" 2>/dev/null || touch -A "-876000" "$st11" 2>/dev/null || true
out=$(run_cr "$SCRATCH/t11" env PATH="$SB11:/usr/bin:/bin" LARCH_PROBE_TTL_SECONDS=60 LARCH_EXTERNAL_AUTH_RETRIES=3 "$CR")
assert_line "codex stamp expired" "CODEX_PRESENT=true" "$out"

SB12="$SCRATCH/bin12"
mkdir -p "$SB12"
cat > "$SB12/codex" <<'STUB'
#!/usr/bin/env bash
exit 1
STUB
chmod +x "$SB12/codex"
out=$(run_cr "$SCRATCH/t12" env PATH="$SB12:/usr/bin:/bin" LARCH_PROBE_TTL_SECONDS=0 "$CR" --skip-codex-probe)
assert_line "codex skip" "CODEX_PRESENT=false" "$out"

out=$(run_cr "$SCRATCH/t13" env PATH="$STUB_BIN:/usr/bin:/bin" \
    LARCH_PROBE_TTL_SECONDS=abc LARCH_PROBE_TIMEOUT_SECONDS=0 \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux LARCH_EXTERNAL_AUTH_RETRIES=3 "$CR")
assert_line "env norm" "CURSOR_PRESENT=true" "$out"

set +e
"$CR" --probe >/dev/null 2>"$SCRATCH/unknown.stderr"
rc=$?
set -e
if [[ "$rc" -eq 1 ]] && grep -Fq "unknown argument: --probe" "$SCRATCH/unknown.stderr"; then
    :
else
    fail "--probe should exit 1 with unknown argument stderr (got rc=$rc)"
fi

if [[ "$FAIL" -eq 1 ]]; then
    echo "FAIL: test-check-reviewers.sh" >&2
    exit 1
fi

echo "PASS: test-check-reviewers.sh"
