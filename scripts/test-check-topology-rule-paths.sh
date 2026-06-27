#!/usr/bin/env bash
# Regression test for python3 python/cli.py lint topology-rule-paths.

set -euo pipefail
export LC_ALL=C

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CLI="$REPO_ROOT/python/cli.py"

PASS=0
FAIL=0
FAIL_DETAILS=()
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/larch-check-topology-rule-paths.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT

if ! command -v python3 >/dev/null 2>&1; then
  echo "FAIL: python3 not on PATH" >&2
  exit 1
fi
if [[ ! -f "$CLI" ]]; then
  echo "ERROR: cli.py not found: $CLI" >&2
  exit 1
fi

fail_case() {
  FAIL=$((FAIL + 1))
  FAIL_DETAILS+=("$1")
}

pass_case() {
  PASS=$((PASS + 1))
}

assert_contains() {
  local label="$1"
  local needle="$2"
  local haystack="$3"
  if [[ "$haystack" == *"$needle"* ]]; then
    pass_case
  else
    fail_case "$label: expected output to contain '$needle'; got '$haystack'"
  fi
}

assert_success() {
  local label="$1"
  local dir="$2"
  if (
    cd "$dir"
    python3 "$CLI" lint topology-rule-paths --root "$dir"
  ) >"$dir/stdout.txt" 2>"$dir/stderr.txt"; then
    pass_case
  else
    fail_case "$label: expected success; stderr: $(cat "$dir/stderr.txt")"
  fi
}

assert_failure_contains() {
  local label="$1"
  local dir="$2"
  local needle="$3"
  if (
    cd "$dir"
    python3 "$CLI" lint topology-rule-paths --root "$dir"
  ) >"$dir/stdout.txt" 2>"$dir/stderr.txt"; then
    fail_case "$label: expected failure"
    return
  fi
  assert_contains "$label" "$needle" "$(cat "$dir/stderr.txt")"
}

assert_abs_success() {
  local label="$1"
  local cwd="$2"
  if (
    cd "$cwd"
    python3 "$CLI" lint topology-rule-paths
  ) >"$cwd/stdout.txt" 2>"$cwd/stderr.txt"; then
    pass_case
  else
    fail_case "$label: expected success; stderr: $(cat "$cwd/stderr.txt")"
  fi
}

new_fixture() {
  local name="$1"
  local dir="$TMP_ROOT/$name"
  mkdir -p "$dir/skills/shared" "$dir/.claude/rules"
  printf '%s\n' "$dir"
}

write_tsv() {
  local dir="$1"
  local body="$2"
  printf '%b' "$body" >"$dir/skills/shared/topology.tsv"
}

write_rule_flow() {
  local dir="$1"
  shift
  {
    printf '%s\n' '---'
    printf 'paths: ['
    local sep=""
    local path
    for path in "$@"; do
      printf '%s"%s"' "$sep" "$path"
      sep=", "
    done
    printf ']\n'
    printf '%s\n' '---' '# Topology Generation'
  } >"$dir/.claude/rules/topology-generation.md"
}

write_rule_block() {
  local dir="$1"
  shift
  {
    printf '%s\n' '---'
    printf '%s\n' 'paths:'
    local path
    for path in "$@"; do
      printf '  - "%s"\n' "$path"
    done
    printf '%s\n' '---' '# Topology Generation'
  } >"$dir/.claude/rules/topology-generation.md"
}

write_valid_tsv() {
  local dir="$1"
  local authority="$2"
  printf 'key\tvalue\tcomposition\t%s\n' "$authority" >"$dir/skills/shared/topology.tsv"
}

# a. Happy path.
dir="$(new_fixture happy)"
write_valid_tsv "$dir" "skills/foo.md"
write_rule_flow "$dir" "skills/foo.md"
assert_success "happy path" "$dir"

# b. Missing-authority failure.
dir="$(new_fixture missing-authority)"
write_valid_tsv "$dir" "skills/foo.md"
write_rule_flow "$dir" "skills/bar.md"
assert_failure_contains "missing authority" "$dir" "skills/foo.md"

# c. Extra rule paths permitted.
dir="$(new_fixture extra-rule-paths)"
write_valid_tsv "$dir" "skills/foo.md"
write_rule_flow "$dir" "skills/foo.md" "docs/topology.md" "scripts/a.py" "scripts/b.py" "skills/bar.md" "README.md"
assert_success "extra rule paths" "$dir"

# d. Multiple missing authorities are listed sorted.
dir="$(new_fixture multiple-missing)"
write_tsv "$dir" 'z\tvalue\tcomposition\tskills/z.md\na\tvalue\tcomposition\tskills/a.md\n'
write_rule_flow "$dir" "skills/covered.md"
if (
  cd "$dir"
  python3 "$CLI" lint topology-rule-paths --root "$dir"
) >"$dir/stdout.txt" 2>"$dir/stderr.txt"; then
  fail_case "multiple missing: expected failure"
else
  assert_contains "multiple missing sorted" $'skills/a.md\n  - skills/z.md' "$(cat "$dir/stderr.txt")"
fi

# e. CRLF rejection in TSV.
dir="$(new_fixture tsv-crlf)"
printf 'key\tvalue\tcomposition\tskills/foo.md\r\n' >"$dir/skills/shared/topology.tsv"
write_rule_flow "$dir" "skills/foo.md"
assert_failure_contains "tsv CRLF" "$dir" "CRLF line endings not allowed"

# e2. CRLF rejection in rule frontmatter.
dir="$(new_fixture rule-crlf)"
write_valid_tsv "$dir" "skills/foo.md"
printf -- '---\r\npaths: ["skills/foo.md"]\r\n---\r\n# Topology Generation\n' >"$dir/.claude/rules/topology-generation.md"
assert_failure_contains "rule CRLF" "$dir" "CRLF line endings not allowed"

# f. Malformed TSV row.
dir="$(new_fixture malformed-row)"
write_tsv "$dir" 'key\tvalue\tonly-three\n'
write_rule_flow "$dir" "skills/foo.md"
assert_failure_contains "malformed row" "$dir" "row 1: malformed row"

# g1, g2, g4. Empty required TSV columns.
for spec in \
  "empty-col-1|\tvalue\tcomposition\tskills/foo.md" \
  "empty-col-2|key\t\tcomposition\tskills/foo.md" \
  "empty-col-4|key\tvalue\tcomposition\t"; do
  name="${spec%%|*}"
  row="${spec#*|}"
  dir="$(new_fixture "$name")"
  write_tsv "$dir" "$row\n"
  write_rule_flow "$dir" "skills/foo.md"
  assert_failure_contains "$name" "$dir" "row 1: malformed row"
done

# h. Path-grammar rejection in TSV column 4.
for spec in \
  "absolute|/foo|repo-relative" \
  "leading-dot|./foo|must not start with ./" \
  "parent|skills/../foo.md|parent traversal" \
  "duplicate-slash|skills//foo.md|duplicate slash"; do
  name="${spec%%|*}"
  rest="${spec#*|}"
  path="${rest%%|*}"
  needle="${rest#*|}"
  dir="$(new_fixture "path-$name")"
  write_valid_tsv "$dir" "$path"
  write_rule_flow "$dir" "$path"
  assert_failure_contains "path $name" "$dir" "$needle"
done

# h2. Trailing-whitespace rejection in TSV column 4.
dir="$(new_fixture trailing-whitespace)"
write_tsv "$dir" 'key\tvalue\tcomposition\tskills/foo.md \n'
write_rule_flow "$dir" "skills/foo.md "
assert_failure_contains "trailing whitespace" "$dir" "leading or trailing whitespace"

# h3. Symlink escapes are rejected even when the manifest path is repo-relative.
dir="$(new_fixture symlink-escape)"
mkdir -p "$dir/skills"
printf 'outside\n' >"$TMP_ROOT/outside.md"
ln -s "$TMP_ROOT/outside.md" "$dir/skills/link.md"
write_valid_tsv "$dir" "skills/link.md"
write_rule_flow "$dir" "skills/link.md"
assert_failure_contains "symlink escape" "$dir" "must resolve within repo root"

# i. Missing paths key.
dir="$(new_fixture missing-paths)"
write_valid_tsv "$dir" "skills/foo.md"
printf '%s\n' '---' 'name: topology-generation' '---' >"$dir/.claude/rules/topology-generation.md"
assert_failure_contains "missing paths" "$dir" "must define paths"

# j. paths is not a list.
dir="$(new_fixture paths-not-list)"
write_valid_tsv "$dir" "skills/foo.md"
printf '%s\n' '---' 'paths: skills/foo.md' '---' >"$dir/.claude/rules/topology-generation.md"
assert_failure_contains "paths not list" "$dir" "paths must be a list"

# k. paths contains a non-string entry.
dir="$(new_fixture paths-non-string)"
write_valid_tsv "$dir" "skills/foo.md"
printf '%s\n' '---' 'paths: ["skills/foo.md", 3, null, true]' '---' >"$dir/.claude/rules/topology-generation.md"
assert_failure_contains "paths non-string" "$dir" "must be a string"

# l. Rule file lacks frontmatter.
dir="$(new_fixture no-frontmatter)"
write_valid_tsv "$dir" "skills/foo.md"
printf '%s\n' '# Topology Generation' >"$dir/.claude/rules/topology-generation.md"
assert_failure_contains "no frontmatter" "$dir" "no YAML frontmatter found"

# m. Block-list YAML shape accepted.
dir="$(new_fixture block-list)"
write_valid_tsv "$dir" "skills/foo.md"
write_rule_block "$dir" "skills/foo.md"
assert_success "block-list" "$dir"

# n. Flow-style YAML shape accepted.
dir="$(new_fixture flow-style)"
write_valid_tsv "$dir" "skills/foo.md"
write_rule_flow "$dir" "skills/foo.md"
assert_success "flow-style" "$dir"

# o. Comments and blank lines in TSV tolerated.
dir="$(new_fixture comments-blanks)"
write_tsv "$dir" '# comment\n\nkey\tvalue\t\tskills/foo.md\n'
write_rule_flow "$dir" "skills/foo.md"
assert_success "comments blanks" "$dir"

# p. Real-registry smoke, including current distinct-authority count pin.
real_dir="$TMP_ROOT/real-registry"
mkdir -p "$real_dir"
assert_abs_success "real registry smoke" "$real_dir"
authority_count="$(awk -F '\t' '$0 != "" && substr($0, 1, 1) != "#" { print $4 }' "$REPO_ROOT/skills/shared/topology.tsv" | sort -u | wc -l | tr -d ' ')"
if [[ "$authority_count" == "14" ]]; then
  pass_case
else
  fail_case "real registry authority count: expected 14, got $authority_count"
fi

# q. Empty TSV.
dir="$(new_fixture empty-tsv)"
write_tsv "$dir" '# comment\n\n'
write_rule_flow "$dir" "skills/foo.md"
assert_failure_contains "empty TSV" "$dir" "has no data rows"

# r. Script invoked from a non-root cwd resolves its repo root correctly.
nonroot_dir="$TMP_ROOT/non-root-cwd"
mkdir -p "$nonroot_dir"
assert_abs_success "non-root cwd" "$nonroot_dir"

if (( FAIL > 0 )); then
  printf 'FAIL: test-check-topology-rule-paths.sh - %s failures\n' "$FAIL" >&2
  printf '%s\n' "${FAIL_DETAILS[@]}" >&2
  exit 1
fi

printf 'PASS: test-check-topology-rule-paths.sh - %s assertions passed\n' "$PASS"
