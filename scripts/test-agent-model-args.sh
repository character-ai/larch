#!/usr/bin/env bash
# Regression harness for scripts/agent-model-args.sh line-token argv output.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SUBJECT="$REPO_ROOT/scripts/agent-model-args.sh"

# Fail fast if ripgrep is missing — the static migration guards below scan
# the repo for unsafe MODEL_ARGS / `[@]` / runtime mapfile patterns and rely
# on `rg`. Without this gate, `rg ... || true` inside `$(...)` would yield
# empty hits whenever rg is absent and the harness would silently PASS those
# guards. Documented prerequisite in test-agent-model-args.md.
if ! command -v rg >/dev/null 2>&1; then
    echo "test-agent-model-args.sh: required tool 'rg' (ripgrep) not found on PATH" >&2
    echo "test-agent-model-args.sh: install ripgrep (e.g., 'brew install ripgrep' / 'apt install ripgrep') and re-run" >&2
    exit 2
fi

PASS=0
FAIL=0
FAILURES=()

pass() { PASS=$((PASS + 1)); }
fail() { FAIL=$((FAIL + 1)); FAILURES+=("$1"); }

assert_file_equals() {
    local label="$1"
    local expected="$2"
    local actual="$3"
    if cmp -s "$expected" "$actual"; then
        pass
    else
        fail "$label: expected $(tr '\n' '|' < "$expected"), got $(tr '\n' '|' < "$actual")"
    fi
}

assert_success_no_empty_lines() {
    local label="$1"
    local output="$2"
    if grep -q '^$' "$output"; then
        fail "$label: stdout contains an empty line"
    else
        pass
    fi
}

TMPDIR="$(mktemp -d /tmp/larch-test-agent-model-args-XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

OUT="$TMPDIR/out.txt"
ERR="$TMPDIR/err.txt"
EXPECTED="$TMPDIR/expected.txt"

env -u LARCH_CODEX_MODEL -u CLAUDE_PLUGIN_OPTION_CODEX_MODEL -u LARCH_CODEX_EFFORT -u CLAUDE_PLUGIN_OPTION_CODEX_EFFORT \
    "$SUBJECT" --tool codex --with-effort > "$OUT" 2> "$ERR"
printf '%s\n%s\n%s\n%s\n' '-m' 'gpt-5.5' '-c' 'model_reasoning_effort="high"' > "$EXPECTED"
assert_file_equals "codex default with effort" "$EXPECTED" "$OUT"
assert_success_no_empty_lines "codex default with effort" "$OUT"

env -u LARCH_CURSOR_MODEL -u CLAUDE_PLUGIN_OPTION_CURSOR_MODEL \
    "$SUBJECT" --tool cursor --with-effort > "$OUT" 2> "$ERR"
printf '%s\n%s\n' '--model' 'composer-2' > "$EXPECTED"
assert_file_equals "cursor default" "$EXPECTED" "$OUT"
assert_success_no_empty_lines "cursor default" "$OUT"

LARCH_CODEX_MODEL="model-with-dashes" "$SUBJECT" --tool codex > "$OUT" 2> "$ERR"
printf '%s\n%s\n' '-m' 'model-with-dashes' > "$EXPECTED"
assert_file_equals "ordinary punctuation preserved" "$EXPECTED" "$OUT"

set +e
LARCH_CODEX_MODEL=$'evil\nextra' "$SUBJECT" --tool codex > "$OUT" 2> "$ERR"
RC=$?
set -e
if [[ "$RC" -ne 0 ]] && grep -Fq '[[:cntrl:]]' "$ERR"; then pass; else fail "codex newline should reject with control-class diagnostic"; fi

set +e
LARCH_CURSOR_MODEL=$'evil\textra' "$SUBJECT" --tool cursor > "$OUT" 2> "$ERR"
RC=$?
set -e
if [[ "$RC" -ne 0 ]] && grep -Fq '[[:cntrl:]]' "$ERR"; then pass; else fail "cursor tab should reject with control-class diagnostic"; fi


set +e
LARCH_CODEX_MODEL="" "$SUBJECT" --tool codex > "$OUT" 2> "$ERR"
RC=$?
set -e
if [[ "$RC" -ne 0 ]] && grep -Fq 'blank or whitespace-only' "$ERR"; then pass; else fail "empty codex model should reject"; fi

set +e
LARCH_CURSOR_MODEL="   " "$SUBJECT" --tool cursor > "$OUT" 2> "$ERR"
RC=$?
set -e
if [[ "$RC" -ne 0 ]] && grep -Fq 'blank or whitespace-only' "$ERR"; then pass; else fail "whitespace cursor model should reject"; fi

LARCH_CODEX_EFFORT=bogus "$SUBJECT" --tool codex --with-effort > "$OUT" 2> "$ERR"
printf '%s\n%s\n%s\n%s\n' '-m' 'gpt-5.5' '-c' 'model_reasoning_effort="high"' > "$EXPECTED"
assert_file_equals "invalid effort stdout stays machine-only" "$EXPECTED" "$OUT"
if grep -Fq 'WARN invalid codex effort' "$ERR"; then pass; else fail "invalid effort warning should be on stderr"; fi

# Migration guard: no unquoted scalar MODEL_ARGS expansion should remain in
# shell runtime. This intentionally allows guarded array expansion forms.
UNQUOTED_MODEL_ARGS=$(rg -n '\$(MODEL_ARGS|CODEX_MODEL_ARGS|CURSOR_MODEL_ARGS)([^A-Za-z_]|$)|\$\{(MODEL_ARGS|CODEX_MODEL_ARGS|CURSOR_MODEL_ARGS)\}' scripts skills --glob '*.sh' --glob '!scripts/test-agent-model-args.sh' || true)
if [[ -z "$UNQUOTED_MODEL_ARGS" ]]; then
    pass
else
    fail "unquoted MODEL_ARGS expansion remains: $UNQUOTED_MODEL_ARGS"
fi

PLAIN_ARRAY_EXPANSION=$(rg -n '"\$\{(MODEL_ARGS|CODEX_MODEL_ARGS|CURSOR_MODEL_ARGS)\[@\]\}"' scripts skills --glob '*.sh' --glob '!scripts/test-agent-model-args.sh' | grep -v '\[@\]+"' || true)
if [[ -z "$PLAIN_ARRAY_EXPANSION" ]]; then
    pass
else
    fail "MODEL_ARGS array expansion missing [@]+ guard: $PLAIN_ARRAY_EXPANSION"
fi

MAPFILE_HITS=$(rg -n '\b(mapfile|readarray)\b' scripts skills --glob '*.sh' --glob '!scripts/test-*' --glob '!skills/**/test-*.sh' | grep -v '^[^:]*:[0-9]\+:[[:space:]]*#' || true) # lint-bash32: ok intentional static portability pattern
if [[ -z "$MAPFILE_HITS" ]]; then
    pass
else
    fail "Bash-4-only mapfile/readarray usage remains in runtime shell: $MAPFILE_HITS"
fi

if (( FAIL > 0 )); then
    printf 'FAIL: test-agent-model-args.sh - %s failed, %s passed\n' "$FAIL" "$PASS" >&2
    printf '  %s\n' "${FAILURES[@]}" >&2
    exit 1
fi

printf 'PASS: test-agent-model-args.sh - %s assertions passed\n' "$PASS"
