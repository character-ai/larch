#!/usr/bin/env bash
# test-hydrate-anchor.sh - regression harness for scripts/hydrate-anchor.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HYDRATE_ANCHOR="$SCRIPT_DIR/hydrate-anchor.sh"
MARKERS_HELPER="$SCRIPT_DIR/anchor-section-markers.sh"

[ -x "$HYDRATE_ANCHOR" ] || { echo "FAIL: $HYDRATE_ANCHOR not executable" >&2; exit 1; }
[ -f "$MARKERS_HELPER" ] || { echo "FAIL: $MARKERS_HELPER missing" >&2; exit 1; }

tmp_root="$(mktemp -d "${TMPDIR:-/tmp}/hydrate-anchor-test.XXXXXX")"
cleanup() {
    chmod u+w "$tmp_root/session/session-id.md" "$tmp_root/.ssh/known_hosts.md" 2>/dev/null || true
    rm -rf "$tmp_root"
}
trap cleanup EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

pass_count=0
pass() {
    pass_count=$((pass_count + 1))
    echo "PASS: $1"
}

assert_contains() {
    local needle=$1
    local haystack=$2
    local label=$3

    if printf '%s' "$haystack" | grep -qF -- "$needle"; then
        pass "$label"
    else
        fail "$label: expected '$needle' in stdout, got: $haystack"
    fi
}

assert_file_equals() {
    local expected=$1
    local actual=$2
    local label=$3

    [ -f "$actual" ] || fail "$label: missing file $actual"
    if cmp -s "$expected" "$actual"; then
        pass "$label"
    else
        echo "Expected:" >&2
        sed 's/^/  /' "$expected" >&2
        echo "Actual:" >&2
        sed 's/^/  /' "$actual" >&2
        fail "$label: content mismatch"
    fi
}

session_tmp="$tmp_root/session"
mkdir -p "$session_tmp/anchor-hydrate" "$session_tmp/anchor-sections/oos-issues" "$tmp_root/.ssh"

fixture="$tmp_root/anchor-fixture.md"
cat > "$fixture" <<'EOF'
<!-- section:plan-goals-test -->
legitimate plan line
legitimate plan detail
<!-- section-end:plan-goals-test -->
<!-- section:../session-id -->
malicious session overwrite
<!-- section-end:../session-id -->
<!-- section:../../.ssh/known_hosts -->
malicious known hosts overwrite
<!-- section-end:../../.ssh/known_hosts -->
<!-- section:oos-issues/../escape -->
malicious embedded traversal
<!-- section-end:oos-issues/../escape -->
<!-- section:unknown-slug -->
unknown slug body
<!-- section-end:unknown-slug -->
<!-- section:code-review-tally -->
legitimate tally line
<!-- section-end:code-review-tally -->
<!-- section:token-report -->
## Token Report

| Step | Skill | Input | Output |
| --- | --- | ---: | ---: |
| Step 1 | larch:implement | 1 | 2 |
<!-- section-end:token-report -->
EOF

shim_dir="$tmp_root/bin"
mkdir -p "$shim_dir"
cat > "$shim_dir/gh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

if [ "${1:-}" = "api" ]; then
    cat "$HYDRATE_ANCHOR_FIXTURE"
    exit 0
fi

echo "unexpected gh invocation: $*" >&2
exit 1
EOF
chmod +x "$shim_dir/gh"

printf 'session canary\n' > "$session_tmp/session-id.md"
printf 'known hosts canary\n' > "$tmp_root/.ssh/known_hosts.md"
chmod a-w "$session_tmp/session-id.md" "$tmp_root/.ssh/known_hosts.md"

expected_plan="$tmp_root/expected-plan.md"
expected_tally="$tmp_root/expected-tally.md"
expected_token_report="$tmp_root/expected-token-report.md"
printf 'legitimate plan line\nlegitimate plan detail\n' > "$expected_plan"
printf 'legitimate tally line\n' > "$expected_tally"
{
    printf '## Token Report\n\n'
    printf '| Step | Skill | Input | Output |\n'
    printf '| --- | --- | ---: | ---: |\n'
    printf '| Step 1 | larch:implement | 1 | 2 |\n'
} > "$expected_token_report"

output="$(
    HYDRATE_ANCHOR_FIXTURE="$fixture" \
    PATH="$shim_dir:$PATH" \
    "$HYDRATE_ANCHOR" --anchor-id 1 --tmpdir "$session_tmp" --repo owner/repo
)"

assert_contains "HYDRATED=true" "$output" "hydrate succeeds with mixed valid and malicious markers"
assert_contains "SECTIONS=3" "$output" "section count includes only canonical extracted sections"
assert_file_equals "$expected_plan" "$session_tmp/anchor-sections/plan-goals-test.md" "canonical plan section extracted"
assert_file_equals "$expected_tally" "$session_tmp/anchor-sections/code-review-tally.md" "canonical tally section extracted"
assert_file_equals "$expected_token_report" "$session_tmp/anchor-sections/token-report.md" "canonical token-report section extracted"

[ ! -e "$session_tmp/anchor-sections/unknown-slug.md" ] \
    || fail "unknown slug should not produce a fragment"
[ ! -e "$session_tmp/anchor-sections/escape.md" ] \
    || fail "embedded traversal slug should not produce a normalized fragment"
pass "malicious and unknown slugs do not create fragment files"

chmod u+w "$session_tmp/session-id.md" "$tmp_root/.ssh/known_hosts.md"
[ "$(cat "$session_tmp/session-id.md")" = "session canary" ] \
    || fail "../ traversal canary was clobbered"
[ "$(cat "$tmp_root/.ssh/known_hosts.md")" = "known hosts canary" ] \
    || fail "../../ traversal canary was clobbered"
pass "pre-existing traversal canaries remain unchanged"

# Data-corruption regression: an invalid open marker that appears INSIDE an
# already-open valid section must drop out of that section so subsequent
# body lines are not appended to the legitimate fragment.
session_corrupt="$tmp_root/session-corrupt"
mkdir -p "$session_corrupt/anchor-hydrate"

fixture_corrupt="$tmp_root/anchor-fixture-corrupt.md"
cat > "$fixture_corrupt" <<'EOF'
<!-- section:plan-goals-test -->
legitimate plan line
<!-- section:../../etc/passwd -->
malicious content must not leak into plan-goals-test
<!-- section-end:plan-goals-test -->
<!-- section:code-review-tally -->
legitimate tally line
<!-- section-end:code-review-tally -->
EOF

expected_plan_clean="$tmp_root/expected-plan-clean.md"
printf 'legitimate plan line\n' > "$expected_plan_clean"

output_corrupt="$(
    HYDRATE_ANCHOR_FIXTURE="$fixture_corrupt" \
    PATH="$shim_dir:$PATH" \
    "$HYDRATE_ANCHOR" --anchor-id 2 --tmpdir "$session_corrupt" --repo owner/repo
)"

assert_contains "HYDRATED=true" "$output_corrupt" "hydrate succeeds when a malicious open is nested inside a valid section"
assert_file_equals "$expected_plan_clean" "$session_corrupt/anchor-sections/plan-goals-test.md" "nested malicious open does not leak content into the enclosing valid section"
assert_file_equals "$expected_tally" "$session_corrupt/anchor-sections/code-review-tally.md" "later valid section still extracts after a malformed predecessor"

echo
echo "Results: $pass_count passed"
