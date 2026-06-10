#!/usr/bin/env bash
# Regression test for check-reviewers.sh runtime probe + stamp cache.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
CR="$REPO_ROOT/scripts/check-reviewers.sh"
PYTHON_BIN=$(command -v python3)
SCRATCH=$(mktemp -d /tmp/larch-test-check-reviewers-XXXXXX)
trap 'rm -rf "$SCRATCH"' EXIT
FAIL=0
STAMP_USER="${USER//[^A-Za-z0-9._-]/}"
STAMP_USER="${STAMP_USER:-larch}"

fail() {
    echo "FAIL: $1" >&2
    FAIL=1
}

assert_no_probe_homes() {
    local label="$1" tmpdir="$2"
    local survivors
    survivors=$(find "$tmpdir" -maxdepth 1 -name 'larch-codex-probe-home.*' 2>/dev/null || true)
    if [[ -z "$survivors" ]]; then
        :
    else
        fail "$label: probe temp homes survived: $survivors"
    fi
}

assert_argv_immediately_after_c() {
    local label="$1" argv_file="$2" config_value="$3"
    if awk -v want="$config_value" '
        NR > 1 && $0 == want && prev == "-c" { ok = 1; exit }
        { prev = $0 }
        END { exit ok ? 0 : 1 }
    ' "$argv_file" 2>/dev/null; then
        :
    else
        fail "$label: expected -c immediately before '$config_value'"
    fi
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
    ( cd "$REPO_ROOT" && TMPDIR="$tmp" LARCH_QUIET_DISABLE=1 env -u OPENAI_API_KEY "$@" )
}

run_cr_with_env() {
    local tmp="$1"
    shift
    mkdir -p "$tmp"
    ( cd "$REPO_ROOT" && TMPDIR="$tmp" LARCH_QUIET_DISABLE=1 "$@" )
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
assert_line "codex available alias" "CODEX_AVAILABLE=true" "$out"
assert_line "cursor available alias" "CURSOR_AVAILABLE=true" "$out"

out=$(run_cr "$SCRATCH/t0b" env PATH="/usr/bin:/bin" LARCH_PROBE_TTL_SECONDS=0 "$CR")
assert_line "codex absent binary" "CODEX_BINARY_FOUND=false" "$out"
assert_line "cursor absent binary" "CURSOR_BINARY_FOUND=false" "$out"
assert_line "codex absent" "CODEX_PRESENT=false" "$out"
assert_line "cursor absent" "CURSOR_PRESENT=false" "$out"
assert_line "codex available alias absent" "CODEX_AVAILABLE=false" "$out"
assert_line "cursor available alias absent" "CURSOR_AVAILABLE=false" "$out"

out=$(run_cr "$SCRATCH/t0c" env PATH="$STUB_BIN:/usr/bin:/bin" LARCH_PROBE_TTL_SECONDS=0 \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux "$CR" --skip-codex-probe)
assert_line "skip codex present" "CODEX_PRESENT=false" "$out"
assert_line "skip codex bin" "CODEX_BINARY_FOUND=true" "$out"
assert_line "skip codex cursor still present" "CURSOR_PRESENT=true" "$out"
assert_line "skip codex cursor binary" "CURSOR_BINARY_FOUND=true" "$out"

out=$(run_cr "$SCRATCH/t0d" env PATH="$STUB_BIN:/usr/bin:/bin" LARCH_PROBE_TTL_SECONDS=0 \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux "$CR" --skip-cursor-probe)
assert_line "skip cursor" "CURSOR_PRESENT=false" "$out"
assert_line "skip cursor codex still present" "CODEX_PRESENT=true" "$out"
assert_line "skip cursor codex binary" "CODEX_BINARY_FOUND=true" "$out"
assert_line "skip cursor cursor binary" "CURSOR_BINARY_FOUND=true" "$out"

# --- Cursor: probe failure non-auth ---
SB1="$SCRATCH/bin1"
mkdir -p "$SB1"
cat > "$SB1/cursor" <<'STUB'
#!/usr/bin/env bash
echo 'some generic failure' >&2
exit 1
STUB
chmod +x "$SB1/cursor"
cat > "$SB1/codex" <<'STUB'
#!/usr/bin/env bash
exit 127
STUB
chmod +x "$SB1/codex"
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
cat > "$SB2/codex" <<'STUB'
#!/usr/bin/env bash
exit 127
STUB
chmod +x "$SB2/codex"
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
cat > "$SB3/codex" <<'STUB'
#!/usr/bin/env bash
exit 127
STUB
chmod +x "$SB3/codex"
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
cat > "$SB4/codex" <<'STUB'
#!/usr/bin/env bash
exit 127
STUB
chmod +x "$SB4/codex"
mkdir -p "$SCRATCH/t4"
stamp="$SCRATCH/t4/larch-cursor-present-${STAMP_USER}.stamp"
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
cat > "$SB5/codex" <<'STUB'
#!/usr/bin/env bash
exit 127
STUB
chmod +x "$SB5/codex"
mkdir -p "$SCRATCH/t5"
stamp5="$SCRATCH/t5/larch-cursor-present-${STAMP_USER}.stamp"
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
cat > "$SB6/cursor" <<'STUB'
#!/usr/bin/env bash
exit 127
STUB
chmod +x "$SB6/cursor"
out=$(run_cr "$SCRATCH/t6" env PATH="$SB6:/usr/bin:/bin" LARCH_PROBE_TTL_SECONDS=0 \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux LARCH_EXTERNAL_AUTH_RETRIES=3 "$CR")
assert_line "codex ok" "CODEX_PRESENT=true" "$out"
assert_line "codex ok binary" "CODEX_BINARY_FOUND=true" "$out"
assert_no_probe_homes "codex ok cleanup" "$SCRATCH/t6"
if [[ -f "$SCRATCH/t6/larch-codex-login-present-${STAMP_USER}.stamp" ]] \
   && [[ "$(cat "$SCRATCH/t6/larch-codex-login-present-${STAMP_USER}.stamp" 2>/dev/null)" == "true" ]] \
   && [[ ! -f "$SCRATCH/t6/larch-codex-env-key-present-${STAMP_USER}.stamp" ]]; then
    :
else
    fail "codex login probe should write only login stamp"
fi

SB6E="$SCRATCH/bin6e"
mkdir -p "$SB6E" "$SCRATCH/t6e"
cat > "$SB6E/codex" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB
chmod +x "$SB6E/codex"
cat > "$SB6E/cursor" <<'STUB'
#!/usr/bin/env bash
exit 127
STUB
chmod +x "$SB6E/cursor"
printf 'false\n' > "$SCRATCH/t6e/larch-codex-login-present-${STAMP_USER}.stamp"
touch "$SCRATCH/t6e/larch-codex-login-present-${STAMP_USER}.stamp"
out=$(run_cr_with_env "$SCRATCH/t6e" env PATH="$SB6E:/usr/bin:/bin" LARCH_PROBE_TTL_SECONDS=3600 \
    OPENAI_API_KEY=sk-larch-probe-sentinel \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux LARCH_EXTERNAL_AUTH_RETRIES=3 "$CR")
assert_line "codex env-key ignores fresh login false stamp" "CODEX_PRESENT=true" "$out"
if [[ -f "$SCRATCH/t6e/larch-codex-env-key-present-${STAMP_USER}.stamp" ]] \
   && [[ "$(cat "$SCRATCH/t6e/larch-codex-env-key-present-${STAMP_USER}.stamp" 2>/dev/null)" == "true" ]] \
   && [[ "$(cat "$SCRATCH/t6e/larch-codex-login-present-${STAMP_USER}.stamp" 2>/dev/null)" == "false" ]]; then
    :
else
    fail "codex env-key probe should write only env-key stamp (login decoy unchanged)"
fi
if grep -Fr 'sk-larch-probe-sentinel' "$SCRATCH/t6e" 2>/dev/null; then
    fail "codex env-key login-decoy probe must not leak OPENAI_API_KEY sentinel into TMPDIR"
fi
assert_no_probe_homes "codex env-key login-decoy cleanup" "$SCRATCH/t6e"

# --- Codex: probe forwards production model args ---
SB6M="$SCRATCH/bin6m"
mkdir -p "$SB6M" "$SCRATCH/t6m"
CODEX_PROBE_ARGV_LOG="$SCRATCH/t6m/codex-probe-argv.log"
: >"$CODEX_PROBE_ARGV_LOG"
cat > "$SB6M/codex" <<'STUB'
#!/usr/bin/env bash
printf '%s\n' "$@" >>"${LARCH_TEST_CODEX_PROBE_ARGV_LOG:?}"
exit 0
STUB
chmod +x "$SB6M/codex"
cat > "$SB6M/cursor" <<'STUB'
#!/usr/bin/env bash
exit 127
STUB
chmod +x "$SB6M/cursor"
out=$(run_cr "$SCRATCH/t6m" env PATH="$SB6M:/usr/bin:/bin" LARCH_PROBE_TTL_SECONDS=0 \
    LARCH_CODEX_MODEL="sentinel-model" LARCH_TEST_CODEX_PROBE_ARGV_LOG="$CODEX_PROBE_ARGV_LOG" \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux LARCH_EXTERNAL_AUTH_RETRIES=3 "$CR")
assert_line "codex probe model present" "CODEX_PRESENT=true" "$out"
grep -Fq 'sentinel-model' "$CODEX_PROBE_ARGV_LOG" || fail "codex probe argv must include sentinel-model"

SB7="$SCRATCH/bin7"
mkdir -p "$SB7"
cat > "$SB7/codex" <<'STUB'
#!/usr/bin/env bash
echo 'build failed' >&2
exit 1
STUB
chmod +x "$SB7/codex"
cat > "$SB7/cursor" <<'STUB'
#!/usr/bin/env bash
exit 127
STUB
chmod +x "$SB7/cursor"
out=$(run_cr "$SCRATCH/t7" env PATH="$SB7:/usr/bin:/bin" LARCH_PROBE_TTL_SECONDS=0 \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux LARCH_EXTERNAL_AUTH_RETRIES=3 "$CR")
assert_line "codex non-auth" "CODEX_PRESENT=false" "$out"
assert_line "codex non-auth binary" "CODEX_BINARY_FOUND=true" "$out"
assert_no_probe_homes "codex non-auth cleanup" "$SCRATCH/t7"

SB7A="$SCRATCH/bin7a"
mkdir -p "$SB7A" "$SCRATCH/t7a-home/.codex"
cat > "$SB7A/codex" <<'STUB'
#!/usr/bin/env bash
printf 'codex should not be invoked after auth-prep failure\n' >&2
exit 0
STUB
chmod +x "$SB7A/codex"
cat > "$SB7A/cursor" <<'STUB'
#!/usr/bin/env bash
exit 127
STUB
chmod +x "$SB7A/cursor"
printf 'model_provider = "openai-larch-env"\n' > "$SCRATCH/t7a-home/.codex/config.toml"
chmod a-w "$SCRATCH/t7a-home/.codex/config.toml" 2>/dev/null || true
out=$(run_cr "$SCRATCH/t7a" env PATH="$SB7A:/usr/bin:/bin" HOME="$SCRATCH/t7a-home" LARCH_PROBE_TTL_SECONDS=0 \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux LARCH_EXTERNAL_AUTH_RETRIES=3 "$CR")
chmod u+w "$SCRATCH/t7a-home/.codex/config.toml" 2>/dev/null || true
assert_line "codex auth-prep failure non-aborting" "CODEX_PRESENT=false" "$out"
assert_line "codex auth-prep failure still emits cursor" "CURSOR_PRESENT=false" "$out"
assert_no_probe_homes "codex auth-prep failure cleanup" "$SCRATCH/t7a"

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
cat > "$SB8/cursor" <<'STUB'
#!/usr/bin/env bash
exit 127
STUB
chmod +x "$SB8/cursor"
out=$(run_cr "$SCRATCH/t8" env PATH="$SB8:/usr/bin:/bin" LARCH_PROBE_TTL_SECONDS=0 \
    LARCH_TEST_CODEX_STATE="$SCRATCH/t8/c" \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux LARCH_EXTERNAL_AUTH_RETRIES=5 "$CR")
assert_line "codex auth retry" "CODEX_PRESENT=true" "$out"
assert_no_probe_homes "codex auth retry cleanup" "$SCRATCH/t8"

SB9="$SCRATCH/bin9"
mkdir -p "$SB9"
cat > "$SB9/codex" <<'STUB'
#!/usr/bin/env bash
echo 'login required' >&2
exit 1
STUB
chmod +x "$SB9/codex"
cat > "$SB9/cursor" <<'STUB'
#!/usr/bin/env bash
exit 127
STUB
chmod +x "$SB9/cursor"
out=$(run_cr "$SCRATCH/t9" env PATH="$SB9:/usr/bin:/bin" LARCH_PROBE_TTL_SECONDS=0 \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux LARCH_EXTERNAL_AUTH_RETRIES=2 "$CR")
assert_line "codex auth exhaust" "CODEX_PRESENT=false" "$out"
assert_line "codex auth exhaust binary" "CODEX_BINARY_FOUND=true" "$out"
assert_no_probe_homes "codex auth exhaust cleanup" "$SCRATCH/t9"

mkdir -p "$SCRATCH/t10"
SB10="$SCRATCH/bin10"
mkdir -p "$SB10"
cat > "$SB10/codex" <<'STUB'
#!/usr/bin/env bash
exit 1
STUB
chmod +x "$SB10/codex"
cat > "$SB10/cursor" <<'STUB'
#!/usr/bin/env bash
exit 127
STUB
chmod +x "$SB10/cursor"
st10="$SCRATCH/t10/larch-codex-login-present-${STAMP_USER}.stamp"
printf 'true\n' >"$st10"
touch "$st10"
out=$(run_cr "$SCRATCH/t10" env PATH="$SB10:/usr/bin:/bin" LARCH_PROBE_TTL_SECONDS=3600 \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux LARCH_EXTERNAL_AUTH_RETRIES=3 "$CR")
assert_line "codex stamp hit" "CODEX_PRESENT=true" "$out"
assert_line "codex stamp hit binary" "CODEX_BINARY_FOUND=true" "$out"

mkdir -p "$SCRATCH/t10-env-key"
SB10E="$SCRATCH/bin10-env-key"
mkdir -p "$SB10E"
cat > "$SB10E/codex" <<'STUB'
#!/usr/bin/env bash
printf '%s\n' "$@" >"${LARCH_TEST_CODEX_ARGV_LOG:?}"
exit 1
STUB
chmod +x "$SB10E/codex"
cat > "$SB10E/cursor" <<'STUB'
#!/usr/bin/env bash
exit 127
STUB
chmod +x "$SB10E/cursor"
st10e="$SCRATCH/t10-env-key/larch-codex-env-key-present-${STAMP_USER}.stamp"
printf 'true\n' >"$st10e"
touch "$st10e"
out=$(cd "$REPO_ROOT" && TMPDIR="$SCRATCH/t10-env-key" PATH="$SB10E:/usr/bin:/bin" LARCH_QUIET_DISABLE=1 \
    OPENAI_API_KEY=sk-larch-probe-sentinel LARCH_TEST_CODEX_ARGV_LOG="$SCRATCH/t10-env-key/codex-argv.log" \
    LARCH_PROBE_TTL_SECONDS=3600 LARCH_EXTERNAL_AUTH_RETRIES=1 \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux "$CR")
assert_line "codex env-key true stamp uses cache" "CODEX_PRESENT=true" "$out"
if [[ -s "$SCRATCH/t10-env-key/codex-argv.log" ]]; then
    fail "codex env-key true stamp should not invoke live probe"
fi

mkdir -p "$SCRATCH/t10-env-key-false"
SB10EF="$SCRATCH/bin10-env-key-false"
mkdir -p "$SB10EF"
cat > "$SB10EF/codex" <<'STUB'
#!/usr/bin/env bash
printf '%s\n' "$@" >"${LARCH_TEST_CODEX_ARGV_LOG:?}"
exit 0
STUB
chmod +x "$SB10EF/codex"
cat > "$SB10EF/cursor" <<'STUB'
#!/usr/bin/env bash
exit 127
STUB
chmod +x "$SB10EF/cursor"
st10ef="$SCRATCH/t10-env-key-false/larch-codex-env-key-present-${STAMP_USER}.stamp"
printf 'false\n' >"$st10ef"
touch "$st10ef"
out=$(cd "$REPO_ROOT" && TMPDIR="$SCRATCH/t10-env-key-false" PATH="$SB10EF:/usr/bin:/bin" LARCH_QUIET_DISABLE=1 \
    OPENAI_API_KEY=sk-larch-probe-sentinel LARCH_TEST_CODEX_ARGV_LOG="$SCRATCH/t10-env-key-false/codex-argv.log" \
    LARCH_PROBE_TTL_SECONDS=3600 LARCH_EXTERNAL_AUTH_RETRIES=1 \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux "$CR")
assert_line "codex env-key false stamp retries live probe" "CODEX_PRESENT=true" "$out"
if ! grep -Fq 'model_providers.openai-larch-env.env_key="OPENAI_API_KEY"' "$SCRATCH/t10-env-key-false/codex-argv.log" 2>/dev/null; then
    fail "codex env-key false stamp should invoke live env-key probe"
fi
_project_key=${REPO_ROOT//\\/\\\\}
_project_key=${_project_key//\"/\\\"}
_trust_expected="projects.\"${_project_key}\".trust_level=\"trusted\""
assert_argv_immediately_after_c "codex env-key false trusted-project -c adjacency" \
    "$SCRATCH/t10-env-key-false/codex-argv.log" "$_trust_expected"
assert_argv_immediately_after_c "codex env-key false model_provider -c adjacency" \
    "$SCRATCH/t10-env-key-false/codex-argv.log" 'model_provider="openai-larch-env"'
assert_argv_immediately_after_c "codex env-key false env_key -c adjacency" \
    "$SCRATCH/t10-env-key-false/codex-argv.log" 'model_providers.openai-larch-env.env_key="OPENAI_API_KEY"'
if grep -Fr 'sk-larch-probe-sentinel' "$SCRATCH/t10-env-key-false" 2>/dev/null; then
    fail "codex env-key false probe must not leak OPENAI_API_KEY sentinel into TMPDIR"
fi
assert_no_probe_homes "codex env-key false cleanup" "$SCRATCH/t10-env-key-false"

mkdir -p "$SCRATCH/t11"
SB11="$SCRATCH/bin11"
mkdir -p "$SB11"
cat > "$SB11/codex" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB
chmod +x "$SB11/codex"
cat > "$SB11/cursor" <<'STUB'
#!/usr/bin/env bash
exit 127
STUB
chmod +x "$SB11/cursor"
st11="$SCRATCH/t11/larch-codex-login-present-${STAMP_USER}.stamp"
printf 'false\n' >"$st11"
touch -t 200001010000 "$st11" 2>/dev/null || touch -A "-876000" "$st11" 2>/dev/null || true
out=$(run_cr "$SCRATCH/t11" env PATH="$SB11:/usr/bin:/bin" LARCH_PROBE_TTL_SECONDS=60 \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux LARCH_EXTERNAL_AUTH_RETRIES=3 "$CR")
assert_line "codex stamp expired" "CODEX_PRESENT=true" "$out"
assert_line "codex stamp expired binary" "CODEX_BINARY_FOUND=true" "$out"

SB12="$SCRATCH/bin12"
mkdir -p "$SB12"
cat > "$SB12/codex" <<'STUB'
#!/usr/bin/env bash
exit 1
STUB
chmod +x "$SB12/codex"
cat > "$SB12/cursor" <<'STUB'
#!/usr/bin/env bash
exit 127
STUB
chmod +x "$SB12/cursor"
out=$(run_cr "$SCRATCH/t12" env PATH="$SB12:/usr/bin:/bin" LARCH_PROBE_TTL_SECONDS=0 \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux "$CR" --skip-codex-probe)
assert_line "codex skip" "CODEX_PRESENT=false" "$out"
assert_line "skip codex bin found" "CODEX_BINARY_FOUND=true" "$out"

out=$(run_cr "$SCRATCH/t13" env PATH="$STUB_BIN:/usr/bin:/bin" \
    LARCH_PROBE_TTL_SECONDS=abc LARCH_PROBE_TIMEOUT_SECONDS=0 \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux LARCH_EXTERNAL_AUTH_RETRIES=3 "$CR")
assert_line "env norm" "CURSOR_PRESENT=true" "$out"
assert_line "env norm codex" "CODEX_PRESENT=true" "$out"

out=$(run_cr "$SCRATCH/t14" env PATH="$SB2:/usr/bin:/bin" LARCH_PROBE_TTL_SECONDS=0 \
    LARCH_TEST_CURSOR_STATE="$SCRATCH/t14/attempts" \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux LARCH_EXTERNAL_AUTH_RETRIES=0 "$CR")
assert_line "auth retries zero normalizes" "CURSOR_PRESENT=true" "$out"

SESS_W="$SCRATCH/written-session.env"
rm -f "$SESS_W"
mkdir -p "$SCRATCH/sess-env-test"
cd "$REPO_ROOT" && TMPDIR="$SCRATCH/sess-env-test" PATH="$STUB_BIN:/usr/bin:/bin" LARCH_QUIET_DISABLE=1 \
    LARCH_PROBE_TTL_SECONDS=0 LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux \
    "$PYTHON_BIN" "$REPO_ROOT/python/cli.py" session setup \
    --prefix larch-tchkrev-ss \
    --skip-preflight --skip-repo-check \
    --check-reviewers --write-session-env "$SESS_W" >/dev/null
sess_content=$(cat "$SESS_W")
assert_line "session-setup wrote codex bin" "CODEX_BINARY_FOUND=true" "$sess_content"
assert_line "session-setup wrote cursor bin" "CURSOR_BINARY_FOUND=true" "$sess_content"

SB_TO="$SCRATCH/bin-probe-timeout"
mkdir -p "$SB_TO"
for _tool in codex cursor; do
    cat > "$SB_TO/$_tool" <<'STUB'
#!/usr/bin/env bash
sleep 300
exit 0
STUB
    chmod +x "$SB_TO/$_tool"
done
_probe_to_start=$SECONDS
out=$(run_cr "$SCRATCH/t-probe-to" env PATH="$SB_TO:/usr/bin:/bin" \
    LARCH_PROBE_TTL_SECONDS=0 LARCH_PROBE_TIMEOUT_SECONDS=2 \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux \
    LARCH_EXTERNAL_AUTH_RETRIES=1 "$CR")
_probe_to_el=$((SECONDS - _probe_to_start))
if ((_probe_to_el > 30)); then
    fail "probe timeout test wall-clock too high (${_probe_to_el}s)"
fi
assert_line "probe timeout codex" "CODEX_PRESENT=false" "$out"
assert_line "probe timeout cursor" "CURSOR_PRESENT=false" "$out"
assert_no_probe_homes "probe timeout codex cleanup" "$SCRATCH/t-probe-to"

# --- Legacy env-key strip via probe temp config capture ---
mkdir -p "$SCRATCH/t-legacy-strip-home/.codex"
printf '%s\n' \
    'model_provider = "openai-larch-env"' \
    'env_key = "OPENAI_API_KEY"' \
    'api_key = "sk-larch-legacy-strip-sentinel"' \
    '[profiles.keep]' \
    'model = "ok"' > "$SCRATCH/t-legacy-strip-home/.codex/config.toml"
_legacy_fixture="$SCRATCH/t-legacy-strip-home/.codex/config.toml"
_legacy_fixture_copy="$SCRATCH/t-legacy-strip-fixture-copy.toml"
cp "$_legacy_fixture" "$_legacy_fixture_copy"
SB_LEGACY="$SCRATCH/bin-legacy-strip"
mkdir -p "$SB_LEGACY"
cat > "$SB_LEGACY/codex" <<'STUB'
#!/usr/bin/env bash
if [[ -n "${LARCH_TEST_CODEX_CONFIG_CAPTURE:-}" && -n "${CODEX_HOME:-}" && -f "$CODEX_HOME/config.toml" ]]; then
    cp "$CODEX_HOME/config.toml" "$LARCH_TEST_CODEX_CONFIG_CAPTURE"
fi
exit 0
STUB
chmod +x "$SB_LEGACY/codex"
cat > "$SB_LEGACY/cursor" <<'STUB'
#!/usr/bin/env bash
exit 127
STUB
chmod +x "$SB_LEGACY/cursor"
_legacy_capture="$SCRATCH/t-legacy-strip/captured-config.toml"
out=$(run_cr_with_env "$SCRATCH/t-legacy-strip" env PATH="$SB_LEGACY:/usr/bin:/bin" \
    HOME="$SCRATCH/t-legacy-strip-home" LARCH_PROBE_TTL_SECONDS=0 \
    OPENAI_API_KEY=sk-larch-legacy-strip-sentinel \
    LARCH_TEST_CODEX_CONFIG_CAPTURE="$_legacy_capture" \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux LARCH_EXTERNAL_AUTH_RETRIES=3 "$CR")
assert_line "legacy env-key strip probe ok" "CODEX_PRESENT=true" "$out"
assert_no_probe_homes "legacy env-key strip cleanup" "$SCRATCH/t-legacy-strip"
if [[ -f "$_legacy_capture" ]]; then
    :
else
    fail "legacy env-key strip must capture temp CODEX_HOME config"
fi
grep -Fq 'model_provider = "openai-larch-env"' "$_legacy_capture" 2>/dev/null \
    && fail "legacy env-key strip must remove larch selector from temp config"
grep -Fq 'env_key = "OPENAI_API_KEY"' "$_legacy_capture" 2>/dev/null \
    && fail "legacy env-key strip must remove env_key from temp config"
grep -Fq 'sk-larch-legacy-strip-sentinel' "$_legacy_capture" 2>/dev/null \
    && fail "legacy env-key strip must remove literal credential from temp config"
grep -Fq '[profiles.keep]' "$_legacy_capture" 2>/dev/null \
    || fail "legacy env-key strip must retain unrelated profiles in temp config"
if grep -Fr 'sk-larch-legacy-strip-sentinel' "$SCRATCH/t-legacy-strip" 2>/dev/null; then
    fail "legacy env-key strip must not leak sentinel into case TMPDIR"
fi
if find "$SCRATCH/t-legacy-strip-home" -type f ! -path "$_legacy_fixture" \
    -exec grep -Fl 'sk-larch-legacy-strip-sentinel' {} + 2>/dev/null | grep -q .; then
    fail "legacy env-key strip must not leak sentinel into isolated HOME outside fixture"
fi
if cmp -s "$_legacy_fixture_copy" "$_legacy_fixture"; then
    :
else
    fail "legacy env-key strip must leave fixture HOME config unchanged"
fi

# --- Stamp decoy: fresh env-key stamp must not satisfy login-mode probe ---
mkdir -p "$SCRATCH/t-stamp-login-decoy-home/.codex"
printf '{"token":"login-decoy"}\n' > "$SCRATCH/t-stamp-login-decoy-home/.codex/auth.json"
printf 'model = "ok"\n' > "$SCRATCH/t-stamp-login-decoy-home/.codex/config.toml"
SB_DECOY="$SCRATCH/bin-stamp-login-decoy"
mkdir -p "$SB_DECOY"
cat > "$SB_DECOY/codex" <<'STUB'
#!/usr/bin/env bash
printf '%s\n' "$@" >"${LARCH_TEST_CODEX_ARGV_LOG:?}"
exit 0
STUB
chmod +x "$SB_DECOY/codex"
cat > "$SB_DECOY/cursor" <<'STUB'
#!/usr/bin/env bash
exit 127
STUB
chmod +x "$SB_DECOY/cursor"
mkdir -p "$SCRATCH/t-stamp-login-decoy"
_decoy_stamp="$SCRATCH/t-stamp-login-decoy/larch-codex-env-key-present-${STAMP_USER}.stamp"
printf 'true\n' >"$_decoy_stamp"
touch "$_decoy_stamp"
_decoy_argv="$SCRATCH/t-stamp-login-decoy/codex-argv.log"
out=$(run_cr "$SCRATCH/t-stamp-login-decoy" env PATH="$SB_DECOY:/usr/bin:/bin" \
    HOME="$SCRATCH/t-stamp-login-decoy-home" LARCH_PROBE_TTL_SECONDS=3600 \
    LARCH_TEST_CODEX_ARGV_LOG="$_decoy_argv" \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux LARCH_EXTERNAL_AUTH_RETRIES=1 "$CR")
assert_line "stamp login decoy probe ok" "CODEX_PRESENT=true" "$out"
grep -Fq 'model_providers.openai-larch-env.env_key="OPENAI_API_KEY"' "$_decoy_argv" 2>/dev/null \
    && fail "stamp login decoy must not emit env-key argv overrides"
grep -Fq 'model_provider="openai-larch-env"' "$_decoy_argv" 2>/dev/null \
    && fail "stamp login decoy must not emit env-key model_provider override"
if [[ -f "$SCRATCH/t-stamp-login-decoy/larch-codex-login-present-${STAMP_USER}.stamp" ]] \
   && [[ "$(cat "$SCRATCH/t-stamp-login-decoy/larch-codex-login-present-${STAMP_USER}.stamp" 2>/dev/null)" == "true" ]] \
   && [[ -f "$_decoy_stamp" ]] \
   && [[ "$(cat "$_decoy_stamp" 2>/dev/null)" == "true" ]]; then
    :
else
    fail "stamp login decoy should write login stamp true and leave env-key decoy unchanged"
fi
assert_no_probe_homes "stamp login decoy cleanup" "$SCRATCH/t-stamp-login-decoy"

# --- Cursor Option B: preflight miss gets one live fallback ---
SB_OPTB_SUCCESS="$SCRATCH/bin-optb-success"
mkdir -p "$SB_OPTB_SUCCESS" "$SCRATCH/t-optb-limited-success-home"
cat > "$SB_OPTB_SUCCESS/cursor" <<'STUB'
#!/usr/bin/env bash
n=$(cat "${LARCH_TEST_CURSOR_COUNT:?}" 2>/dev/null || echo 0)
echo "$((n + 1))" >"${LARCH_TEST_CURSOR_COUNT:?}"
exit 0
STUB
chmod +x "$SB_OPTB_SUCCESS/cursor"
out=$(run_cr "$SCRATCH/t-optb-limited-success" env PATH="$SB_OPTB_SUCCESS:/usr/bin:/bin" \
    HOME="$SCRATCH/t-optb-limited-success-home" CURSOR_API_KEY= \
    LARCH_TEST_CURSOR_COUNT="$SCRATCH/t-optb-limited-success/cursor-count" \
    LARCH_PROBE_TTL_SECONDS=0 LARCH_EXTERNAL_AUTH_RETRIES=5 \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Darwin \
    LIB_CURSOR_AUTH_TEST_SECURITY_RC_SEQ=1,1,1 "$CR")
assert_line "optb limited success" "CURSOR_PRESENT=true" "$out"
if [[ "$(cat "$SCRATCH/t-optb-limited-success/cursor-count" 2>/dev/null || echo 0)" == "1" ]]; then
    :
else
    fail "optb limited success should run exactly one live Cursor probe"
fi

SB_OPTB_NEG="$SCRATCH/bin-optb-negative"
mkdir -p "$SB_OPTB_NEG" "$SCRATCH/t-optb-limited-negative-home"
cat > "$SB_OPTB_NEG/cursor" <<'STUB'
#!/usr/bin/env bash
printf 'RAW_CURSOR_PROBE_STDERR_MARKER_SECURITY_CODE\n' >&2
exit 1
STUB
chmod +x "$SB_OPTB_NEG/cursor"
_optb_neg_err="$SCRATCH/t-optb-limited-negative.stderr"
out=$(run_cr "$SCRATCH/t-optb-limited-negative" env PATH="$SB_OPTB_NEG:/usr/bin:/bin" \
    HOME="$SCRATCH/t-optb-limited-negative-home" CURSOR_API_KEY= \
    LARCH_PROBE_TTL_SECONDS=0 LARCH_EXTERNAL_AUTH_RETRIES=5 \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Darwin \
    LIB_CURSOR_AUTH_TEST_SECURITY_RC_SEQ=1,1,1 "$CR" 2>"$_optb_neg_err")
assert_line "optb limited negative" "CURSOR_PRESENT=false" "$out"
grep -Fq 'RAW_CURSOR_PROBE_STDERR_MARKER_SECURITY_CODE' "$_optb_neg_err" 2>/dev/null \
    && fail "optb limited negative must not leak raw Cursor probe stderr"

SB_OPTB_AUTH="$SCRATCH/bin-optb-auth"
mkdir -p "$SB_OPTB_AUTH" "$SCRATCH/t-optb-no-full-loop-home"
cat > "$SB_OPTB_AUTH/cursor" <<'STUB'
#!/usr/bin/env bash
n=$(cat "${LARCH_TEST_CURSOR_COUNT:?}" 2>/dev/null || echo 0)
echo "$((n + 1))" >"${LARCH_TEST_CURSOR_COUNT:?}"
printf 'authentication failed\n' >&2
exit 1
STUB
chmod +x "$SB_OPTB_AUTH/cursor"
out=$(run_cr "$SCRATCH/t-optb-no-full-loop" env PATH="$SB_OPTB_AUTH:/usr/bin:/bin" \
    HOME="$SCRATCH/t-optb-no-full-loop-home" CURSOR_API_KEY= \
    LARCH_TEST_CURSOR_COUNT="$SCRATCH/t-optb-no-full-loop/cursor-count" \
    LARCH_PROBE_TTL_SECONDS=0 LARCH_EXTERNAL_AUTH_RETRIES=5 \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Darwin \
    LIB_CURSOR_AUTH_TEST_SECURITY_RC_SEQ=1,1,1 "$CR")
assert_line "optb no full loop terminal false" "CURSOR_PRESENT=false" "$out"
if [[ "$(cat "$SCRATCH/t-optb-no-full-loop/cursor-count" 2>/dev/null || echo 0)" == "1" ]]; then
    :
else
    fail "optb no full loop should run exactly one auth-classified Cursor probe"
fi

SB_OPTB_SETUP="$SCRATCH/bin-optb-setup"
mkdir -p "$SB_OPTB_SETUP" "$SCRATCH/t-optb-setup-chain-home"
cat > "$SB_OPTB_SETUP/cursor" <<'STUB'
#!/usr/bin/env bash
n=$(cat "${LARCH_TEST_CURSOR_COUNT:?}" 2>/dev/null || echo 0)
echo "$((n + 1))" >"${LARCH_TEST_CURSOR_COUNT:?}"
exit 0
STUB
chmod +x "$SB_OPTB_SETUP/cursor"
_optb_setup_log="$SCRATCH/t-optb-setup-chain/setup.log"
out=$(run_cr "$SCRATCH/t-optb-setup-chain" env PATH="$SB_OPTB_SETUP:/usr/bin:/bin" \
    HOME="$SCRATCH/t-optb-setup-chain-home" CURSOR_API_KEY= \
    LARCH_TEST_CURSOR_COUNT="$SCRATCH/t-optb-setup-chain/cursor-count" \
    LARCH_CHECK_REVIEWERS_TEST_MODE=1 LARCH_CHECK_REVIEWERS_TEST_SETUP_LOG="$_optb_setup_log" \
    LARCH_PROBE_TTL_SECONDS=0 LARCH_EXTERNAL_AUTH_RETRIES=5 \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Darwin \
    LIB_CURSOR_AUTH_TEST_SECURITY_RC_SEQ=1,1,1 "$CR")
assert_line "optb setup-chain success" "CURSOR_PRESENT=true" "$out"
for _step in cursor_preread_service_token cursor_auth_export_env cursor_launcher_setup_private_config_dir cursor_launcher_cleanup_private_config_dir; do
    grep -Fxq "$_step" "$_optb_setup_log" 2>/dev/null || fail "optb setup-chain missing $_step"
done

SB_OPTB_SETUP_FAIL="$SCRATCH/bin-optb-setup-fail"
mkdir -p "$SB_OPTB_SETUP_FAIL" "$SCRATCH/t-optb-setup-chain-fail-home"
cat > "$SB_OPTB_SETUP_FAIL/cursor" <<'STUB'
#!/usr/bin/env bash
printf 'probe should be skipped when setup fails\n' >"${LARCH_TEST_CURSOR_COUNT:?}"
exit 0
STUB
chmod +x "$SB_OPTB_SETUP_FAIL/cursor"
_optb_setup_fail_log="$SCRATCH/t-optb-setup-chain-fail/setup.log"
out=$(run_cr "$SCRATCH/t-optb-setup-chain-fail" env PATH="$SB_OPTB_SETUP_FAIL:/usr/bin:/bin" \
    HOME="$SCRATCH/t-optb-setup-chain-fail-home" CURSOR_API_KEY= \
    LARCH_TEST_CURSOR_COUNT="$SCRATCH/t-optb-setup-chain-fail/cursor-count" \
    LARCH_CHECK_REVIEWERS_TEST_MODE=1 LARCH_CHECK_REVIEWERS_TEST_SETUP_LOG="$_optb_setup_fail_log" \
    LARCH_CHECK_REVIEWERS_TEST_FAIL_SETUP_STEP=cursor_launcher_setup_private_config_dir \
    LARCH_PROBE_TTL_SECONDS=0 LARCH_EXTERNAL_AUTH_RETRIES=5 \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Darwin \
    LIB_CURSOR_AUTH_TEST_SECURITY_RC_SEQ=1,1,1 "$CR")
assert_line "optb setup-chain fail" "CURSOR_PRESENT=false" "$out"
if [[ -f "$SCRATCH/t-optb-setup-chain-fail/cursor-count" ]]; then
    fail "optb setup-chain failure should skip the one-shot Cursor probe"
fi
grep -Fxq 'cursor_launcher_setup_private_config_dir' "$_optb_setup_fail_log" 2>/dev/null \
    || fail "optb setup-chain failure should reach private config setup"

# --- Option C: false stamps are uncached by default and bounded when requested ---
SB_OPTC_CURSOR="$SCRATCH/bin-optc-cursor"
mkdir -p "$SB_OPTC_CURSOR" "$SCRATCH/t-optc-cursor" "$SCRATCH/t-optc-cursor-home"
cat > "$SB_OPTC_CURSOR/cursor" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB
chmod +x "$SB_OPTC_CURSOR/cursor"
printf 'false\n' >"$SCRATCH/t-optc-cursor/larch-cursor-present-${STAMP_USER}.stamp"
touch "$SCRATCH/t-optc-cursor/larch-cursor-present-${STAMP_USER}.stamp"
out=$(run_cr "$SCRATCH/t-optc-cursor" env PATH="$SB_OPTC_CURSOR:/usr/bin:/bin" \
    HOME="$SCRATCH/t-optc-cursor-home" CURSOR_API_KEY= \
    LARCH_PROBE_TTL_SECONDS=3600 LARCH_PROBE_NEGATIVE_TTL_SECONDS=0 LARCH_EXTERNAL_AUTH_RETRIES=5 \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Darwin \
    LIB_CURSOR_AUTH_TEST_SECURITY_RC_SEQ=1,1,1 "$CR")
assert_line "optc cursor false stamp ignored" "CURSOR_PRESENT=true" "$out"

SB_OPTC_CURSOR_CACHED="$SCRATCH/bin-optc-cursor-cached"
mkdir -p "$SB_OPTC_CURSOR_CACHED" "$SCRATCH/t-optc-cursor-cached" "$SCRATCH/t-optc-cursor-cached-home"
cat > "$SB_OPTC_CURSOR_CACHED/cursor" <<'STUB'
#!/usr/bin/env bash
printf 'cursor cached false should not invoke probe\n' >"${LARCH_TEST_CURSOR_COUNT:?}"
exit 0
STUB
chmod +x "$SB_OPTC_CURSOR_CACHED/cursor"
printf 'false\n' >"$SCRATCH/t-optc-cursor-cached/larch-cursor-present-${STAMP_USER}.stamp"
touch "$SCRATCH/t-optc-cursor-cached/larch-cursor-present-${STAMP_USER}.stamp"
out=$(run_cr "$SCRATCH/t-optc-cursor-cached" env PATH="$SB_OPTC_CURSOR_CACHED:/usr/bin:/bin" \
    HOME="$SCRATCH/t-optc-cursor-cached-home" CURSOR_API_KEY= \
    LARCH_TEST_CURSOR_COUNT="$SCRATCH/t-optc-cursor-cached/cursor-count" \
    LARCH_PROBE_TTL_SECONDS=3600 LARCH_PROBE_NEGATIVE_TTL_SECONDS=3600 LARCH_EXTERNAL_AUTH_RETRIES=5 \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Darwin \
    LIB_CURSOR_AUTH_TEST_SECURITY_RC_SEQ=1,1,1 "$CR")
assert_line "optc cursor cached false" "CURSOR_PRESENT=false" "$out"
if [[ -f "$SCRATCH/t-optc-cursor-cached/cursor-count" ]]; then
    fail "optc cursor cached false should not invoke live Cursor probe"
fi

SB_OPTC_CODEX="$SCRATCH/bin-optc-codex"
mkdir -p "$SB_OPTC_CODEX" "$SCRATCH/t-optc-codex-login"
cat > "$SB_OPTC_CODEX/codex" <<'STUB'
#!/usr/bin/env bash
printf 'codex invoked\n' >>"${LARCH_TEST_CODEX_COUNT:?}"
exit 0
STUB
chmod +x "$SB_OPTC_CODEX/codex"
printf 'false\n' >"$SCRATCH/t-optc-codex-login/larch-codex-login-present-${STAMP_USER}.stamp"
touch "$SCRATCH/t-optc-codex-login/larch-codex-login-present-${STAMP_USER}.stamp"
out=$(run_cr "$SCRATCH/t-optc-codex-login" env PATH="$SB_OPTC_CODEX:/usr/bin:/bin" \
    LARCH_TEST_CODEX_COUNT="$SCRATCH/t-optc-codex-login/codex-count" \
    LARCH_PROBE_TTL_SECONDS=3600 LARCH_PROBE_NEGATIVE_TTL_SECONDS=0 \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux LARCH_EXTERNAL_AUTH_RETRIES=3 "$CR")
assert_line "optc codex login false stamp ignored" "CODEX_PRESENT=true" "$out"
if [[ -s "$SCRATCH/t-optc-codex-login/codex-count" ]] \
   && [[ ! -f "$SCRATCH/t-optc-codex-login/larch-codex-env-key-present-${STAMP_USER}.stamp" ]]; then
    :
else
    fail "optc codex login should seed/read login stamp path and avoid env-key stamp path"
fi

SB_OPTC_CODEX_CACHED="$SCRATCH/bin-optc-codex-cached"
mkdir -p "$SB_OPTC_CODEX_CACHED" "$SCRATCH/t-optc-codex-login-cached"
cat > "$SB_OPTC_CODEX_CACHED/codex" <<'STUB'
#!/usr/bin/env bash
printf 'codex cached false should not invoke probe\n' >"${LARCH_TEST_CODEX_COUNT:?}"
exit 0
STUB
chmod +x "$SB_OPTC_CODEX_CACHED/codex"
printf 'false\n' >"$SCRATCH/t-optc-codex-login-cached/larch-codex-login-present-${STAMP_USER}.stamp"
touch "$SCRATCH/t-optc-codex-login-cached/larch-codex-login-present-${STAMP_USER}.stamp"
out=$(run_cr "$SCRATCH/t-optc-codex-login-cached" env PATH="$SB_OPTC_CODEX_CACHED:/usr/bin:/bin" \
    LARCH_TEST_CODEX_COUNT="$SCRATCH/t-optc-codex-login-cached/codex-count" \
    LARCH_PROBE_TTL_SECONDS=3600 LARCH_PROBE_NEGATIVE_TTL_SECONDS=3600 \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux LARCH_EXTERNAL_AUTH_RETRIES=3 "$CR")
assert_line "optc codex login cached false" "CODEX_PRESENT=false" "$out"
if [[ -f "$SCRATCH/t-optc-codex-login-cached/codex-count" ]]; then
    fail "optc codex login cached false should not invoke live Codex probe"
fi

SB_OPTC_CODEX_ENV_CACHED="$SCRATCH/bin-optc-codex-env-cached"
mkdir -p "$SB_OPTC_CODEX_ENV_CACHED" "$SCRATCH/t-optc-codex-env-key-cached"
cat > "$SB_OPTC_CODEX_ENV_CACHED/codex" <<'STUB'
#!/usr/bin/env bash
printf 'codex env-key cached false should not invoke probe\n' >"${LARCH_TEST_CODEX_COUNT:?}"
exit 0
STUB
chmod +x "$SB_OPTC_CODEX_ENV_CACHED/codex"
printf 'false\n' >"$SCRATCH/t-optc-codex-env-key-cached/larch-codex-env-key-present-${STAMP_USER}.stamp"
touch "$SCRATCH/t-optc-codex-env-key-cached/larch-codex-env-key-present-${STAMP_USER}.stamp"
out=$(run_cr_with_env "$SCRATCH/t-optc-codex-env-key-cached" env PATH="$SB_OPTC_CODEX_ENV_CACHED:/usr/bin:/bin" \
    OPENAI_API_KEY=sk-larch-probe-sentinel \
    LARCH_TEST_CODEX_COUNT="$SCRATCH/t-optc-codex-env-key-cached/codex-count" \
    LARCH_PROBE_TTL_SECONDS=3600 LARCH_PROBE_NEGATIVE_TTL_SECONDS=3600 \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux LARCH_EXTERNAL_AUTH_RETRIES=3 "$CR")
assert_line "optc codex env-key cached false" "CODEX_PRESENT=false" "$out"
if [[ -f "$SCRATCH/t-optc-codex-env-key-cached/codex-count" ]]; then
    fail "optc codex env-key cached false should not invoke live Codex probe"
fi
if grep -Fr 'sk-larch-probe-sentinel' "$SCRATCH/t-optc-codex-env-key-cached" 2>/dev/null; then
    fail "optc codex env-key cached false must not leak OPENAI_API_KEY sentinel into TMPDIR"
fi

set +e
(cd "$REPO_ROOT" && TMPDIR="$SCRATCH/probe-arg-tmp" LARCH_QUIET_DISABLE=1 "$CR" --probe >/dev/null 2>"$SCRATCH/unknown.stderr")
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
