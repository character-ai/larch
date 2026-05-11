#!/usr/bin/env bash
# Regression test for scripts/check-generators.sh.
# shellcheck disable=SC2016

set -euo pipefail
export LC_ALL=C

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SUBJECT="$REPO_ROOT/scripts/check-generators.sh"

PASS=0
FAIL=0
FAIL_DETAILS=()
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/larch-check-generators.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT

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

assert_equals() {
  local label="$1"
  local expected="$2"
  local actual="$3"
  if [[ "$actual" == "$expected" ]]; then
    pass_case
  else
    fail_case "$label: expected '$expected', got '$actual'"
  fi
}

new_fixture() {
  local name="$1"
  local dir="$TMP_ROOT/$name"
  mkdir -p "$dir/scripts" "$dir/agents" "$dir/subdir"
  cp "$SUBJECT" "$dir/scripts/check-generators.sh"
  printf '%s\n' "$dir"
}

commit_fixture() {
  local dir="$1"
  shift
  (
    cd "$dir"
    # Create $HOME before any git invocation: some git builds (or templateDir
    # hooks) error out when HOME does not exist.
    mkdir -p "$dir/home"
    HOME="$dir/home" GIT_CONFIG_GLOBAL="$dir/gitconfig" git init -q
    HOME="$dir/home" GIT_CONFIG_GLOBAL="$dir/gitconfig" git -c user.name=test -c user.email=test@test.invalid -c commit.gpgsign=false add scripts/generators.tsv "$@"
    HOME="$dir/home" GIT_CONFIG_GLOBAL="$dir/gitconfig" git -c user.name=test -c user.email=test@test.invalid -c commit.gpgsign=false commit -q -m "fixture baseline"
  )
}

write_generator() {
  local path="$1"
  local body="$2"
  {
    printf '%s\n' '#!/usr/bin/env bash'
    printf '%s\n' 'set -euo pipefail'
    printf '%s\n' "$body"
  } >"$path"
  chmod +x "$path"
}

run_walker() {
  local dir="$1"
  shift || true
  (
    cd "$dir"
    HOME="$dir/home" GIT_CONFIG_GLOBAL="$dir/gitconfig" bash scripts/check-generators.sh "$@"
  )
}

assert_walker_success() {
  local label="$1"
  local dir="$2"
  local err="$dir/stderr.txt"
  if run_walker "$dir" >"$dir/stdout.txt" 2>"$err"; then
    pass_case
  else
    fail_case "$label: expected success; stderr: $(cat "$err")"
  fi
}

assert_walker_failure_contains() {
  # Both "walker exited non-zero" and "stderr contains needle" must hold for the
  # case to count as a single PASS. Counting each separately would inflate PASS
  # when the needle is missing (PASS=1, FAIL=1 for one logical case).
  local label="$1"
  local dir="$2"
  local needle="$3"
  local err="$dir/stderr.txt"
  if run_walker "$dir" >"$dir/stdout.txt" 2>"$err"; then
    fail_case "$label: expected failure"
    return
  fi
  local haystack
  haystack="$(cat "$err")"
  if [[ "$haystack" == *"$needle"* ]]; then
    pass_case
  else
    fail_case "$label: expected output to contain '$needle'; got '$haystack'"
  fi
}

setup_single_valid_fixture() {
  local name="$1"
  local dir
  dir="$(new_fixture "$name")"
  printf 'generated\n' >"$dir/agents/out.md"
  write_generator "$dir/scripts/gen.sh" '[[ "${1:-}" == "--check" ]] || { echo "Usage: $0 [--check]" >&2; exit 2; }'
  printf 'scripts/gen.sh\tagents/out.md\n' >"$dir/scripts/generators.tsv"
  commit_fixture "$dir" scripts/generators.tsv agents/out.md
  printf '%s\n' "$dir"
}

# a. Happy path.
dir="$(setup_single_valid_fixture happy)"
assert_walker_success "happy path" "$dir"

# b. Drift failure from generator.
dir="$(new_fixture drift)"
printf 'generated\n' >"$dir/agents/out.md"
write_generator "$dir/scripts/gen.sh" '[[ "${1:-}" == "--check" ]] || exit 2; echo generator failed >&2; exit 1'
printf 'scripts/gen.sh\tagents/out.md\n' >"$dir/scripts/generators.tsv"
commit_fixture "$dir" scripts/generators.tsv agents/out.md
assert_walker_failure_contains "drift failure" "$dir" "drift detected"
assert_contains "drift names generator" "scripts/gen.sh" "$(cat "$dir/stderr.txt")"

# c-d4. Malformed rows.
for spec in \
  "too-few|scripts/gen.sh|malformed row" \
  "too-many|scripts/gen.sh	agents/out.md	extra|malformed row" \
  "empty-middle|scripts/gen.sh		agents/out.md|malformed row" \
  "leading-tab|	scripts/gen.sh	agents/out.md|malformed row" \
  "trailing-tab|scripts/gen.sh	agents/out.md	|malformed row"; do
  name="${spec%%|*}"
  rest="${spec#*|}"
  row="${rest%%|*}"
  needle="${rest#*|}"
  dir="$(new_fixture "malformed-$name")"
  printf 'generated\n' >"$dir/agents/out.md"
  write_generator "$dir/scripts/gen.sh" '[[ "${1:-}" == "--check" ]] || exit 2'
  printf '%s\n' "$row" >"$dir/scripts/generators.tsv"
  commit_fixture "$dir" scripts/generators.tsv agents/out.md
  assert_walker_failure_contains "malformed $name" "$dir" "$needle"
done

# e. Comment + blank tolerance, invoked exactly once.
dir="$(new_fixture comments)"
printf 'generated\n' >"$dir/agents/out.md"
write_generator "$dir/scripts/gen.sh" '[[ "${1:-}" == "--check" ]] || exit 2; printf "called\n" >> scripts/calls.log'
printf '# comment\n\nscripts/gen.sh\tagents/out.md\n' >"$dir/scripts/generators.tsv"
commit_fixture "$dir" scripts/generators.tsv agents/out.md
assert_walker_success "comment blank tolerance" "$dir"
assert_equals "comment fixture call count" "called" "$(sed -n '1p' "$dir/scripts/calls.log")"
assert_equals "comment fixture one call" "1" "$(wc -l <"$dir/scripts/calls.log" | tr -d ' ')"

# f. Empty registry.
dir="$(new_fixture empty)"
printf '# comment\n\n' >"$dir/scripts/generators.tsv"
commit_fixture "$dir" scripts/generators.tsv
assert_walker_failure_contains "empty registry" "$dir" "no rows registered"

# g-h2. Path grammar.
for spec in \
  "absolute|/tmp/gen.sh	agents/out.md|absolute path" \
  "parent|scripts/../gen.sh	agents/out.md|parent traversal" \
  "leading-dot|./scripts/gen.sh	agents/out.md|must not start with ./" \
  "leading-dash|-rf	agents/out.md|must not start with -" \
  "duplicate-slash|scripts//gen.sh	agents/out.md|duplicate slash" \
  "git-pathspec|:(top)scripts/gen.sh	agents/out.md|reserved for git pathspec magic"; do
  name="${spec%%|*}"
  rest="${spec#*|}"
  row="${rest%%|*}"
  needle="${rest#*|}"
  dir="$(new_fixture "path-$name")"
  printf 'generated\n' >"$dir/agents/out.md"
  write_generator "$dir/scripts/gen.sh" '[[ "${1:-}" == "--check" ]] || exit 2'
  printf '%s\n' "$row" >"$dir/scripts/generators.tsv"
  commit_fixture "$dir" scripts/generators.tsv agents/out.md
  assert_walker_failure_contains "path $name" "$dir" "$needle"
done

# i. Missing generator script.
dir="$(new_fixture missing-generator)"
printf 'generated\n' >"$dir/agents/out.md"
printf 'scripts/missing.sh\tagents/out.md\n' >"$dir/scripts/generators.tsv"
commit_fixture "$dir" scripts/generators.tsv agents/out.md
assert_walker_failure_contains "missing generator" "$dir" "generator script not found"

# j. Missing output path.
dir="$(new_fixture missing-output)"
write_generator "$dir/scripts/gen.sh" '[[ "${1:-}" == "--check" ]] || exit 2'
printf 'scripts/gen.sh\tagents/missing.md\n' >"$dir/scripts/generators.tsv"
commit_fixture "$dir" scripts/generators.tsv
assert_walker_failure_contains "missing output" "$dir" "output path not found"

# j2. Untracked output path.
dir="$(new_fixture untracked-output)"
printf 'generated\n' >"$dir/agents/out.md"
write_generator "$dir/scripts/gen.sh" '[[ "${1:-}" == "--check" ]] || exit 2'
printf 'scripts/gen.sh\tagents/out.md\n' >"$dir/scripts/generators.tsv"
commit_fixture "$dir" scripts/generators.tsv
assert_walker_failure_contains "untracked output" "$dir" "not tracked"

# k-l. Duplicates.
dir="$(new_fixture duplicate-generator)"
printf 'a\n' >"$dir/agents/a.md"
printf 'b\n' >"$dir/agents/b.md"
write_generator "$dir/scripts/gen.sh" '[[ "${1:-}" == "--check" ]] || exit 2'
printf 'scripts/gen.sh\tagents/a.md\nscripts/gen.sh\tagents/b.md\n' >"$dir/scripts/generators.tsv"
commit_fixture "$dir" scripts/generators.tsv agents/a.md agents/b.md
assert_walker_failure_contains "duplicate generator" "$dir" "duplicate generator"

dir="$(new_fixture duplicate-output)"
printf 'a\n' >"$dir/agents/a.md"
write_generator "$dir/scripts/gen-a.sh" '[[ "${1:-}" == "--check" ]] || exit 2'
write_generator "$dir/scripts/gen-b.sh" '[[ "${1:-}" == "--check" ]] || exit 2'
printf 'scripts/gen-a.sh\tagents/a.md\nscripts/gen-b.sh\tagents/a.md\n' >"$dir/scripts/generators.tsv"
commit_fixture "$dir" scripts/generators.tsv agents/a.md
assert_walker_failure_contains "duplicate output" "$dir" "duplicate output"

# m. Sequential ordering.
dir="$(new_fixture sequential)"
printf 'a\n' >"$dir/agents/a.md"
printf 'b\n' >"$dir/agents/b.md"
write_generator "$dir/scripts/gen-a.sh" '[[ "${1:-}" == "--check" ]] || exit 2; printf "gen-a\n" >> scripts/order.log'
write_generator "$dir/scripts/gen-b.sh" '[[ "${1:-}" == "--check" ]] || exit 2; printf "gen-b\n" >> scripts/order.log'
printf 'scripts/gen-a.sh\tagents/a.md\nscripts/gen-b.sh\tagents/b.md\n' >"$dir/scripts/generators.tsv"
commit_fixture "$dir" scripts/generators.tsv agents/a.md agents/b.md
assert_walker_success "sequential ordering" "$dir"
assert_equals "sequential log" $'gen-a\ngen-b' "$(<"$dir/scripts/order.log")"

# n. Real-registry smoke. The row count and canonical rows are intentionally
# pinned: any legitimate addition to scripts/generators.tsv must update BOTH
# assertions below in the same PR. The pin acts as a guardrail so an accidental
# row removal fails CI loudly.
data_rows="$(awk -F '\t' '!/^#/ && NF == 2 && $1 != "" && $2 != "" { print $1 "\t" $2 }' "$REPO_ROOT/scripts/generators.tsv")"
assert_equals "real registry row count" "8" "$(printf '%s\n' "$data_rows" | sed '/^$/d' | wc -l | tr -d ' ')"
assert_equals "real registry canonical rows" $'scripts/generate-code-reviewer-agent.sh\tagents/code-reviewer.md\nscripts/generate-reviewer-correctness-edges-agent.sh\tagents/reviewer-correctness-edges.md\nscripts/generate-reviewer-security-structure-tests-agent.sh\tagents/reviewer-security-structure-tests.md\nscripts/generate-pre-rendered-reviewer-prompts.sh\tagents/pre-rendered/.manifest\nscripts/generate-cursor-implementer.sh\tagents/cursor-implementer.md\nscripts/generate-gemini-implementer.sh\tagents/gemini-implementer.md\nscripts/generate-codex-implementer.sh\tagents/codex-implementer.md\nscripts/generate-topology-docs.sh\tdocs/topology.md' "$data_rows"

# o. Post-run drift detection.
dir="$(new_fixture post-run-drift)"
printf 'generated\n' >"$dir/agents/out.md"
write_generator "$dir/scripts/gen.sh" '[[ "${1:-}" == "--check" ]] || exit 2; printf "mutated\n" > agents/out.md'
printf 'scripts/gen.sh\tagents/out.md\n' >"$dir/scripts/generators.tsv"
commit_fixture "$dir" scripts/generators.tsv agents/out.md
assert_walker_failure_contains "post-run drift" "$dir" "post-run working-tree delta"

# p. CRLF rejection.
dir="$(new_fixture crlf)"
printf 'generated\n' >"$dir/agents/out.md"
write_generator "$dir/scripts/gen.sh" '[[ "${1:-}" == "--check" ]] || exit 2'
printf 'scripts/gen.sh\tagents/out.md\r\n' >"$dir/scripts/generators.tsv"
commit_fixture "$dir" scripts/generators.tsv agents/out.md
assert_walker_failure_contains "crlf rejection" "$dir" "CRLF"

# q. Non-root cwd invocation.
dir="$(setup_single_valid_fixture non-root-cwd)"
(
  cd "$dir/subdir"
  if HOME="$dir/home" GIT_CONFIG_GLOBAL="$dir/gitconfig" bash "$dir/scripts/check-generators.sh" >"$dir/stdout.txt" 2>"$dir/stderr.txt"; then
    pass_case
  else
    fail_case "non-root cwd: expected success; stderr: $(cat "$dir/stderr.txt")"
  fi
)

# CLI usage.
dir="$(setup_single_valid_fixture usage)"
if run_walker "$dir" --unknown >"$dir/stdout.txt" 2>"$dir/stderr.txt"; then
  fail_case "unknown args: expected failure"
else
  pass_case
  assert_contains "unknown args usage" "Usage:" "$(cat "$dir/stderr.txt")"
fi

# r. Not inside a git work tree.
dir="$(new_fixture not-in-git)"
printf 'generated\n' >"$dir/agents/out.md"
write_generator "$dir/scripts/gen.sh" '[[ "${1:-}" == "--check" ]] || exit 2'
printf 'scripts/gen.sh\tagents/out.md\n' >"$dir/scripts/generators.tsv"
# Deliberately do NOT init git here.
err="$dir/stderr.txt"
if run_walker "$dir" >"$dir/stdout.txt" 2>"$err"; then
  fail_case "not in git work tree: expected failure"
else
  pass_case
  assert_contains "not in git work tree" "not inside a git work tree" "$(cat "$err")"
fi

# s. Registry not found.
dir="$(new_fixture no-registry)"
mkdir -p "$dir/home"
(
  cd "$dir"
  HOME="$dir/home" GIT_CONFIG_GLOBAL="$dir/gitconfig" git init -q
)
err="$dir/stderr.txt"
if run_walker "$dir" >"$dir/stdout.txt" 2>"$err"; then
  fail_case "missing registry: expected failure"
else
  pass_case
  assert_contains "missing registry" "registry not found" "$(cat "$err")"
fi

if [[ "$FAIL" -ne 0 ]]; then
  printf 'FAIL: test-check-generators.sh - %s failed, %s passed\n' "$FAIL" "$PASS" >&2
  printf '  %s\n' "${FAIL_DETAILS[@]}" >&2
  exit 1
fi

printf 'PASS: test-check-generators.sh - %s assertions passed\n' "$PASS"
