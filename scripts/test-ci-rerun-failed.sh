#!/usr/bin/env bash
# test-ci-rerun-failed.sh — regression harness for ci-rerun-failed.sh.
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SCRIPT="$REPO_ROOT/scripts/ci-rerun-failed.sh"

[ -x "$SCRIPT" ] || { echo "FAIL: $SCRIPT not executable"; exit 1; }

PASS=0
FAIL=0
SANDBOX=$(mktemp -d "${TMPDIR:-/tmp}/larch-ci-rerun-failed-test.XXXXXX")
trap 'rm -rf "$SANDBOX"' EXIT

assert_contains() {
    local needle=$1 haystack=$2 label=$3
    if printf '%s' "$haystack" | grep -qF -- "$needle"; then
        PASS=$((PASS + 1))
        echo "PASS: $label"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: $label"
        echo "  expected to contain: $needle"
        printf '%s\n' "$haystack" | sed 's/^/    /'
    fi
}

assert_not_contains() {
    local needle=$1 haystack=$2 label=$3
    if ! printf '%s' "$haystack" | grep -qF -- "$needle"; then
        PASS=$((PASS + 1))
        echo "PASS: $label"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: $label"
        echo "  expected NOT to contain: $needle"
        printf '%s\n' "$haystack" | sed 's/^/    /'
    fi
}

stub_dir="$SANDBOX/bin"
mkdir -p "$stub_dir"

# Case 1: gh run rerun exits 0 → RERUN_SUBMITTED=true, ERROR=
cat > "$stub_dir/gh" << 'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$stub_dir/gh"
out=$(PATH="$stub_dir:$PATH" "$SCRIPT" --run-id 12345 --repo org/repo 2>&1)
assert_contains 'RERUN_SUBMITTED=true' "$out" "success: RERUN_SUBMITTED=true"
assert_contains 'ERROR=' "$out" "success: ERROR= present"
assert_not_contains 'RERUN_SUBMITTED=false' "$out" "success: not false"

# Case 2: gh run rerun exits 1 with a generic error → RERUN_SUBMITTED=false
cat > "$stub_dir/gh" << 'EOF'
#!/usr/bin/env bash
echo "some generic failure" >&2
exit 1
EOF
chmod +x "$stub_dir/gh"
out=$(PATH="$stub_dir:$PATH" "$SCRIPT" --run-id 12345 --repo org/repo 2>&1)
assert_contains 'RERUN_SUBMITTED=false' "$out" "generic-failure: RERUN_SUBMITTED=false"
assert_contains 'ERROR=gh run rerun failed' "$out" "generic-failure: ERROR prefix"

# Case 3: gh run rerun exits 1 with "already running" → RERUN_SUBMITTED=true
cat > "$stub_dir/gh" << 'EOF'
#!/usr/bin/env bash
echo "run 99999 cannot be rerun; This workflow is already running" >&2
exit 1
EOF
chmod +x "$stub_dir/gh"
out=$(PATH="$stub_dir:$PATH" "$SCRIPT" --run-id 99999 --repo org/repo 2>&1)
assert_contains 'RERUN_SUBMITTED=true' "$out" "already-running: RERUN_SUBMITTED=true"
assert_not_contains 'RERUN_SUBMITTED=false' "$out" "already-running: not false"
# ERROR must be empty
error_line=$(printf '%s\n' "$out" | grep '^ERROR=')
if [ "$error_line" = "ERROR=" ]; then
    PASS=$((PASS + 1))
    echo "PASS: already-running: ERROR empty"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: already-running: ERROR not empty: $error_line"
fi

# Case 4: missing --run-id → usage exit 1 (no output keys)
out=$(PATH="$stub_dir:$PATH" "$SCRIPT" --repo org/repo 2>&1) && rc=0 || rc=$?
if [ "$rc" -ne 0 ]; then
    PASS=$((PASS + 1))
    echo "PASS: missing-run-id: exits non-zero"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: missing-run-id: expected non-zero exit"
fi

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
