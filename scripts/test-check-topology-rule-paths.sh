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
  mkdir -p "$dir/skills/shared"
  printf '%s\n' "$dir"
}

write_tsv() {
  local dir="$1"
  local body="$2"
  printf '%b' "$body" >"$dir/skills/shared/topology.tsv"
}

write_valid_tsv() {
  local dir="$1"
  local value="$2"
  local authority="$3"
  printf 'key\t%s\tcomposition\t%s\n' "$value" "$authority" >"$dir/skills/shared/topology.tsv"
}

write_authority() {
  local dir="$1"
  local authority="$2"
  local body="$3"
  mkdir -p "$(dirname "$dir/$authority")"
  printf '%s\n' "$body" >"$dir/$authority"
}

# a. Happy path with a non-git fixture root.
dir="$(new_fixture happy)"
write_valid_tsv "$dir" "needle" "skills/foo.md"
write_authority "$dir" "skills/foo.md" "contains needle"
assert_success "happy path" "$dir"

# b. Missing authority file fails in a non-git fixture root.
dir="$(new_fixture missing-authority-file)"
write_valid_tsv "$dir" "needle" "skills/foo.md"
assert_failure_contains "missing authority file" "$dir" "runtime_authority file does not exist: skills/foo.md"

# c. Authority file exists but does not contain the row value.
dir="$(new_fixture authority-missing-value)"
write_valid_tsv "$dir" "needle" "skills/foo.md"
write_authority "$dir" "skills/foo.md" "wrong body"
assert_failure_contains "authority missing value" "$dir" "does not contain value 'needle'"

# d. Untracked authority file fails when --root points at a git work tree.
dir="$(new_fixture untracked-authority)"
write_valid_tsv "$dir" "needle" "skills/foo.md"
write_authority "$dir" "skills/foo.md" "contains needle"
git -C "$dir" init -q
git -C "$dir" add skills/shared/topology.tsv
assert_failure_contains "untracked authority" "$dir" "runtime_authority is not tracked by git: skills/foo.md"

# e. Tracked authority succeeds when --root points at a git work tree.
dir="$(new_fixture tracked-authority)"
write_valid_tsv "$dir" "needle" "skills/foo.md"
write_authority "$dir" "skills/foo.md" "contains needle"
git -C "$dir" init -q
git -C "$dir" add skills/shared/topology.tsv skills/foo.md
assert_success "tracked authority" "$dir"

# f. CRLF rejection in TSV.
dir="$(new_fixture tsv-crlf)"
printf 'key\tneedle\tcomposition\tskills/foo.md\r\n' >"$dir/skills/shared/topology.tsv"
write_authority "$dir" "skills/foo.md" "contains needle"
assert_failure_contains "tsv CRLF" "$dir" "CRLF line endings not allowed"

# g. Malformed TSV row.
dir="$(new_fixture malformed-row)"
write_tsv "$dir" 'key\tvalue\tonly-three\n'
assert_failure_contains "malformed row" "$dir" "row 1: malformed row"

# h1, h2, h4. Empty required TSV columns.
for spec in \
  "empty-col-1|\tvalue\tcomposition\tskills/foo.md" \
  "empty-col-2|key\t\tcomposition\tskills/foo.md" \
  "empty-col-4|key\tvalue\tcomposition\t"; do
  name="${spec%%|*}"
  row="${spec#*|}"
  dir="$(new_fixture "$name")"
  write_tsv "$dir" "$row\n"
  assert_failure_contains "$name" "$dir" "row 1: malformed row"
done

# i. Path-grammar rejection in TSV column 4.
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
  write_valid_tsv "$dir" "needle" "$path"
  assert_failure_contains "path $name" "$dir" "$needle"
done

# i2. Trailing-whitespace rejection in TSV column 4.
dir="$(new_fixture trailing-whitespace)"
write_tsv "$dir" 'key\tneedle\tcomposition\tskills/foo.md \n'
assert_failure_contains "trailing whitespace" "$dir" "leading or trailing whitespace"

# i3. Symlink escapes are rejected even when the manifest path is repo-relative.
dir="$(new_fixture symlink-escape)"
mkdir -p "$dir/skills"
printf 'outside needle\n' >"$TMP_ROOT/outside.md"
ln -s "$TMP_ROOT/outside.md" "$dir/skills/link.md"
write_valid_tsv "$dir" "needle" "skills/link.md"
assert_failure_contains "symlink escape" "$dir" "must resolve within repo root"

# i4. Symlinks inside the repo are not regular authority files.
dir="$(new_fixture symlink-in-repo)"
mkdir -p "$dir/skills"
printf 'contains needle\n' >"$dir/skills/real.md"
ln -s "real.md" "$dir/skills/link.md"
write_valid_tsv "$dir" "needle" "skills/link.md"
assert_failure_contains "symlink in repo" "$dir" "must be a regular file"

# j. Comments and blank lines in TSV tolerated.
dir="$(new_fixture comments-blanks)"
write_tsv "$dir" '# comment\n\nkey\tneedle\t\tskills/foo.md\n'
write_authority "$dir" "skills/foo.md" "contains needle"
assert_success "comments blanks" "$dir"

# k. Real-registry smoke, including current distinct-authority count pin.
real_dir="$TMP_ROOT/real-registry"
mkdir -p "$real_dir"
assert_abs_success "real registry smoke" "$real_dir"
authority_count="$(awk -F '\t' '$0 != "" && substr($0, 1, 1) != "#" { print $4 }' "$REPO_ROOT/skills/shared/topology.tsv" | sort -u | wc -l | tr -d ' ')"
if [[ "$authority_count" == "14" ]]; then
  pass_case
else
  fail_case "real registry authority count: expected 14, got $authority_count"
fi

# l. Empty TSV.
dir="$(new_fixture empty-tsv)"
write_tsv "$dir" '# comment\n\n'
assert_failure_contains "empty TSV" "$dir" "has no data rows"

# m. Script invoked from a non-root cwd resolves its repo root correctly.
nonroot_dir="$TMP_ROOT/non-root-cwd"
mkdir -p "$nonroot_dir"
assert_abs_success "non-root cwd" "$nonroot_dir"

if (( FAIL > 0 )); then
  printf 'FAIL: test-check-topology-rule-paths.sh - %s failures\n' "$FAIL" >&2
  printf '%s\n' "${FAIL_DETAILS[@]}" >&2
  exit 1
fi

printf 'PASS: test-check-topology-rule-paths.sh - %s assertions passed\n' "$PASS"
