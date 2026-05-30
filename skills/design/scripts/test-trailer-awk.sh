#!/usr/bin/env bash
# Direct unit harness for lib-plan-optional-trailers.awk (issue #3204).

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
AWK="$SCRIPT_DIR/lib-plan-optional-trailers.awk"

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

TMPROOT=$(mktemp -d "${TMPDIR:-/tmp}/larch-trailer-awk-test.XXXXXX")
trap 'rm -rf "$TMPROOT"' EXIT

trailer_nr() {
    awk 'NF { nr = NR } END { print nr + 0 }' "$1"
}

write_fixture() {
    local name="$1"
    shift
    local path="$TMPROOT/$name"
    cat >"$path"
    printf '%s' "$path"
}

run_awk() {
    local mode="$1" fixture="$2"
    awk -v mode="$mode" -v trailer_nr="$(trailer_nr "$fixture")" -f "$AWK" "$fixture"
}

run_has_key() {
    local fixture="$1" key="$2"
    awk -v mode=has_key -v key="$key" -v trailer_nr="$(trailer_nr "$fixture")" \
        -f "$AWK" "$fixture"
}

assert_eq_lines() {
    local label="$1" got="$2" want="$3"
    if [[ "$(printf '%s' "$got")" != "$(printf '%s' "$want")" ]]; then
        printf 'FAIL: %s\n  got:\n%s\n  want:\n%s\n' "$label" "$got" "$want" >&2
        exit 1
    fi
}

assert_parse() {
    local fixture="$1" want="$2"
    local got
    got=$(run_awk parse "$fixture")
    assert_eq_lines "parse $(basename "$fixture")" "$got" "$want"
}

assert_keys() {
    local fixture="$1" want="$2"
    local got
    got=$(run_awk keys "$fixture")
    assert_eq_lines "keys $(basename "$fixture")" "$got" "$want"
}

assert_values() {
    local fixture="$1" want="$2"
    local got
    got=$(run_awk values "$fixture")
    assert_eq_lines "values $(basename "$fixture")" "$got" "$want"
}

assert_has_key() {
    local fixture="$1" key="$2" want_rc="$3"
    local rc
    set +e
    run_has_key "$fixture" "$key" >/dev/null
    rc=$?
    set -e
    [[ "$rc" == "$want_rc" ]] || fail "has_key $key on $(basename "$fixture") want rc=$want_rc got rc=$rc"
}

# --- parse ---
f=$(write_fixture all-three-present <<'EOF'
body
diff_added: 100
diff_deleted: 50
mechanical_churn: true
diff_lines: 200
EOF
)
assert_parse "$f" $'3\n100\n50\ntrue'

f=$(write_fixture none-present <<'EOF'
body
diff_lines: 1
EOF
)
assert_parse "$f" $'0\n-\n-\nfalse'

f=$(write_fixture octal-rejected <<'EOF'
body
diff_added: 08
diff_deleted: 09
diff_lines: 10
EOF
)
assert_parse "$f" $'0\n-\n-\nfalse'

f=$(write_fixture block-boundary <<'EOF'
body
diff_added: 99
not a trailer
diff_added: 5
diff_lines: 10
EOF
)
assert_parse "$f" $'1\n5\n-\nfalse'

# Blank line above diff_lines: terminates scan (orphan trailer above boundary).
f=$(write_fixture blank-before-diff-lines <<'EOF'
body
diff_added: 99

diff_lines: 10
EOF
)
assert_parse "$f" $'0\n-\n-\nfalse'

f=$(write_fixture octal-then-valid <<'EOF'
body
diff_added: 08
diff_added: 5
diff_lines: 10
EOF
)
assert_parse "$f" $'1\n5\n-\nfalse'

f=$(write_fixture mech-true <<'EOF'
body
diff_added: 1
mechanical_churn: true
diff_lines: 10
EOF
)
assert_parse "$f" $'2\n1\n-\ntrue'

f=$(write_fixture mech-false <<'EOF'
body
diff_added: 1
mechanical_churn: false
diff_lines: 10
EOF
)
assert_parse "$f" $'2\n1\n-\nfalse'

f=$(write_fixture retain-010 <<'EOF'
body
diff_added: 010
diff_deleted: 010
diff_lines: 10
EOF
)
assert_parse "$f" $'2\n010\n010\nfalse'

f=$(write_fixture duplicate-diff-added <<'EOF'
body
diff_added: 1
diff_added: 2
diff_lines: 10
EOF
)
assert_parse "$f" $'2\n2\n-\nfalse'

# --- keys ---
assert_keys "$TMPROOT/all-three-present" $'diff_added\ndiff_deleted\nmechanical_churn'
assert_keys "$TMPROOT/none-present" ''
assert_keys "$TMPROOT/octal-rejected" ''
assert_keys "$TMPROOT/octal-then-valid" 'diff_added'
assert_keys "$TMPROOT/blank-before-diff-lines" ''
assert_keys "$TMPROOT/mech-true" $'diff_added\nmechanical_churn'
assert_keys "$TMPROOT/mech-false" $'diff_added\nmechanical_churn'
assert_keys "$TMPROOT/retain-010" $'diff_added\ndiff_deleted'
assert_keys "$TMPROOT/duplicate-diff-added" 'diff_added'
assert_keys "$TMPROOT/block-boundary" 'diff_added'

# --- values ---
assert_values "$TMPROOT/block-boundary" 'diff_added=5'
assert_values "$TMPROOT/none-present" ''
assert_values "$TMPROOT/octal-rejected" ''
assert_values "$TMPROOT/octal-then-valid" 'diff_added=5'
assert_values "$TMPROOT/blank-before-diff-lines" ''
assert_values "$TMPROOT/all-three-present" $'diff_added=100\ndiff_deleted=50\nmechanical_churn=true'
assert_values "$TMPROOT/duplicate-diff-added" $'diff_added=2'
assert_values "$TMPROOT/mech-true" $'diff_added=1\nmechanical_churn=true'
assert_values "$TMPROOT/mech-false" $'diff_added=1\nmechanical_churn=false'
assert_values "$TMPROOT/retain-010" $'diff_added=010\ndiff_deleted=010'

# --- has_key (present) ---
assert_has_key "$TMPROOT/all-three-present" diff_added 0
assert_has_key "$TMPROOT/all-three-present" diff_deleted 0
assert_has_key "$TMPROOT/all-three-present" mechanical_churn 0
assert_has_key "$TMPROOT/mech-true" mechanical_churn 0
assert_has_key "$TMPROOT/mech-false" mechanical_churn 0
assert_has_key "$TMPROOT/retain-010" diff_added 0
assert_has_key "$TMPROOT/retain-010" diff_deleted 0

# --- has_key (absent / rejected) ---
assert_has_key "$TMPROOT/none-present" diff_added 1
assert_has_key "$TMPROOT/none-present" diff_deleted 1
assert_has_key "$TMPROOT/none-present" mechanical_churn 1
assert_has_key "$TMPROOT/octal-rejected" diff_added 1
assert_has_key "$TMPROOT/octal-rejected" diff_deleted 1
# block-boundary: in-block diff_added (rc=0). boundary-orphan-only / blank-before-diff-lines: rc=1.
assert_has_key "$TMPROOT/block-boundary" diff_added 0
assert_has_key "$TMPROOT/blank-before-diff-lines" diff_added 1
assert_has_key "$TMPROOT/octal-then-valid" diff_added 0

f=$(write_fixture boundary-orphan-only <<'EOF'
body
diff_added: 99
not a trailer
diff_lines: 10
EOF
)
assert_has_key "$f" diff_added 1

echo "PASS: test-trailer-awk.sh"
