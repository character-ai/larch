#!/usr/bin/env bash
# Regression harness for scripts/check-contains-pins.sh.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SUBJECT="$REPO_ROOT/scripts/check-contains-pins.sh"
LIB_QUIET="$REPO_ROOT/scripts/lib-quiet.sh"

if [[ ! -f "$SUBJECT" ]]; then
    echo "ERROR: required script not found: $SUBJECT" >&2
    exit 1
fi

PASS=0
FAIL=0
FAIL_DETAILS=()
TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-check-contains-pins.XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

fail_case() {
    FAIL=$((FAIL + 1))
    FAIL_DETAILS+=("$1")
}

pass_case() {
    PASS=$((PASS + 1))
}

assert_contains() {
    local label="$1" needle="$2" haystack="$3"
    if [[ "$haystack" == *"$needle"* ]]; then
        pass_case
    else
        fail_case "$label: expected output to contain '$needle'; got '${haystack:0:500}'"
    fi
}

assert_not_contains() {
    local label="$1" needle="$2" haystack="$3"
    if [[ "$haystack" == *"$needle"* ]]; then
        fail_case "$label: expected output not to contain '$needle'; got '${haystack:0:500}'"
    else
        pass_case
    fi
}

assert_exit_eq() {
    local label="$1" got="$2" want="$3"
    if [[ "$got" -eq "$want" ]]; then
        pass_case
    else
        fail_case "$label: expected exit $want, got $got"
    fi
}

new_fixture() {
    local name="$1"
    local dir="$TMPROOT/$name"
    mkdir -p "$dir/scripts" "$dir/docs" "$dir/home"
    cp "$SUBJECT" "$dir/scripts/check-contains-pins.sh"
    cp "$LIB_QUIET" "$dir/scripts/lib-quiet.sh"
    (
        cd "$dir"
        HOME="$dir/home" GIT_CONFIG_GLOBAL="$dir/gitconfig" git init -q -b main
    )
    printf '%s\n' "$dir"
}

run_checker() {
    local dir="$1"
    shift || true
    set +e
    RUN_OUT=$(cd "$dir" && LARCH_QUIET_DISABLE=1 HOME="$dir/home" GIT_CONFIG_GLOBAL="$dir/gitconfig" bash scripts/check-contains-pins.sh "$@" 2>"$dir/stderr.txt")
    RUN_EXIT=$?
    RUN_ERR=$(cat "$dir/stderr.txt")
    set -e
}

write_single_pin() {
    local dir="$1" literal="$2"
    printf '%s\n' "alpha beta gamma" "$literal" > "$dir/docs/target.md"
    cat > "$dir/scripts/test-fixture.sh" <<EOF
#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="\$(cd "\$(dirname "\$0")/.." && pwd -P)"
TARGET="\$REPO_ROOT/docs/target.md"
contains "\$TARGET" '$literal' 'target pin'
EOF
}

echo "=== Section 1: happy paths ==="

dir="$(new_fixture single-quoted)"
write_single_pin "$dir" "literal exists verbatim"
run_checker "$dir"
assert_exit_eq "single-quoted literal exists" "$RUN_EXIT" 0

dir="$(new_fixture double-quoted)"
printf '%s\n' "static double literal" > "$dir/docs/target.md"
cat > "$dir/scripts/test-fixture.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
TARGET="$REPO_ROOT/docs/target.md"
EOF
printf '%s "$%s" "%s" "%s"\n' "contains" "TARGET" "static double literal" "target pin" >> "$dir/scripts/test-fixture.sh"
run_checker "$dir"
assert_exit_eq "static double-quoted literal exists" "$RUN_EXIT" 0

dir="$(new_fixture double-quoted-backticks)"
# shellcheck disable=SC2016 # backticks are literal markdown fixture text
printf '%s\n' 'Use `literal token` exactly' > "$dir/docs/target.md"
cat > "$dir/scripts/test-fixture.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
TARGET="$REPO_ROOT/docs/target.md"
EOF
# shellcheck disable=SC2016 # backticks are literal markdown fixture text
printf '%s "$%s" "%s" "%s"\n' "contains" "TARGET" 'Use `literal token` exactly' "target pin" >> "$dir/scripts/test-fixture.sh"
run_checker "$dir"
assert_exit_eq "static double-quoted backtick literal exists" "$RUN_EXIT" 0
assert_not_contains "static double-quoted backtick literal is canonical" "SKIPPED_NON_CANONICAL" "$RUN_ERR"

dir="$(new_fixture indented-canonical)"
printf '%s\n' "indented canonical literal" > "$dir/docs/target.md"
cat > "$dir/scripts/test-fixture.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
TARGET="$REPO_ROOT/docs/target.md"
  contains "$TARGET" 'indented canonical literal' 'target pin'
EOF
run_checker "$dir"
assert_exit_eq "indented canonical literal exists" "$RUN_EXIT" 0

echo "=== Section 2: defect and warning paths ==="

dir="$(new_fixture diverged)"
printf '%s\n' "literal exists verbatim" > "$dir/docs/target.md"
cat > "$dir/scripts/test-diverged.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
TARGET="$REPO_ROOT/docs/target.md"
EOF
printf "%s \"\$%s\" '%s' '%s'\n" "contains" "TARGET" "literal exists verbatix" "target pin" >> "$dir/scripts/test-diverged.sh"
run_checker "$dir"
assert_exit_eq "diverged literal exits 1" "$RUN_EXIT" 1
assert_contains "diverged literal reports defect" "DEFECT: scripts/test-diverged.sh:5: literal 'literal exists verbatix' not found in docs/target.md" "$RUN_OUT"

dir="$(new_fixture unresolved)"
cat > "$dir/scripts/test-unresolved.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
EOF
printf "%s \"\$%s\" '%s' '%s'\n" "contains" "MISSING_MD" "literal" "target pin" >> "$dir/scripts/test-unresolved.sh"
run_checker "$dir"
assert_exit_eq "unresolved var exits 0" "$RUN_EXIT" 0
assert_contains "unresolved var warns" "UNRESOLVED_VAR: scripts/test-unresolved.sh:3: could not resolve \$MISSING_MD" "$RUN_ERR"

dir="$(new_fixture mixed-quote)"
cat > "$dir/scripts/test-mixed.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
TARGET="$REPO_ROOT/docs/target.md"
EOF
printf '%s "$%s" "%s$%s" "%s"\n' "contains" "TARGET" "prefix" "TARGET" "target pin" >> "$dir/scripts/test-mixed.sh"
run_checker "$dir"
assert_exit_eq "interpolated double literal exits 0" "$RUN_EXIT" 0
assert_contains "interpolated double literal warns" "SKIPPED_NON_CANONICAL: scripts/test-mixed.sh:5" "$RUN_ERR"

dir="$(new_fixture single-quoted-backticks)"
# shellcheck disable=SC2016 # backticks are literal markdown fixture text
printf '%s\n' 'Keep `markdown backticks` intact' > "$dir/docs/target.md"
cat > "$dir/scripts/test-backticks.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
TARGET="$REPO_ROOT/docs/target.md"
contains "$TARGET" 'Keep `markdown backticks` intact' 'target pin'
EOF
run_checker "$dir"
assert_exit_eq "single-quoted backtick literal exists" "$RUN_EXIT" 0

echo "=== Section 3: changed-file scoping and aggregation ==="

dir="$(new_fixture changed-scope)"
printf '%s\n' "target A current text" > "$dir/docs/target-A.md"
printf '%s\n' "target B current text" > "$dir/docs/target-B.md"
cat > "$dir/scripts/test-scope.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
TARGET_A="$REPO_ROOT/docs/target-A.md"
EOF
printf "%s \"\$%s\" '%s' '%s'\n" "contains" "TARGET_A" "target A stale text" "target A pin" >> "$dir/scripts/test-scope.sh"
printf '%s\n' "docs/target-B.md" > "$dir/changed.txt"
run_checker "$dir" --changed-files "$dir/changed.txt"
assert_exit_eq "changed-files skips untouched target" "$RUN_EXIT" 0
assert_not_contains "changed-files skip has no defect" "DEFECT:" "$RUN_OUT"

dir="$(new_fixture changed-target-scope)"
printf '%s\n' "target A current text" > "$dir/docs/target-A.md"
cat > "$dir/scripts/test-scope.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
TARGET_A="$REPO_ROOT/docs/target-A.md"
EOF
printf "%s \"\$%s\" '%s' '%s'\n" "contains" "TARGET_A" "target A stale text" "target A pin" >> "$dir/scripts/test-scope.sh"
printf '%s\n' "docs/target-A.md" > "$dir/changed.txt"
run_checker "$dir" --changed-files "$dir/changed.txt"
assert_exit_eq "changed-files checks changed target pins" "$RUN_EXIT" 1
assert_contains "changed target reports defect" "DEFECT: scripts/test-scope.sh:5: literal 'target A stale text' not found in docs/target-A.md" "$RUN_OUT"

dir="$(new_fixture changed-script-scope)"
printf '%s\n' "target A current text" > "$dir/docs/target-A.md"
cat > "$dir/scripts/test-scope.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
TARGET_A="$REPO_ROOT/docs/target-A.md"
EOF
printf "%s \"\$%s\" '%s' '%s'\n" "contains" "TARGET_A" "target A stale text" "target A pin" >> "$dir/scripts/test-scope.sh"
printf '%s\n' "scripts/test-scope.sh" > "$dir/changed.txt"
run_checker "$dir" --changed-files "$dir/changed.txt"
assert_exit_eq "changed-files checks changed test script pins" "$RUN_EXIT" 1
assert_contains "changed test script reports defect" "DEFECT: scripts/test-scope.sh:5: literal 'target A stale text' not found in docs/target-A.md" "$RUN_OUT"

dir="$(new_fixture changed-script-unresolved)"
cat > "$dir/scripts/test-unresolved.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
EOF
printf "%s \"\$%s\" '%s' '%s'\n" "contains" "MISSING_MD" "literal" "target pin" >> "$dir/scripts/test-unresolved.sh"
printf '%s\n' "scripts/test-unresolved.sh" > "$dir/changed.txt"
run_checker "$dir" --changed-files "$dir/changed.txt"
assert_exit_eq "changed-files unresolved var exits 0" "$RUN_EXIT" 0
assert_contains "changed-files unresolved var warns" "UNRESOLVED_VAR: scripts/test-unresolved.sh:3: could not resolve \$MISSING_MD" "$RUN_ERR"

dir="$(new_fixture repo-escape)"
printf '%s\n' "outside repo" > "$TMPROOT/outside-target.md"
cat > "$dir/scripts/test-escape.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
TARGET="$REPO_ROOT/../outside-target.md"
contains "$TARGET" 'outside repo' 'target pin'
EOF
run_checker "$dir"
assert_exit_eq "repo escape exits 0" "$RUN_EXIT" 0
assert_contains "repo escape warns unresolved" "UNRESOLVED_VAR: scripts/test-escape.sh:5: could not resolve \$TARGET" "$RUN_ERR"

dir="$(new_fixture multi-defect)"
printf '%s\n' "first target" > "$dir/docs/a.md"
printf '%s\n' "second target" > "$dir/docs/b.md"
cat > "$dir/scripts/test-a.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
A="$REPO_ROOT/docs/a.md"
EOF
printf "%s \"\$%s\" '%s' '%s'\n" "contains" "A" "missing one" "pin one" >> "$dir/scripts/test-a.sh"
printf "%s \"\$%s\" '%s' '%s'\n" "contains" "A" "missing two" "pin two" >> "$dir/scripts/test-a.sh"
cat > "$dir/scripts/test-b.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
B="$REPO_ROOT/docs/b.md"
EOF
printf "%s \"\$%s\" '%s' '%s'\n" "contains" "B" "missing three" "pin three" >> "$dir/scripts/test-b.sh"
run_checker "$dir"
assert_exit_eq "multiple defects exit 1" "$RUN_EXIT" 1
assert_contains "multiple defects first" "literal 'missing one' not found in docs/a.md" "$RUN_OUT"
assert_contains "multiple defects second" "literal 'missing two' not found in docs/a.md" "$RUN_OUT"
assert_contains "multiple defects third" "literal 'missing three' not found in docs/b.md" "$RUN_OUT"

echo "=== Section 4: empty and portability paths ==="

dir="$(new_fixture empty)"
run_checker "$dir"
assert_exit_eq "empty test set exits 0" "$RUN_EXIT" 0

dir="$(new_fixture env-clean)"
write_single_pin "$dir" "portable literal"
set +e
RUN_OUT=$(cd "$dir" && env -i PATH="/usr/bin:/bin" HOME="$dir/home" GIT_CONFIG_GLOBAL="$dir/gitconfig" LARCH_QUIET_DISABLE=1 bash scripts/check-contains-pins.sh 2>"$dir/stderr.txt")
RUN_EXIT=$?
RUN_ERR=$(cat "$dir/stderr.txt")
set -e
assert_exit_eq "env-clean bash invocation exits 0" "$RUN_EXIT" 0
subject_source="$(cat "$SUBJECT")"
declare_prefix="declare -"
assoc_suffix="A"
map_prefix="map"
map_suffix="file"
caret_char="^"
append_prefix="&"
append_suffix=">>"
assert_not_contains "no associative-array syntax usage" "${declare_prefix}${assoc_suffix}" "$subject_source"
assert_not_contains "no line-array helper usage" "${map_prefix}${map_suffix}" "$subject_source"
assert_not_contains "no uppercase parameter expansion" "${caret_char}${caret_char}" "$subject_source"
assert_not_contains "no append-all redirect" "${append_prefix}${append_suffix}" "$subject_source"

echo ""
echo "=== Summary ==="
echo "PASS=$PASS"
echo "FAIL=$FAIL"

if [[ "$FAIL" -ne 0 ]]; then
    echo "Failed tests:" >&2
    for detail in "${FAIL_DETAILS[@]}"; do
        echo "  - $detail" >&2
    done
    exit 1
fi

exit 0
