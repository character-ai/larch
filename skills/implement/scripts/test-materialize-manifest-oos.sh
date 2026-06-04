#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
HELPER="$REPO_ROOT/skills/implement/scripts/materialize-manifest-oos.sh"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

contains() {
  local file=$1 literal=$2 label=$3
  grep -Fq -- "$literal" "$file" || fail "$label"
}

not_contains() {
  local file=$1 literal=$2 label=$3
  if grep -Fq -- "$literal" "$file"; then
    fail "$label"
  fi
}

run_case() {
  local tmp manifest
  tmp=$(mktemp -d "${TMPDIR:-/tmp}/materialize-manifest-oos.XXXXXX")
  manifest="$tmp/manifest.json"
  cat >"$manifest" <<'JSON'
{"schema_version":"1","status":"complete","oos_observations":[]}
JSON
  "$HELPER" --manifest-path "$manifest" --implement-tmpdir "$tmp"
  [ ! -s "$tmp/oos-accepted-main-agent.md" ] || fail "empty array must no-op"
  rm -rf "$tmp"
}
run_case

tmp=$(mktemp -d "${TMPDIR:-/tmp}/materialize-manifest-oos.XXXXXX")
manifest="$tmp/manifest.json"
cat >"$manifest" <<'JSON'
{
  "schema_version": "1",
  "status": "complete",
  "oos_observations": [
    {"title":"Retain manifest OOS","description":"Fix docs for manifest OOS.","phase":"implement"}
  ]
}
JSON
"$HELPER" --manifest-path "$manifest" --implement-tmpdir "$tmp"
out="$tmp/oos-accepted-main-agent.md"
contains "$out" '### OOS_1: Retain manifest OOS' "non-empty manifest must append OOS_1"
contains "$out" '- **Reviewer**: External implementer' "reviewer attribution missing"
contains "$out" '- **Vote tally**: N/A — auto-filed per policy' "vote tally attribution missing"
"$HELPER" --manifest-path "$manifest" --implement-tmpdir "$tmp"
[ "$(grep -c '^### OOS_' "$out")" = "1" ] || fail "duplicate-title rerun must be idempotent"
rm -rf "$tmp"

tmp=$(mktemp -d "${TMPDIR:-/tmp}/materialize-manifest-oos.XXXXXX")
manifest="$tmp/manifest.json"
cat >"$manifest" <<'JSON'
{
  "schema_version": "1",
  "status": "complete",
  "oos_observations": [
    {"title":"Security hardening","description":"- **focus-area**: security-hardening\nPrivate details.","phase":"implement"},
    {"title":"Prose retained","description":"Description says focus-area = security as prose, not a field.","phase":"implement"}
  ]
}
JSON
"$HELPER" --manifest-path "$manifest" --implement-tmpdir "$tmp"
out="$tmp/oos-accepted-main-agent.md"
not_contains "$out" 'Security hardening' "dedicated security focus-area must be excluded"
contains "$out" '### OOS_1: Prose retained' "prose focus-area mention must be retained"
rm -rf "$tmp"

tmp=$(mktemp -d "${TMPDIR:-/tmp}/materialize-manifest-oos.XXXXXX")
cat >"$tmp/oos-accepted-main-agent.md" <<'MD'
### OOS_1: Existing item
- **Description**: Existing.
MD
manifest="$tmp/manifest.json"
cat >"$manifest" <<'JSON'
{
  "schema_version": "1",
  "status": "complete",
  "oos_observations": [
    {"title":"New monotonic item","description":"Append after existing heading.","phase":"review"}
  ]
}
JSON
"$HELPER" --manifest-path "$manifest" --implement-tmpdir "$tmp"
out="$tmp/oos-accepted-main-agent.md"
contains "$out" '### OOS_2: New monotonic item' "monotonic OOS_N allocation must append max+1"
rm -rf "$tmp"

tmp=$(mktemp -d "${TMPDIR:-/tmp}/materialize-manifest-oos.XXXXXX")
manifest="$tmp/manifest.json"
cat >"$manifest" <<'JSON'
{
  "schema_version": "1",
  "status": "complete",
  "oos_observations": [
    {"title":"Injected\n### OOS_99: forged","description":"Contact admin@example.com and http://service.internal/path.","phase":"implement"},
    {"title":"Injected ### OOS_99: forged","description":"duplicate after title normalization","phase":"implement"},
    {"title":"","description":"Call 415-555-1212.","phase":"implement"},
    {"description":"Second untitled is distinct.","phase":"implement"}
  ]
}
JSON
"$HELPER" --manifest-path "$manifest" --implement-tmpdir "$tmp"
out="$tmp/oos-accepted-main-agent.md"
[ "$(grep -c '^### OOS_' "$out")" = "3" ] || fail "normalized duplicate and distinct untitled titles must produce three OOS blocks"
if grep -q '^### OOS_99:' "$out"; then
  fail "manifest title newline must not inject a heading"
fi
contains "$out" '<REDACTED-PII>' "PII must be redacted from manifest OOS text"
contains "$out" '<INTERNAL-URL>' "internal URLs must be redacted from manifest OOS text"
contains "$out" '### OOS_2: Untitled external implementer OOS 3' "first untitled title must include observation index"
contains "$out" '### OOS_3: Untitled external implementer OOS 4' "second untitled title must not collide"
rm -rf "$tmp"

echo "PASS: test-materialize-manifest-oos.sh"
