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
contains "$out" '- **Description**: Fix docs for manifest OOS.' "description field missing"
contains "$out" '- **Reviewer**: External implementer' "reviewer attribution missing"
contains "$out" '- **Vote tally**: N/A — auto-filed per policy' "vote tally attribution missing"
"$HELPER" --manifest-path "$manifest" --implement-tmpdir "$tmp"
[ "$(grep -c '^### OOS_' "$out")" = "1" ] || fail "duplicate-title rerun must be idempotent"
rm -rf "$tmp"

tmp=$(mktemp -d "${TMPDIR:-/tmp}/materialize-manifest-oos.XXXXXX")
manifest="$tmp/manifest.json"
cat >"$manifest" <<'JSON'
{"schema_version":"1","status":"complete","oos_observations":[{"title":"Counted","description":"x","phase":"implement","focus_area":"correctness"}]}
JSON
[ "$("$HELPER" --count-only --manifest-path "$manifest" --implement-tmpdir "$tmp")" = "1" ] || fail "count-only must report manifest OOS length"
"$HELPER" --manifest-path "$manifest" --implement-tmpdir "$tmp"
contains "$tmp/oos-accepted-main-agent.md" '- **focus-area**: correctness' "structured public focus-area missing"
rm -rf "$tmp"

tmp=$(mktemp -d "${TMPDIR:-/tmp}/materialize-manifest-oos.XXXXXX")
manifest="$tmp/manifest.json"
cat >"$manifest" <<'JSON'
{"schema_version":"1","status":"complete","oos_observations":"bad"}
JSON
set +e
"$HELPER" --count-only --manifest-path "$manifest" --implement-tmpdir "$tmp" >/dev/null 2>"$tmp/count.err"
rc=$?
set -e
[ "$rc" -ne 0 ] || fail "count-only must fail closed on invalid oos_observations type"
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
contains "$tmp/security-oos-observations.md" '### Security OOS: Security hardening' "security audit title missing"
contains "$tmp/security-oos-observations.md" '- **Description**: - **focus-area**: security-hardening' "security audit description missing"
contains "$tmp/execution-issues.md" 'security-routed manifest OOS retained in security-oos-observations.md' "security breadcrumb missing"
not_contains "$tmp/execution-issues.md" 'Security hardening' "security breadcrumb must not expose title"
"$HELPER" --manifest-path "$manifest" --implement-tmpdir "$tmp"
[ "$(grep -c '^### Security OOS: Security hardening' "$tmp/security-oos-observations.md")" = "1" ] || fail "security audit rerun must be idempotent"
[ "$(grep -c '^### Warnings' "$tmp/execution-issues.md")" = "1" ] || fail "security warnings must upsert one category header"
rm -rf "$tmp"

tmp=$(mktemp -d "${TMPDIR:-/tmp}/materialize-manifest-oos.XXXXXX")
manifest="$tmp/manifest.json"
cat >"$manifest" <<'JSON'
{
  "schema_version": "1",
  "status": "complete",
  "oos_observations": [
    {"title":"Security title only","description":"Retain private body.","phase":"review"},
    {"title":"Structured marker","description":"Retain structured body.","phase":"implement","focus_area":"security-privacy"}
  ]
}
JSON
"$HELPER" --manifest-path "$manifest" --implement-tmpdir "$tmp"
out="$tmp/oos-accepted-main-agent.md"
contains "$out" '### OOS_1: Security title only' "security title alone must remain public-routed"
not_contains "$out" 'Structured marker' "structured security marker must be excluded"
not_contains "$tmp/security-oos-observations.md" 'Security title only' "security title alone must not be security-routed"
contains "$tmp/security-oos-observations.md" '- **focus-area**: security-privacy' "structured focus-area missing from audit"
rm -rf "$tmp"

tmp=$(mktemp -d "${TMPDIR:-/tmp}/materialize-manifest-oos.XXXXXX")
manifest="$tmp/manifest.json"
cat >"$manifest" <<'JSON'
{"schema_version":"1","status":"complete","oos_observations":[{"title":"Needs scrub","description":"token text"}]}
JSON
set +e
CLAUDE_PLUGIN_ROOT="$tmp/missing-plugin-root" "$HELPER" --manifest-path "$manifest" --implement-tmpdir "$tmp" >/dev/null 2>"$tmp/missing-redactor.err"
rc=$?
set -e
[ "$rc" -ne 0 ] || fail "missing redact-secrets.sh with observations must fail closed"
contains "$tmp/missing-redactor.err" 'redact-secrets.sh missing or not executable' "missing redactor error missing"
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
