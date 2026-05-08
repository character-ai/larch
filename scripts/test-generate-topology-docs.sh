#!/usr/bin/env bash
# Regression test for scripts/generate-topology-docs.sh.

set -euo pipefail
export LC_ALL=C

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SUBJECT="$REPO_ROOT/scripts/generate-topology-docs.sh"

PASS=0
FAIL=0
FAIL_DETAILS=()
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/larch-generate-topology-docs.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT

pass_case() {
  PASS=$((PASS + 1))
}

fail_case() {
  FAIL=$((FAIL + 1))
  FAIL_DETAILS+=("$1")
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

run_generator() {
  local tsv="$1"
  local doc="$2"
  shift 2
  (
    cd "$REPO_ROOT"
    LARCH_TOPOLOGY_TSV="$tsv" LARCH_TOPOLOGY_DOC="$doc" bash "$SUBJECT" "$@"
  )
}

assert_success() {
  local label="$1"
  local tsv="$2"
  local doc="$3"
  shift 3
  if run_generator "$tsv" "$doc" "$@" >"$TMP_ROOT/stdout.txt" 2>"$TMP_ROOT/stderr.txt"; then
    pass_case
  else
    fail_case "$label: expected success; stderr: $(cat "$TMP_ROOT/stderr.txt")"
  fi
}

assert_failure_contains() {
  local label="$1"
  local tsv="$2"
  local doc="$3"
  local needle="$4"
  shift 4
  if run_generator "$tsv" "$doc" "$@" >"$TMP_ROOT/stdout.txt" 2>"$TMP_ROOT/stderr.txt"; then
    fail_case "$label: expected failure"
    return
  fi
  assert_contains "$label" "$needle" "$(cat "$TMP_ROOT/stderr.txt")"
}

BASE_TSV="$REPO_ROOT/skills/shared/topology.tsv"

# a. Round-trip write + check against the committed TSV.
doc="$TMP_ROOT/topology.md"
assert_success "write mode" "$BASE_TSV" "$doc"
assert_success "check mode" "$BASE_TSV" "$doc" --check
assert_contains "rendered regular anchor" 'id="design.sketch.regular_slots"' "$(cat "$doc")"

# b. Drift detection.
printf '\nmanual drift\n' >>"$doc"
assert_failure_contains "drift detection" "$BASE_TSV" "$doc" "out of sync" --check

# c-f. Bad TSV grammar and key/value validation.
bad="$TMP_ROOT/bad.tsv"
printf 'design.sketch.regular_slots\t8\tskills/design/references/sketch-launch.md\n' >"$bad"
assert_failure_contains "missing column" "$bad" "$TMP_ROOT/missing-column.md" "malformed row" --check

printf 'design.sketch.regular_slots\t4\t2 Cursor + 2 Codex\tskills/design/references/sketch-launch.md\textra\n' >"$bad"
assert_failure_contains "extra column" "$bad" "$TMP_ROOT/extra-column.md" "malformed row" --check

printf 'design:sketch\t4\t2 Cursor + 2 Codex\tskills/design/references/sketch-launch.md\n' >"$bad"
assert_failure_contains "colon in key" "$bad" "$TMP_ROOT/colon-key.md" "key must not contain colon" --check

printf 'design.sketch.regular_slots\t<4>\t2 Cursor + 2 Codex\tskills/design/references/sketch-launch.md\n' >"$bad"
assert_failure_contains "forbidden value char" "$bad" "$TMP_ROOT/forbidden-value.md" "forbidden character" --check

# g-h. Runtime authority validation.
printf 'docs.readme.bad\tVALUENOTPRESENT\t\tdocs/skills.md\n' >"$bad"
assert_failure_contains "stale authority value" "$bad" "$TMP_ROOT/stale-authority.md" "not found in runtime_authority" --check

printf 'docs.missing.bad\t4 regular\t\tdocs/missing-topology-authority.md\n' >"$bad"
assert_failure_contains "missing authority" "$bad" "$TMP_ROOT/missing-authority.md" "runtime_authority not found" --check

# i. CRLF line endings rejected.
crlf="$TMP_ROOT/crlf.tsv"
printf 'design.sketch.regular_slots\t4 regular\t2 Cursor + 2 Codex\tskills/design/references/sketch-launch.md\r\n' >"$crlf"
assert_failure_contains "CRLF line ending" "$crlf" "$TMP_ROOT/crlf.md" "CRLF line endings not allowed" --check

# j. Duplicate key rejected.
dupkey="$TMP_ROOT/dup-key.tsv"
{
  printf 'design.sketch.regular_slots\t4 regular\t2 Cursor + 2 Codex\tskills/design/references/sketch-launch.md\n'
  printf 'design.sketch.regular_slots\tnot a duplicate\tsame key as row 1\tskills/design/references/sketch-launch.md\n'
} >"$dupkey"
assert_failure_contains "duplicate key" "$dupkey" "$TMP_ROOT/dup-key.md" "duplicate key" --check

# k. Short or purely-numeric values rejected (anchor-phrase requirement).
shortval="$TMP_ROOT/short-value.tsv"
printf 'design.sketch.regular_slots\t4\t2 Cursor + 2 Codex\tskills/design/references/sketch-launch.md\n' >"$shortval"
assert_failure_contains "purely numeric value" "$shortval" "$TMP_ROOT/short-value.md" "too short or purely numeric" --check

# l. Empty composition row generates correctly (regression for IFS=tab field-collapse bug — empty
# composition column must NOT shift runtime_authority into the composition slot). Uses a tracked
# repo file as the runtime_authority and a value-phrase that grep-pins inside it.
empty_comp="$TMP_ROOT/empty-comp.tsv"
printf 'docs.empty.composition\tAUTO-GENERATED\t\tdocs/topology.md\n' >"$empty_comp"
empty_comp_doc="$TMP_ROOT/empty-comp.md"
assert_success "empty composition row" "$empty_comp" "$empty_comp_doc"
# Authority must be in last column of the rendered table row (would be wrong if IFS collapsed).
# shellcheck disable=SC2016
assert_contains "empty composition keeps authority in last column" '`docs/topology.md` |' "$(cat "$empty_comp_doc")"

# m. Anchor-collision detection (defense-in-depth: keys that map to the same anchor must fail).
# With verbatim-key anchors, the duplicate-key check above already catches collisions for identical
# keys; this test exercises the anchor map by providing two distinct keys whose verbatim anchors
# would still collide if the encoding ever regressed. Skipped here because verbatim encoding is
# trivially injective; the duplicate-key test (j) is the primary guard.

if [[ "$FAIL" -ne 0 ]]; then
  printf 'FAIL: %s case(s) failed\n' "$FAIL" >&2
  printf ' - %s\n' "${FAIL_DETAILS[@]}" >&2
  exit 1
fi

printf 'PASS: %s assertions\n' "$PASS"
