#!/usr/bin/env bash
# test-lint-no-raw-stderr-after-quiet-init.sh - Regression harness for python3 python/cli.py lint no-raw-stderr-after-quiet-init.

unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
CLI="$REPO_ROOT/python/cli.py"

if ! command -v python3 >/dev/null 2>&1; then
    echo "FAIL: python3 not on PATH" >&2
    exit 1
fi

if [[ ! -f "$CLI" ]]; then
    echo "ERROR: cli.py not found: $CLI" >&2
    exit 1
fi

TMPROOT=$(mktemp -d -t lint-no-raw-stderr-after-quiet-init-XXXXXX)
trap 'rm -rf "$TMPROOT"' EXIT

PASS=0
FAIL=0

assert_case() {
    local label="$1" expected_exit="$2" stderr_file="$3" exit_code="$4"
    shift 4
    if [[ "$exit_code" -ne "$expected_exit" ]]; then
        echo "FAIL [$label]: expected exit $expected_exit, got $exit_code" >&2
        echo "--- stderr ---" >&2
        cat "$stderr_file" >&2
        echo "--------------" >&2
        FAIL=$((FAIL + 1))
        return
    fi
    for needle in "$@"; do
        if ! grep -Fq "$needle" "$stderr_file"; then
            echo "FAIL [$label]: stderr missing expected needle: $needle" >&2
            echo "--- stderr ---" >&2
            cat "$stderr_file" >&2
            echo "--------------" >&2
            FAIL=$((FAIL + 1))
            return
        fi
    done
    PASS=$((PASS + 1))
    echo "PASS [$label]"
}

write_sh() {
    local path="$1"
    mkdir -p "$(dirname "$path")"
    cat > "$path"
}

reset_tree() {
    find "$TMPROOT" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
}

run_lint() {
    local stderr_file="$1"
    set +e
    python3 "$CLI" lint no-raw-stderr-after-quiet-init --root "$TMPROOT" 2>"$stderr_file"
    local rc=$?
    set -e
    echo "$rc"
}

# --- Case a: good fixture --------------------------------------------------
reset_tree
write_sh "$TMPROOT/scripts/good.sh" <<'EOF'
#!/usr/bin/env bash
echo "source failure before init" >&2
larch_quiet_init
larch_err "after init"
larch_errf 'after init %s\n' "formatted"
EOF
stderr_file=$(mktemp)
rc=$(run_lint "$stderr_file")
assert_case "a (known good)" 0 "$stderr_file" "$rc"
rm -f "$stderr_file"

# --- Case b: bad echo fixture ---------------------------------------------
reset_tree
write_sh "$TMPROOT/scripts/bad.sh" <<'EOF'
#!/usr/bin/env bash
larch_quiet_init
if true; then
    echo "after init" >&2
fi
EOF
stderr_file=$(mktemp)
rc=$(run_lint "$stderr_file")
assert_case "b (known bad echo)" 1 "$stderr_file" "$rc" \
    "scripts/bad.sh:4:" "S041/no-raw-stderr-after-quiet-init"
rm -f "$stderr_file"

# --- Case c: bad printf/cat fixtures under skill and hook scopes -----------
reset_tree
write_sh "$TMPROOT/skills/example/scripts/bad-skill.sh" <<'EOF'
#!/usr/bin/env bash
larch_quiet_init
printf 'after init\n' >&2
EOF
write_sh "$TMPROOT/hooks/bad-hook.sh" <<'EOF'
#!/usr/bin/env bash
larch_quiet_init
cat "$0" >&2
EOF
stderr_file=$(mktemp)
rc=$(run_lint "$stderr_file")
assert_case "c (skill and hook scopes)" 1 "$stderr_file" "$rc" \
    "skills/example/scripts/bad-skill.sh:3:" "hooks/bad-hook.sh:3:"
rm -f "$stderr_file"

# --- Case d: quoted/function/heredoc false positives -----------------------
reset_tree
write_sh "$TMPROOT/scripts/ignored.sh" <<'EOF'
#!/usr/bin/env bash
larch_quiet_init() { :; }
note='larch_quiet_init'
cat <<'TEXT'
echo "inside heredoc" >&2
TEXT
EOF
stderr_file=$(mktemp)
rc=$(run_lint "$stderr_file")
assert_case "d (ignored non-trigger text)" 0 "$stderr_file" "$rc"
rm -f "$stderr_file"

echo ""
echo "Summary: $PASS passed, $FAIL failed"
if (( FAIL > 0 )); then
    exit 1
fi
