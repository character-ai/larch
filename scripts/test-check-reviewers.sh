#!/usr/bin/env bash
# Regression test for check-reviewers.sh presence detection.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
TMPDIR=$(mktemp -d /tmp/larch-test-check-reviewers-XXXXXX)
trap 'rm -rf "$TMPDIR"' EXIT
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

STUB_BIN="$TMPDIR/bin"
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

out=$(PATH="$STUB_BIN:/usr/bin:/bin" "$REPO_ROOT/scripts/check-reviewers.sh")
assert_line "codex present" "CODEX_PRESENT=true" "$out"
assert_line "cursor present" "CURSOR_PRESENT=true" "$out"
assert_line "codex available alias" "CODEX_AVAILABLE=true" "$out"
assert_line "cursor available alias" "CURSOR_AVAILABLE=true" "$out"

out=$(PATH="/usr/bin:/bin" "$REPO_ROOT/scripts/check-reviewers.sh")
assert_line "codex absent" "CODEX_PRESENT=false" "$out"
assert_line "cursor absent" "CURSOR_PRESENT=false" "$out"
assert_line "codex absent alias" "CODEX_AVAILABLE=false" "$out"
assert_line "cursor absent alias" "CURSOR_AVAILABLE=false" "$out"

out=$(PATH="$STUB_BIN:/usr/bin:/bin" "$REPO_ROOT/scripts/check-reviewers.sh" --skip-codex-probe)
assert_line "skip codex" "CODEX_PRESENT=false" "$out"
assert_line "skip codex cursor still present" "CURSOR_PRESENT=true" "$out"

out=$(PATH="$STUB_BIN:/usr/bin:/bin" "$REPO_ROOT/scripts/check-reviewers.sh" --skip-cursor-probe)
assert_line "skip cursor codex still present" "CODEX_PRESENT=true" "$out"
assert_line "skip cursor" "CURSOR_PRESENT=false" "$out"

set +e
"$REPO_ROOT/scripts/check-reviewers.sh" --probe >/dev/null 2>"$TMPDIR/unknown.stderr"
rc=$?
set -e
if [[ "$rc" -eq 0 ]] || ! grep -Fq "unknown argument: --probe" "$TMPDIR/unknown.stderr"; then
    fail "--probe should be rejected under the presence-only contract"
fi

if [[ "$FAIL" -eq 1 ]]; then
    echo "FAIL: test-check-reviewers.sh" >&2
    exit 1
fi

echo "PASS: test-check-reviewers.sh"
