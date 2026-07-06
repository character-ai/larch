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
    shift
    set +e
    (
        cd "$TMPROOT" || exit 1
        bash "$LINT" --root "$TMPROOT" "$@"
    ) 2>"$stderr_file"
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

assert_not_in_stderr() {
    local label="$1"
    local stderr_file="$2"
    local needle="$3"

    if grep -Fq "$needle" "$stderr_file"; then
        printf 'FAIL [%s]: stderr contained unexpected needle: %s\n' "$label" "$needle" >&2
        cat "$stderr_file" >&2
        FAIL=$((FAIL + 1))
        return
    fi
}

assert_empty_stderr() {
    local label="$1"
    local stderr_file="$2"

    if [[ -s "$stderr_file" ]]; then
        printf 'FAIL [%s]: expected empty stderr\n' "$label" >&2
        cat "$stderr_file" >&2
        FAIL=$((FAIL + 1))
        return
    fi
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
arr=(a b c); echo "${arr[-1]}" # lint-bash32: ok fixture
echo {1..10..2} # lint-bash32: ok fixture
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
    "coproc" \
    "negative array index" \
    "step brace expansion"

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
write_sh "$TMPROOT/scripts/command-grep-condition.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

if command grep -Fq needle haystack.txt; then # lint-bash32: ok fixture
    printf '%s\n' found
fi
if ! command grep -Fq missing haystack.txt; then # lint-bash32: ok fixture
    printf '%s\n' missing
fi
if command rg -q needle .; then # lint-bash32: ok fixture
    printf '%s\n' rg-found
fi
if false; then
    printf '%s\n' skip
elif command grep -Eq needle haystack.txt; then # lint-bash32: ok fixture
    printf '%s\n' elif-found
fi
EOF
sed '/lint-bash32: ok fixture/s/[[:space:]]*# lint-bash32: ok fixture//' "$TMPROOT/scripts/command-grep-condition.sh" > "$TMPROOT/scripts/command-grep-condition-unsuppressed.sh"
rm -f "$TMPROOT/scripts/command-grep-condition.sh"
rc="$(run_lint "$stderr_file")"
assert_case "command grep-family conditions fail" 1 "$stderr_file" "$rc" \
    "scripts/command-grep-condition-unsuppressed.sh" \
    "scripts/command-grep-condition-unsuppressed.sh:4:" \
    "scripts/command-grep-condition-unsuppressed.sh:7:" \
    "scripts/command-grep-condition-unsuppressed.sh:10:" \
    "scripts/command-grep-condition-unsuppressed.sh:15:" \
    "if/elif command grep-family condition"

reset_tree
write_sh "$TMPROOT/scripts/safe-command-grep-condition.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

if ( command grep -Fq needle haystack.txt ) 2>/dev/null; then
    printf '%s\n' found
fi
if false; then
    printf '%s\n' skip
elif ( command grep -Eq needle haystack.txt ) 2>/dev/null; then
    printf '%s\n' elif-found
fi
cat haystack.txt | command grep -Fq needle
if command grep -Fq needle haystack.txt; then # lint-bash32: ok reviewed fixture
    printf '%s\n' reviewed
fi
EOF
rc="$(run_lint "$stderr_file")"
assert_case "safe command grep-family conditions pass" 0 "$stderr_file" "$rc"
assert_empty_stderr "safe command grep-family conditions pass" "$stderr_file"

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

reset_tree
write_sh "$TMPROOT/scripts/good.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

printf '%s\n' "${1:-ok}"
EOF
rc="$(run_lint "$stderr_file" scripts/good.sh)"
assert_case "positional clean .sh" 0 "$stderr_file" "$rc"
assert_empty_stderr "positional clean .sh" "$stderr_file"

reset_tree
write_sh "$TMPROOT/scripts/bad-positional.sh" <<'EOF'
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
sed '/lint-bash32: ok fixture/s/[[:space:]]*# lint-bash32: ok fixture//' "$TMPROOT/scripts/bad-positional.sh" > "$TMPROOT/scripts/bad-unsuppressed.sh"
rm -f "$TMPROOT/scripts/bad-positional.sh"
write_sh "$TMPROOT/scripts/bad-positional-2.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
declare -A sibling=() # lint-bash32: ok fixture
EOF
sed '/lint-bash32: ok fixture/s/[[:space:]]*# lint-bash32: ok fixture//' "$TMPROOT/scripts/bad-positional-2.sh" > "$TMPROOT/scripts/bad-unsuppressed-2.sh"
rm -f "$TMPROOT/scripts/bad-positional-2.sh"
rc="$(run_lint "$stderr_file" scripts/bad-unsuppressed.sh)"
assert_case "positional forbidden constructs .sh" 1 "$stderr_file" "$rc" \
    "scripts/bad-unsuppressed.sh" \
    "declare -A associative arrays" \
    "typeset -A associative arrays" \
    "mapfile/readarray" \
    "parameter case conversion" \
    "declare -n nameref" \
    "local -n nameref" \
    "&>""> append-all redirection" \
    "coproc"
assert_not_in_stderr "positional forbidden constructs .sh" "$stderr_file" "bad-unsuppressed-2.sh"

reset_tree
write_sh "$TMPROOT/scripts/helper.inc.bash" <<'EOF'
# shellcheck shell=bash
declare -A bad=() # lint-bash32: ok fixture
EOF
sed '/lint-bash32: ok fixture/s/[[:space:]]*# lint-bash32: ok fixture//' "$TMPROOT/scripts/helper.inc.bash" > "$TMPROOT/scripts/helper-bad.inc.bash"
rm -f "$TMPROOT/scripts/helper.inc.bash"
rc="$(run_lint "$stderr_file" scripts/helper-bad.inc.bash)"
assert_case "positional forbidden constructs .inc.bash" 1 "$stderr_file" "$rc" \
    "scripts/helper-bad.inc.bash" \
    "declare -A associative arrays"

reset_tree
write_sh "$TMPROOT/scripts/good.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' ok
EOF
printf '%s\n' '# notes' > "$TMPROOT/notes.md"
rc="$(run_lint "$stderr_file" scripts/good.sh notes.md)"
assert_case "positional skip non-shell" 0 "$stderr_file" "$rc" \
    "lint-bash32: skipping non-shell path: notes.md"

reset_tree
rc="$(run_lint "$stderr_file" /tmp/foo.sh)"
assert_case "positional skip outside-root" 0 "$stderr_file" "$rc" \
    "lint-bash32: skipping path outside lint root: /tmp/foo.sh"

reset_tree
write_sh "$TMPROOT/scripts/good.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' ok
EOF
rc="$(run_lint "$stderr_file" "$TMPROOT/scripts/good.sh")"
assert_case "positional absolute in-root .sh" 0 "$stderr_file" "$rc"
assert_empty_stderr "positional absolute in-root .sh" "$stderr_file"

reset_tree
OUTSIDE_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-lint-bash32-outside.XXXXXX")"
trap 'rm -rf "$TMPROOT" "$OUTSIDE_ROOT"' EXIT
write_sh "$OUTSIDE_ROOT/escaped.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
declare -A escaped=() # lint-bash32: ok fixture
EOF
sed '/lint-bash32: ok fixture/s/[[:space:]]*# lint-bash32: ok fixture//' "$OUTSIDE_ROOT/escaped.sh" >"$OUTSIDE_ROOT/escaped-unsuppressed.sh"
rm -f "$OUTSIDE_ROOT/escaped.sh"
rc="$(run_lint "$stderr_file" "../$(basename "$OUTSIDE_ROOT")/escaped-unsuppressed.sh")"
assert_case "positional skip relative parent traversal" 0 "$stderr_file" "$rc" \
    "lint-bash32: skipping path outside lint root: ../$(basename "$OUTSIDE_ROOT")/escaped-unsuppressed.sh"

reset_tree
write_sh "$OUTSIDE_ROOT/escaped.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
declare -A escaped=() # lint-bash32: ok fixture
EOF
sed '/lint-bash32: ok fixture/s/[[:space:]]*# lint-bash32: ok fixture//' "$OUTSIDE_ROOT/escaped.sh" >"$OUTSIDE_ROOT/escaped-unsuppressed.sh"
rm -f "$OUTSIDE_ROOT/escaped.sh"
rc="$(run_lint "$stderr_file" "$TMPROOT/../$(basename "$OUTSIDE_ROOT")/escaped-unsuppressed.sh")"
assert_case "positional skip absolute parent traversal outside-root" 0 "$stderr_file" "$rc" \
    "lint-bash32: skipping path outside lint root: $TMPROOT/../$(basename "$OUTSIDE_ROOT")/escaped-unsuppressed.sh"

if command -v git >/dev/null 2>&1; then
    reset_tree
    cat > "$TMPROOT/scripts/residual-bash-paths.txt" <<'EOF'
scripts/untracked-bad.sh
EOF
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
    assert_case "git worktree scans untracked manifest scripts" 1 "$stderr_file" "$rc" \
        "scripts/untracked-bad.sh:3:" \
        "declare -A associative arrays"
else
    printf 'SKIP [git worktree scans untracked manifest scripts]: git not on PATH\n'
fi

reset_tree
mkdir -p "$TMPROOT/scripts"
cat > "$TMPROOT/scripts/residual-bash-paths.txt" <<'EOF'
scripts/in-scope.sh
EOF
write_sh "$TMPROOT/scripts/in-scope.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' ok
EOF
write_sh "$TMPROOT/scripts/out-of-scope.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
declare -A seen=() # lint-bash32: ok fixture
EOF
sed '/lint-bash32: ok fixture/s/[[:space:]]*# lint-bash32: ok fixture//' "$TMPROOT/scripts/out-of-scope.sh" > "$TMPROOT/scripts/out-of-scope-bad.sh"
rm -f "$TMPROOT/scripts/out-of-scope.sh"
rc="$(run_lint "$stderr_file")"
assert_case "manifest scopes repo scan to in-scope paths" 0 "$stderr_file" "$rc"
assert_not_in_stderr "manifest scopes repo scan to in-scope paths" "$stderr_file" "out-of-scope-bad.sh"


reset_tree
write_sh "$TMPROOT/scripts/empty-array-at.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
items=()
printf '%s\n' "${items[@]}"
EOF
rc="$(run_lint "$stderr_file")"
assert_case "unguarded empty-array at expansion fails" 1 "$stderr_file" "$rc" \
    "scripts/empty-array-at.sh:4:" \
    "unguarded empty-array expansion \${items[@]}"

reset_tree
write_sh "$TMPROOT/scripts/empty-array-star.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
items=()
printf '%s\n' "${items[*]}"
EOF
rc="$(run_lint "$stderr_file")"
assert_case "unguarded empty-array star expansion fails" 1 "$stderr_file" "$rc" \
    "scripts/empty-array-star.sh:4:" \
    "unguarded empty-array expansion \${items[*]}"

reset_tree
write_sh "$TMPROOT/scripts/guarded-empty-array.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
items=()
if [ "${#items[@]}" -gt 0 ]; then
    printf '%s\n' "${items[@]}"
fi
EOF
rc="$(run_lint "$stderr_file")"
assert_case "length-guarded empty-array expansion passes" 0 "$stderr_file" "$rc"
assert_empty_stderr "length-guarded empty-array expansion passes" "$stderr_file"

reset_tree
write_sh "$TMPROOT/scripts/non-empty-array.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
items=(one)
printf '%s\n' "${items[@]}"
EOF
rc="$(run_lint "$stderr_file")"
assert_case "non-empty literal array is not flagged" 0 "$stderr_file" "$rc"
assert_empty_stderr "non-empty literal array is not flagged" "$stderr_file"

reset_tree
write_sh "$TMPROOT/scripts/suppressed-empty-array.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
items=()
printf '%s\n' "${items[@]}" # lint-bash32: ok reviewed fixture
other=()
printf '%s\n' "${other[@]}" # lint-bash32: ok
EOF
rc="$(run_lint "$stderr_file")"
assert_case "empty-array pragma suppresses with or without reason" 0 "$stderr_file" "$rc"
assert_empty_stderr "empty-array pragma suppresses with or without reason" "$stderr_file"

reset_tree
write_sh "$TMPROOT/scripts/commented-empty-array.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
items=()
# printf '%s\n' "${items[@]}"
EOF
rc="$(run_lint "$stderr_file")"
assert_case "commented empty-array expansion is ignored" 0 "$stderr_file" "$rc"
assert_empty_stderr "commented empty-array expansion is ignored" "$stderr_file"

reset_tree
write_sh "$TMPROOT/scripts/assignment-before-expansion.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
items=()
printf '%s\n' "${items[@]}"
EOF
rc="$(run_lint "$stderr_file")"
assert_case "same-line empty assignment before expansion fails" 1 "$stderr_file" "$rc" \
    "scripts/assignment-before-expansion.sh:4:" \
    "unguarded empty-array expansion \${items[@]}"

reset_tree
write_sh "$TMPROOT/scripts/repopulated-empty-array.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
items=()
if [ "${#items[@]}" -gt 0 ]; then
    printf '%s\n' "${items[@]}"
fi
items=(one)
items=()
printf '%s\n' "${items[@]}"
EOF
rc="$(run_lint "$stderr_file")"
assert_case "guard state clears after repopulation" 1 "$stderr_file" "$rc" \
    "scripts/repopulated-empty-array.sh:9:" \
    "unguarded empty-array expansion \${items[@]}"


reset_tree
cat > "$TMPROOT/scripts/lint-bash32-empty-array-baseline.tsv" <<'EOF'
scripts/baselined-empty-array.sh	items	fixture legacy empty expansion
EOF
write_sh "$TMPROOT/scripts/baselined-empty-array.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
items=()
printf '%s\n' "${items[@]}"
EOF
rc="$(run_lint "$stderr_file")"
assert_case "empty-array baseline suppresses with reason" 0 "$stderr_file" "$rc"
assert_empty_stderr "empty-array baseline suppresses with reason" "$stderr_file"

rm -f "$stderr_file"

printf 'Summary: %s passed, %s failed\n' "$PASS" "$FAIL"
if [[ "$FAIL" -ne 0 ]]; then
    exit 1
fi
