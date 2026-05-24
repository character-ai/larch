#!/usr/bin/env bash
# test-scout-plan-archetypes-wrapper.sh — regression harness for scout-plan-archetypes-wrapper.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
WRAPPER="$REPO_ROOT/skills/design/scripts/scout-plan-archetypes-wrapper.sh"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-scout-plan-wrapper.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

[[ -x "$WRAPPER" ]] || fail "wrapper not executable"

BIN="$TMP/bin"
mkdir -p "$BIN"
cat > "$BIN/scout-dynamic-archetypes.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
if [[ -n "${SCOUT_STUB_ARGV_LOG:-}" ]]; then
    printf '%q ' "$@" >>"$SCOUT_STUB_ARGV_LOG"
    printf '\n' >>"$SCOUT_STUB_ARGV_LOG"
fi
out=""
plan=""
desc=""
scope=""
max=""
session=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) out="${2:?}"; shift 2 ;;
        --plan-file) plan="${2:?}"; shift 2 ;;
        --description-file) desc="${2:?}"; shift 2 ;;
        --scope-files) scope="${2:?}"; shift 2 ;;
        --max-archetypes) max="${2:?}"; shift 2 ;;
        --session-env-path) session="${2:?}"; shift 2 ;;
        --mode|--timeout) shift 2 ;;
        --prompt-override-file) shift 2 ;;
        *) shift 1 ;;
    esac
done
[[ -n "$out" && -n "$scope" ]] || exit 2
[[ -f "${SCOUT_STUB_MANIFEST:-}" ]] || exit 2
cp "${SCOUT_STUB_MANIFEST}" "$out"
printf 'SCOUT_STATUS=ok\nSCOUT_OUTPUT=%s\nSCOUT_ARCHETYPE_COUNT=%s\n' "$out" "$(jq '.archetypes | length' "$out")"
STUB
chmod +x "$BIN/scout-dynamic-archetypes.sh"

setup_design_dir() {
    local d="$1"
    mkdir -p "$d"
    printf 'feature\n' >"$d/feature-description.txt"
    printf 'source\n' >"$d/source-env.sh"
}

echo "=== scope-files from plan with three backtick paths ==="
D1="$TMP/d1"
setup_design_dir "$D1"
cat >"$D1/plan.txt" <<'PLAN'
## Files to modify

### NEW: `skills/a.sh`
### UPDATED: `skills/b.sh`
### REWRITTEN: `skills/c.sh`
PLAN
export SCOUT_PLAN_ARCHETYPES_SCOUT_SH="$BIN/scout-dynamic-archetypes.sh"
export CLAUDE_PLUGIN_ROOT="$REPO_ROOT"
export SCOUT_STUB_MANIFEST="$TMP/m3.json"
export SCOUT_STUB_ARGV_LOG="$D1/argv.log"
: >"$SCOUT_STUB_ARGV_LOG"
cat >"$SCOUT_STUB_MANIFEST" <<'JSON'
{"archetypes":[{"name":"x","focus_area":"correctness","weight":1,"rationale":"r","prompt_body":"p"}]}
JSON
"$WRAPPER" \
    --plan-file "$D1/plan.txt" \
    --description-file "$D1/feature-description.txt" \
    --output "$D1/scout-plan-manifest.json" \
    --max-archetypes 6 \
    --session-env-path "$D1/source-env.sh" >"$D1/out.env"
grep -Fq 'SCOUT_STATUS=ok' "$D1/out.env" || fail "d1 status"
grep -Fq 'SCOUT_ARCHETYPE_COUNT=1' "$D1/out.env" || fail "d1 count"
[[ -f "$D1/scout-plan-scope-files.txt" ]] || fail "scope file missing"
[[ "$(wc -l <"$D1/scout-plan-scope-files.txt" | tr -d ' ')" == "3" ]] || fail "expected 3 scope lines"
grep -Fq -- '--scope-files' "$D1/argv.log" || fail "scope-files not passed"
grep -Fq -- '--prompt-override-file' "$D1/argv.log" || fail "prompt override not passed"

echo "=== scope stub when no parseable paths ==="
D0="$TMP/d0"
setup_design_dir "$D0"
printf 'no headings here\n' >"$D0/plan.txt"
export SCOUT_STUB_MANIFEST="$TMP/m0.json"
unset SCOUT_STUB_ARGV_LOG || true
printf '{"archetypes":[]}\n' >"$SCOUT_STUB_MANIFEST"
"$WRAPPER" \
    --plan-file "$D0/plan.txt" \
    --description-file "$D0/feature-description.txt" \
    --output "$D0/scout-plan-manifest.json" \
    --max-archetypes 6 \
    --session-env-path "$D0/source-env.sh" >/dev/null
grep -Fxq 'skills/design/SKILL.md' "$D0/scout-plan-scope-files.txt" || fail "stub scope line"

echo "=== cap 6 post-filter (stub returns 8) ==="
D8="$TMP/d8"
setup_design_dir "$D8"
# shellcheck disable=SC2016 # backticks are literal plan markdown, not command substitution
printf '### NEW: `%s`\n' 'x' >"$D8/plan.txt"
export SCOUT_STUB_MANIFEST="$TMP/m8.json"
unset SCOUT_STUB_ARGV_LOG || true
jq -n '{archetypes: [range(0;8) | . as $i | {name: ("a-" + ($i|tostring)), focus_area:"correctness", weight:1, rationale:"r", prompt_body:"p"}]}' >"$TMP/m8.json"
"$WRAPPER" \
    --plan-file "$D8/plan.txt" \
    --description-file "$D8/feature-description.txt" \
    --output "$D8/out.json" \
    --max-archetypes 6 \
    --session-env-path "$D8/source-env.sh" | tee "$D8/out.env"
grep -Fq 'WARN=scout-plan-archetypes-wrapper:' "$D8/out.env" || fail "expected truncate WARN KV"
[[ "$(jq '.archetypes | length' "$D8/out.json")" == "6" ]] || fail "expected 6 after cap"

echo "=== reserved slug dropped ==="
DR="$TMP/dr"
setup_design_dir "$DR"
# shellcheck disable=SC2016 # backticks are literal plan markdown, not command substitution
printf '### NEW: `%s`\n' 'z' >"$DR/plan.txt"
export SCOUT_STUB_MANIFEST="$TMP/mr.json"
unset SCOUT_STUB_ARGV_LOG || true
cat >"$TMP/mr.json" <<'JSON'
{"archetypes":[
  {"name":"arch","focus_area":"correctness","weight":1,"rationale":"r","prompt_body":"p"},
  {"name":"api-z","focus_area":"correctness","weight":1,"rationale":"r","prompt_body":"p"}
]}
JSON
"$WRAPPER" \
    --plan-file "$DR/plan.txt" \
    --description-file "$DR/feature-description.txt" \
    --output "$DR/out.json" \
    --max-archetypes 6 \
    --session-env-path "$DR/source-env.sh" | tee "$DR/out.env"
grep -Fq 'WARN=scout-plan-archetypes-wrapper:' "$DR/out.env" || fail "reserved WARN KV"
[[ "$(jq -r '.archetypes[0].name' "$DR/out.json")" == "api-z" ]] || fail "expected api-z only"

echo "=== malformed ###NEW: (no whitespace after ###) ignored for scope paths ==="
DM="$TMP/dm"
setup_design_dir "$DM"
cat >"$DM/plan.txt" <<'PLAN'
###NEW: `ignored.md`
### NEW: `skills/kept.sh`
PLAN
export SCOUT_STUB_MANIFEST="$TMP/mm.json"
unset SCOUT_STUB_ARGV_LOG || true
cat >"$TMP/mm.json" <<'JSON'
{"archetypes":[{"name":"scope-check","focus_area":"correctness","weight":1,"rationale":"r","prompt_body":"p"}]}
JSON
"$WRAPPER" \
    --plan-file "$DM/plan.txt" \
    --description-file "$DM/feature-description.txt" \
    --output "$DM/scout-plan-manifest.json" \
    --max-archetypes 6 \
    --session-env-path "$DM/source-env.sh" >/dev/null
[[ "$(wc -l <"$DM/scout-plan-scope-files.txt" | tr -d ' ')" == "1" ]] || fail "expected one scope line"
grep -Fxq 'skills/kept.sh' "$DM/scout-plan-scope-files.txt" || fail "malformed heading must not populate scope"
! grep -Fq 'ignored.md' "$DM/scout-plan-scope-files.txt" || fail "concatenated ###NEW must not yield ignored.md"

echo "All scout-plan-archetypes-wrapper harness assertions passed."
