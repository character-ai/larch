#!/usr/bin/env bash
# Regression coverage for /design artifact manifest writer and reader.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
WRITER="$SCRIPT_DIR/write-design-manifest.sh"
READER="$SCRIPT_DIR/read-design-manifest.sh"

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

TMPROOT=$(mktemp -d "${TMPDIR:-/tmp}/larch-design-manifest-test.XXXXXX")
trap 'rm -rf "$TMPROOT"' EXIT

make_design_tree() {
    local dir="$1"
    mkdir -p "$dir"
    printf '# Plan\n\nDo the work.\n' > "$dir/plan.txt"
    printf '# Tally\n\nReviewer | Score\n' > "$dir/voting-tally.md"
    printf 'NO_CONTESTED_DECISIONS\n' > "$dir/contested-decisions.md"
    : > "$dir/oos.md"
    : > "$dir/rejected-findings.md"
    : > "$dir/accepted-plan-findings.md"
    # shellcheck disable=SC2016 # literal markdown fence fixture
    printf '```mermaid\ngraph TD\n```\n' > "$dir/architecture-diagram.md"
}

DESIGN="$TMPROOT/design"
IMPLEMENT="$TMPROOT/implement"
make_design_tree "$DESIGN"
mkdir -p "$IMPLEMENT"

"$WRITER" --design-tmpdir "$DESIGN" --implement-tmpdir "$IMPLEMENT" >/dev/null
[[ -f "$IMPLEMENT/design-export/manifest.env" ]] || fail "writer did not create manifest"
[[ ! -f "$IMPLEMENT/design-export/manifest.env.tmp" ]] || fail "writer left fixed tmp file"

out=$("$READER" --implement-tmpdir "$IMPLEMENT")
printf '%s\n' "$out" | grep -q '^MANIFEST_OK=true$' || fail "reader did not accept valid manifest"
IMPLEMENT_CANON=$(cd -P "$IMPLEMENT" && pwd -P)
printf '%s\n' "$out" | grep -q "^PLAN_FILE=$IMPLEMENT_CANON/design-export/plan.txt$" || fail "reader did not emit normalized plan path"

DESIGN_MISSING="$TMPROOT/design-missing"
IMPLEMENT_MISSING="$TMPROOT/implement-missing"
make_design_tree "$DESIGN_MISSING"
rm "$DESIGN_MISSING/plan.txt"
mkdir -p "$IMPLEMENT_MISSING"
if "$WRITER" --design-tmpdir "$DESIGN_MISSING" --implement-tmpdir "$IMPLEMENT_MISSING" >/dev/null 2>&1; then
    fail "writer accepted missing required plan"
fi
[[ ! -f "$IMPLEMENT_MISSING/design-export/manifest.env" ]] || fail "writer left manifest after failed write"

BASE_EXPORT="$TMPROOT/manual/design-export"
mkdir -p "$BASE_EXPORT"
printf '# Plan\n' > "$BASE_EXPORT/plan.txt"
printf '# Tally\n' > "$BASE_EXPORT/voting-tally.md"
: > "$BASE_EXPORT/contested-decisions.md"
: > "$BASE_EXPORT/oos.md"
: > "$BASE_EXPORT/rejected-findings.md"
: > "$BASE_EXPORT/accepted-plan-findings.md"

write_manifest() {
    local file="$BASE_EXPORT/manifest.env"
    {
        printf 'MANIFEST_VERSION=1\n'
        printf 'PLAN_FILE=%s/plan.txt\n' "$BASE_EXPORT"
        printf 'PLAN_REVIEW_TALLY_FILE=%s/voting-tally.md\n' "$BASE_EXPORT"
        printf 'CONTESTED_CRITERIA_FILE=%s/contested-decisions.md\n' "$BASE_EXPORT"
        printf 'OOS_FILE=%s/oos.md\n' "$BASE_EXPORT"
        printf 'REJECTED_FINDINGS_FILE=%s/rejected-findings.md\n' "$BASE_EXPORT"
        printf 'ACCEPTED_PLAN_FINDINGS_FILE=%s/accepted-plan-findings.md\n' "$BASE_EXPORT"
        printf 'TIMESTAMP=2026-01-01T00:00:00Z\n'
        printf 'SESSION_ID=test-session\n'
    } > "$file"
}

write_manifest
out=$("$READER" --implement-tmpdir "$TMPROOT/manual")
printf '%s\n' "$out" | grep -q '^MANIFEST_OK=true$' || fail "manual valid manifest rejected"

cp "$BASE_EXPORT/manifest.env" "$BASE_EXPORT/manifest.good"
printf 'bad-key=value\n' >> "$BASE_EXPORT/manifest.env"
out=$("$READER" --implement-tmpdir "$TMPROOT/manual")
printf '%s\n' "$out" | grep -q '^ERROR=invalid-key$' || fail "malformed key was not rejected"

cp "$BASE_EXPORT/manifest.good" "$BASE_EXPORT/manifest.env"
# shellcheck disable=SC2016 # literal shell-shaped payload; reader must not eval it
printf 'INJECT=$(echo sourced)\n' >> "$BASE_EXPORT/manifest.env"
out=$("$READER" --implement-tmpdir "$TMPROOT/manual")
printf '%s\n' "$out" | grep -q '^MANIFEST_OK=true$' || fail "safe unknown key with shell syntax should be treated as inert data"

cp "$BASE_EXPORT/manifest.good" "$BASE_EXPORT/manifest.env"
sed "s#PLAN_FILE=.*#PLAN_FILE=$TMPROOT/outside.txt#" "$BASE_EXPORT/manifest.good" > "$BASE_EXPORT/manifest.env"
printf '# Outside\n' > "$TMPROOT/outside.txt"
out=$("$READER" --implement-tmpdir "$TMPROOT/manual")
printf '%s\n' "$out" | grep -q '^ERROR=path-escaped-export-dir$' || fail "path traversal outside export dir was not rejected"

cp "$BASE_EXPORT/manifest.good" "$BASE_EXPORT/manifest.env"
ln -sf "$BASE_EXPORT/plan.txt" "$BASE_EXPORT/plan-link.txt"
sed "s#PLAN_FILE=.*#PLAN_FILE=$BASE_EXPORT/plan-link.txt#" "$BASE_EXPORT/manifest.good" > "$BASE_EXPORT/manifest.env"
out=$("$READER" --implement-tmpdir "$TMPROOT/manual")
printf '%s\n' "$out" | grep -q '^ERROR=symlink-rejected$' || fail "symlink path was not rejected"

cp "$BASE_EXPORT/manifest.good" "$BASE_EXPORT/manifest.env"
printf 'SESSION_ID=bad\001value\n' >> "$BASE_EXPORT/manifest.env"
out=$("$READER" --implement-tmpdir "$TMPROOT/manual")
printf '%s\n' "$out" | grep -q '^ERROR=control-char$' || fail "control character was not rejected"

echo "PASS: test-design-manifest.sh"
