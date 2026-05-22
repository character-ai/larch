#!/usr/bin/env bash
# test-lint-bash32.sh - Regression harness for scripts/lint-bash32.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LINT="$REPO_ROOT/scripts/lint-bash32.sh"

if [[ ! -f "$LINT" ]]; then
    printf 'ERROR: lint script not found: %s\n' "$LINT" >&2
    exit 1
fi

TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-lint-bash32.XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

PASS=0
FAIL=0

reset_tree() {
    find "$TMPROOT" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
    mkdir -p "$TMPROOT/scripts"
}

write_sh() {
    local path="$1"
    mkdir -p "$(dirname "$path")"
    cat > "$path"
}

run_lint() {
    local stderr_file="$1"
    set +e
    bash "$LINT" --root "$TMPROOT" 2>"$stderr_file"
    local rc=$?
    set -e
    printf '%s\n' "$rc"
}

assert_case() {
    local label="$1"
    local expected_exit="$2"
    local stderr_file="$3"
    local rc="$4"
    shift 4

    if [[ "$rc" -ne "$expected_exit" ]]; then
        printf 'FAIL [%s]: expected exit %s, got %s\n' "$label" "$expected_exit" "$rc" >&2
        cat "$stderr_file" >&2
        FAIL=$((FAIL + 1))
        return
    fi
    for needle in "$@"; do
        if ! grep -Fq "$needle" "$stderr_file"; then
            printf 'FAIL [%s]: stderr missing expected needle: %s\n' "$label" "$needle" >&2
            cat "$stderr_file" >&2
            FAIL=$((FAIL + 1))
            return
        fi
    done
    printf 'PASS [%s]\n' "$label"
    PASS=$((PASS + 1))
}

stderr_file="$(mktemp)"

reset_tree
write_sh "$TMPROOT/scripts/good.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

lower=$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')
while IFS= read -r line; do
    printf '%s\n' "$lower:$line"
done
EOF
rc="$(run_lint "$stderr_file")"
assert_case "clean Bash 3.2 script" 0 "$stderr_file" "$rc"

reset_tree
write_sh "$TMPROOT/scripts/bad.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
declare -A seen=() # lint-bash32: ok fixture
typeset -A old=() # lint-bash32: ok fixture
mapfile -t rows < input.txt # lint-bash32: ok fixture
readarray -t more < input.txt # lint-bash32: ok fixture
echo "${NAME^^}" # lint-bash32: ok fixture
echo "${NAME^}" # lint-bash32: ok fixture
echo "${NAME,,}" # lint-bash32: ok fixture
echo "${NAME,}" # lint-bash32: ok fixture
declare -n ref=target # lint-bash32: ok fixture
local -n inner=target # lint-bash32: ok fixture
cmd &>> log.txt # lint-bash32: ok fixture
coproc WORKER { cat; } # lint-bash32: ok fixture
coproc { cat; } # lint-bash32: ok fixture
EOF
sed '/lint-bash32: ok fixture/s/[[:space:]]*# lint-bash32: ok fixture//' "$TMPROOT/scripts/bad.sh" > "$TMPROOT/scripts/bad-unsuppressed.sh"
rm -f "$TMPROOT/scripts/bad.sh"
rc="$(run_lint "$stderr_file")"
assert_case "forbidden constructs" 1 "$stderr_file" "$rc" \
    "declare -A associative arrays" \
    "typeset -A associative arrays" \
    "mapfile/readarray" \
    "parameter case conversion" \
    "declare -n nameref" \
    "local -n nameref" \
    "&>""> append-all redirection" \
    "coproc"

reset_tree
write_sh "$TMPROOT/scripts/comments-and-allow.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
# declare -A in a comment is documentation, not code.
# mapfile and ${VAR,,} in a comment are ignored.
grep -nE 'declare -A|mapfile|\$\{[A-Z_]+,,\}' target.sh # lint-bash32: ok intentional static pattern
EOF
rc="$(run_lint "$stderr_file")"
assert_case "comments and inline allow" 0 "$stderr_file" "$rc"

reset_tree
write_sh "$TMPROOT/scripts/char-class-negation.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
# ${var//[^A-Z]/x} is substitution with char-class negation, not case conversion.
safe="${MYVAR//[^A-Za-z0-9_-]/_}"
other="${bad_cap//[^a-zA-Z0-9]/x}"
csv="${expected_csv:+,}more"
EOF
rc="$(run_lint "$stderr_file")"
assert_case "char-class negation not flagged" 0 "$stderr_file" "$rc"

reset_tree
write_sh "$TMPROOT/scripts/helper.inc.bash" <<'EOF'
# shellcheck shell=bash
declare -A bad=() # lint-bash32: ok fixture
EOF
sed '/lint-bash32: ok fixture/s/[[:space:]]*# lint-bash32: ok fixture//' "$TMPROOT/scripts/helper.inc.bash" >"$TMPROOT/scripts/helper-bad.inc.bash"
rm -f "$TMPROOT/scripts/helper.inc.bash"
rc="$(run_lint "$stderr_file")"
assert_case "inc.bash extension is scanned" 1 "$stderr_file" "$rc" \
    "scripts/helper-bad.inc.bash" \
    "declare -A associative arrays"

if command -v git >/dev/null 2>&1; then
    reset_tree
    (
        cd "$TMPROOT"
        git init -q
    )
    write_sh "$TMPROOT/scripts/untracked-bad.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
EOF
    printf '%s\n' 'declare -A seen=()' >> "$TMPROOT/scripts/untracked-bad.sh" # lint-bash32: ok fixture
    rc="$(run_lint "$stderr_file")"
    assert_case "git worktree scans untracked scripts" 1 "$stderr_file" "$rc" \
        "scripts/untracked-bad.sh:3:" \
        "declare -A associative arrays"
else
    printf 'SKIP [git worktree scans untracked scripts]: git not on PATH\n'
fi

rm -f "$stderr_file"

printf 'Summary: %s passed, %s failed\n' "$PASS" "$FAIL"
if [[ "$FAIL" -ne 0 ]]; then
    exit 1
fi
