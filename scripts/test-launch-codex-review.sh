#!/usr/bin/env bash
# Offline regression harness for scripts/launch-codex-review.sh.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
LAUNCHER="$REPO_ROOT/scripts/launch-codex-review.sh"
TMPDIR="$(mktemp -d /tmp/larch-test-launch-codex-review-XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

export RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05

PASS=0
FAIL=0
FAILURES=()
pass() { PASS=$((PASS + 1)); }
fail() { FAIL=$((FAIL + 1)); FAILURES+=("$1"); }

assert_eq() {
    local label="$1"
    local expected="$2"
    local actual="$3"
    if [[ "$actual" == "$expected" ]]; then pass; else fail "$label: expected '$expected', got '$actual'"; fi
}

assert_grep() {
    local label="$1"
    local pattern="$2"
    local file="$3"
    if grep -Fq -- "$pattern" "$file"; then pass; else fail "$label: missing '$pattern' in $file"; fi
}

set +e
"$LAUNCHER" >/dev/null 2>"$TMPDIR/missing.stderr"
RC=$?
set -e
assert_eq "missing flags exit" "2" "$RC"
assert_grep "missing output message" "--output is required" "$TMPDIR/missing.stderr"

for bad_timeout in nope 0 00 000; do
    OUT="$TMPDIR/bad-${bad_timeout}.txt"
    set +e
    "$LAUNCHER" --output "$OUT" --timeout "$bad_timeout" --prompt "x" >/dev/null 2>"$TMPDIR/bad-${bad_timeout}.stderr"
    RC=$?
    set -e
    assert_eq "bad timeout $bad_timeout exit" "2" "$RC"
    assert_grep "bad timeout $bad_timeout message" "must be a positive integer" "$TMPDIR/bad-${bad_timeout}.stderr"
done

STUB_BIN="$TMPDIR/bin"
mkdir -p "$STUB_BIN"
cat > "$STUB_BIN/codex" <<'STUB_CODEX'
#!/usr/bin/env bash
set -euo pipefail
: "${CODEX_STUB_ARGV_LOG:?}"
: "${CODEX_STUB_COUNT_FILE:?}"
count=0
if [[ -f "$CODEX_STUB_COUNT_FILE" ]]; then
    count=$(cat "$CODEX_STUB_COUNT_FILE")
fi
count=$((count + 1))
printf '%s\n' "$count" > "$CODEX_STUB_COUNT_FILE"
output=""
last=""
for arg in "$@"; do
    printf '%s\n' "$arg" >> "$CODEX_STUB_ARGV_LOG"
    if [[ "$last" == "--output-last-message" ]]; then
        output="$arg"
    fi
    last="$arg"
done
[[ -n "$output" ]] || exit 9
printf 'codex review ok\n' > "$output"
printf 'tokens used\n1\n'
STUB_CODEX
chmod +x "$STUB_BIN/codex"

OUTDIR_REAL="$TMPDIR/out-real"
mkdir -p "$OUTDIR_REAL"
OUTDIR_LINK="$TMPDIR/out-link"
ln -s "$OUTDIR_REAL" "$OUTDIR_LINK"
OUTPUT="$OUTDIR_LINK/../out-link/review.txt"
ARGV="$TMPDIR/argv.txt"
COUNT="$TMPDIR/count.txt"
PATH="$STUB_BIN:$PATH" \
    CODEX_STUB_ARGV_LOG="$ARGV" \
    CODEX_STUB_COUNT_FILE="$COUNT" \
    LARCH_CODEX_MODEL="stub-model" \
    "$LAUNCHER" --output "$OUTPUT" --timeout 5 --prompt "review prompt" >/dev/null

assert_eq "stub invoked once" "1" "$(cat "$COUNT")"
assert_eq "argv 1" "exec" "$(sed -n '1p' "$ARGV")"
assert_eq "argv 2" "--full-auto" "$(sed -n '2p' "$ARGV")"
assert_eq "argv 3" "-C" "$(sed -n '3p' "$ARGV")"
assert_eq "argv 4" "$REPO_ROOT" "$(sed -n '4p' "$ARGV")"
assert_eq "argv 5 add-dir flag" "--add-dir" "$(sed -n '5p' "$ARGV")"
assert_eq "argv 6 canonical output dir" "$(cd "$OUTDIR_REAL" && pwd -P)" "$(sed -n '6p' "$ARGV")"

if [[ "$(grep -Fxc -- '-m' "$ARGV")" == "1" ]] && grep -Fxq -- 'stub-model' "$ARGV"; then
    pass
else
    fail "model args should include one -m and literal stub-model"
fi

ARGV_INJECT="$TMPDIR/argv-inject.txt"
COUNT_INJECT="$TMPDIR/count-inject.txt"
PATH="$STUB_BIN:$PATH" \
    CODEX_STUB_ARGV_LOG="$ARGV_INJECT" \
    CODEX_STUB_COUNT_FILE="$COUNT_INJECT" \
    LARCH_CODEX_MODEL="evil --model gpt-injection" \
    "$LAUNCHER" --output "$TMPDIR/inject.txt" --timeout 5 --prompt "review prompt" >/dev/null
if [[ "$(grep -Fxc -- '-m' "$ARGV_INJECT")" == "1" ]] && grep -Fxq -- 'evil --model gpt-injection' "$ARGV_INJECT"; then
    pass
else
    fail "model with spaces should remain one argv token after -m"
fi

set +e
PATH="$STUB_BIN:$PATH" \
    CODEX_STUB_ARGV_LOG="$TMPDIR/argv-bad.txt" \
    CODEX_STUB_COUNT_FILE="$TMPDIR/count-bad.txt" \
    LARCH_CODEX_MODEL=$'evil\nextra' \
    "$LAUNCHER" --output "$TMPDIR/bad-model.txt" --timeout 5 --prompt "review prompt" >/dev/null 2>"$TMPDIR/bad-model.stderr"
RC=$?
set -e
if [[ "$RC" -ne 0 ]] && [[ ! -e "$TMPDIR/count-bad.txt" ]] && [[ ! -e "$TMPDIR/bad-model.txt.done" ]]; then
    pass
else
    fail "newline model should fail before invoking codex or producing .done (rc=$RC count=$(cat "$TMPDIR/count-bad.txt" 2>/dev/null))"
fi
assert_grep "newline model diagnostic" "[[:cntrl:]]" "$TMPDIR/bad-model.stderr"

if (( FAIL > 0 )); then
    printf 'FAIL: test-launch-codex-review.sh - %s failed, %s passed\n' "$FAIL" "$PASS" >&2
    printf '  %s\n' "${FAILURES[@]}" >&2
    exit 1
fi

printf 'PASS: test-launch-codex-review.sh - %s assertions passed\n' "$PASS"
