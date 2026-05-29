#!/usr/bin/env bash
# Combined offline harness for lib-plan-optional-trailers unit scripts.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
# shellcheck source=skills/design/scripts/lib-plan-optional-trailers.sh
source "$SCRIPT_DIR/lib-plan-optional-trailers.sh"

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

TMPROOT=$(mktemp -d "${TMPDIR:-/tmp}/larch-trailer-helpers-test.XXXXXX")
trap 'rm -rf "$TMPROOT"' EXIT

d="$TMPROOT/has-any"
mkdir -p "$d"
printf 'body\ndiff_added: 1\ndiff_lines: 2\n' >"$d/plan.txt"
"$SCRIPT_DIR/test-trailer-has-any.sh" "$d/plan.txt" | grep -q 'has_any=yes' \
    || fail "test-trailer-has-any should detect diff_added"

d="$TMPROOT/validate"
mkdir -p "$d"
printf 'body\ndiff_added: 1\ndiff_lines: 2\n' >"$d/plan.txt"
snapshot_optional_trailer_keys "$d/plan.txt" "$d/keys"
"$SCRIPT_DIR/test-trailer-validate.sh" "$d/plan.txt" "$d/keys" | grep -q 'validate=ok' \
    || fail "test-trailer-validate should accept preserved trailers"
printf 'body\ndiff_lines: 2\n' >"$d/plan.txt"
set +e
out=$("$SCRIPT_DIR/test-trailer-validate.sh" "$d/plan.txt" "$d/keys" 2>&1)
rc=$?
set -e
if [[ "$rc" != 1 ]] || ! printf '%s\n' "$out" | grep -q 'validate=fail'; then
  fail "test-trailer-validate should reject lost keys"
fi

d="$TMPROOT/dedup"
mkdir -p "$d"
printf 'body\nbody\ndiff_added: 5\ndiff_lines: 10\n' >"$d/plan.txt"
snapshot_optional_trailer_keys "$d/plan.txt" "$d/.gate-b-optional-trailer-keys"
"$SCRIPT_DIR/test-trailer-dedup.sh" "$d" | grep -q 'dedup=ok' \
    || fail "test-trailer-dedup should succeed when trailers preserved"

echo "PASS: test-trailer-helpers.sh"
