#!/usr/bin/env bash
# Regression harness for scout-dynamic-archetypes.sh.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
SCRIPT="$REPO_ROOT/scripts/scout-dynamic-archetypes.sh"
export CLAUDE_PLUGIN_ROOT="$REPO_ROOT"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-scout-dynamic-archetypes.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

BIN="$TMP/bin"
mkdir -p "$BIN"
REAL_JQ=$(command -v jq)
export REAL_JQ
cat > "$BIN/claude" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
cat >/dev/null
if [[ "${SCOUT_STUB_FAIL:-false}" == "true" ]]; then
    exit 17
fi
cat "${SCOUT_STUB_OUTPUT_FILE:?SCOUT_STUB_OUTPUT_FILE required}"
STUB
chmod +x "$BIN/claude"
cat > "$BIN/jq" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${SCOUT_STUB_JQ_FAIL_MODE:-}" == "validation" && "${1:-}" == "-c" && "${2:-}" == "--argjson" ]]; then
    printf 'stubbed validation jq failure\n' >&2
    exit 9
fi
exec "${REAL_JQ:?REAL_JQ required}" "$@"
STUB
chmod +x "$BIN/jq"

diff_file="$TMP/review.diff"
scope_file="$TMP/scope-files.txt"
plan_file="$TMP/plan.md"
printf 'diff --git a/scripts/foo.sh b/scripts/foo.sh\n' > "$diff_file"
printf 'scripts/foo.sh\n' > "$scope_file"
printf '# plan\n' > "$plan_file"

seed_case_inputs() {
    local out_dir="$1"
    cp "$diff_file" "$out_dir/review.diff"
    cp "$scope_file" "$out_dir/scope-files.txt"
    cp "$plan_file" "$out_dir/plan.md"
}

run_case() {
    local label="$1" fixture="$2" out_dir output stdout_file
    out_dir="$TMP/$label"
    mkdir -p "$out_dir"
    seed_case_inputs "$out_dir"
    output="$out_dir/scout-manifest.json"
    stdout_file="$out_dir/stdout.env"
    PATH="$BIN:$PATH" SCOUT_STUB_OUTPUT_FILE="$fixture" "$SCRIPT" \
        --mode diff \
        --diff-file "$out_dir/review.diff" \
        --plan-file "$out_dir/plan.md" \
        --max-archetypes 4 \
        --output "$output" \
        --timeout 5 \
        > "$stdout_file"
    printf '%s\n' "$stdout_file"
}

run_case_description() {
    local label="$1" fixture="$2" description_text="$3" out_dir output stdout_file
    out_dir="$TMP/$label"
    mkdir -p "$out_dir"
    seed_case_inputs "$out_dir"
    output="$out_dir/scout-manifest.json"
    stdout_file="$out_dir/stdout.env"
    PATH="$BIN:$PATH" SCOUT_STUB_OUTPUT_FILE="$fixture" "$SCRIPT" \
        --mode description \
        --scope-files "$out_dir/scope-files.txt" \
        --description-text "$description_text" \
        --plan-file "$out_dir/plan.md" \
        --max-archetypes 4 \
        --output "$output" \
        --timeout 5 \
        > "$stdout_file"
    printf '%s\n' "$stdout_file"
}

assert_raw_matches() {
    local label="$1" fixture="$2"
    local raw_file="$TMP/$label/scout-manifest.json.raw"
    [[ -f "$raw_file" ]] || fail "$label raw sidecar missing"
    cmp -s "$fixture" "$raw_file" || fail "$label raw sidecar mismatch"
}

cat > "$TMP/valid4.json" <<'JSON'
{"archetypes":[
  {"name":"api-contract","focus_area":"correctness","weight":4,"rationale":"API changes are central.","prompt_body":"Check API contract compatibility."},
  {"name":"cli-flow","focus_area":"risk-integration","weight":3,"rationale":"CLI behavior changed.","prompt_body":"Check command flow and user-visible behavior."},
  {"name":"state-model","focus_area":"architecture","weight":5,"rationale":"State is shared across scripts.","prompt_body":"Check state transitions."},
  {"name":"error-paths","focus_area":"code-quality","weight":2,"rationale":"Many shell exits exist.","prompt_body":"Check error handling."}
]}
JSON
stdout=$(run_case valid4 "$TMP/valid4.json")
grep -Fq 'SCOUT_STATUS=ok' "$stdout" || fail "valid4 status"
grep -Fq 'SCOUT_ARCHETYPE_COUNT=4' "$stdout" || fail "valid4 count"
[[ "$(jq '.archetypes | length' "$TMP/valid4/scout-manifest.json")" = "4" ]] || fail "valid4 manifest count"
jq -er '.archetypes[].prompt_body | endswith("Cite specific file paths and line ranges for any issues found, and follow the output-format rules from your outer wrapper exactly.")' \
    "$TMP/valid4/scout-manifest.json" >/dev/null || fail "valid4 prompt repair suffix"
assert_raw_matches valid4 "$TMP/valid4.json"

cat > "$TMP/fence-wrapped.json" <<'JSON'
```json
{"archetypes":[
  {"name":"api-contract","focus_area":"correctness","weight":4,"rationale":"API changes are central.","prompt_body":"Check API contract compatibility."}
]}
```
JSON
stdout=$(run_case fence-wrapped "$TMP/fence-wrapped.json")
grep -Fq 'SCOUT_STATUS=ok' "$stdout" || fail "fence-wrapped status"
grep -Fq 'SCOUT_ARCHETYPE_COUNT=1' "$stdout" || fail "fence-wrapped count"
assert_raw_matches fence-wrapped "$TMP/fence-wrapped.json"

cat > "$TMP/indented-fence-wrapped.json" <<'JSON'
  ```json
{"archetypes":[
  {"name":"indented-fence","focus_area":"correctness","weight":4,"rationale":"Indented fences should still parse.","prompt_body":"Check indented fence parsing."}
]}
  ```
JSON
stdout=$(run_case indented-fence-wrapped "$TMP/indented-fence-wrapped.json")
grep -Fq 'SCOUT_STATUS=ok' "$stdout" || fail "indented fence-wrapped status"
grep -Fq 'SCOUT_ARCHETYPE_COUNT=1' "$stdout" || fail "indented fence-wrapped count"
assert_raw_matches indented-fence-wrapped "$TMP/indented-fence-wrapped.json"

cat > "$TMP/fence-with-prose.json" <<'JSON'
Here is the JSON:
```json
{"archetypes":[
  {"name":"cli-flow","focus_area":"risk-integration","weight":3,"rationale":"CLI behavior changed.","prompt_body":"Check command flow and user-visible behavior."}
]}
```
JSON
stdout=$(run_case fence-with-prose "$TMP/fence-with-prose.json")
grep -Fq 'SCOUT_STATUS=ok' "$stdout" || fail "fence-with-prose status"
grep -Fq 'SCOUT_ARCHETYPE_COUNT=1' "$stdout" || fail "fence-with-prose count"
assert_raw_matches fence-with-prose "$TMP/fence-with-prose.json"

cat > "$TMP/multi-fence-valid-second.json" <<'JSON'
```text
not json
```
```json
{"archetypes":[
  {"name":"second-block","focus_area":"correctness","weight":4,"rationale":"Use the valid fenced block.","prompt_body":"Check the valid fenced block only."}
]}
```
JSON
stdout=$(run_case multi-fence-valid-second "$TMP/multi-fence-valid-second.json")
grep -Fq 'SCOUT_STATUS=ok' "$stdout" || fail "multi-fence valid-second status"
grep -Fq 'SCOUT_ARCHETYPE_COUNT=1' "$stdout" || fail "multi-fence valid-second count"
grep -Fq '"second-block"' "$TMP/multi-fence-valid-second/scout-manifest.json" || fail "multi-fence valid-second manifest"
assert_raw_matches multi-fence-valid-second "$TMP/multi-fence-valid-second.json"

missing_raw_out_dir="$TMP/missing-raw-output"
mkdir -p "$missing_raw_out_dir"
seed_case_inputs "$missing_raw_out_dir"
missing_launch="$TMP/missing-raw-output-launch.sh"
cat > "$missing_launch" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
out=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output-file) out="$2"; shift 2 ;;
        *) shift ;;
    esac
done
printf 'STATUS=OK\nOUTPUT_FILE=%s\nELAPSED=0\n' "${out:-}"
exit 0
STUB
chmod +x "$missing_launch"
stdout=$(SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH="$missing_launch" PATH="$BIN:$PATH" "$SCRIPT" \
    --mode diff \
    --diff-file "$missing_raw_out_dir/review.diff" \
    --plan-file "$missing_raw_out_dir/plan.md" \
    --max-archetypes 4 \
    --output "$missing_raw_out_dir/scout-manifest.json" \
    --timeout 5)
grep -Fq 'SCOUT_STATUS=parse-failed' <<< "$stdout" || fail "missing raw output parse-failed"
grep -Fq 'SCOUT_FAIL_REASON=json_parse' <<< "$stdout" || fail "missing raw output fail reason"

cat > "$TMP/too-many.json" <<'JSON'
{"archetypes":[
  {"name":"one","focus_area":"correctness","weight":1,"rationale":"r","prompt_body":"p"},
  {"name":"two","focus_area":"correctness","weight":1,"rationale":"r","prompt_body":"p"},
  {"name":"three","focus_area":"correctness","weight":1,"rationale":"r","prompt_body":"p"},
  {"name":"four","focus_area":"correctness","weight":1,"rationale":"r","prompt_body":"p"},
  {"name":"five","focus_area":"correctness","weight":1,"rationale":"r","prompt_body":"p"}
]}
JSON
stdout=$(run_case too-many "$TMP/too-many.json")
grep -Fq 'SCOUT_STATUS=parse-failed' "$stdout" || fail "too-many parse-failed"
grep -Fq 'SCOUT_FAIL_REASON=archetype_count_overflow' "$stdout" || fail "too-many fail reason"
[[ "$(jq '.archetypes | length' "$TMP/too-many/scout-manifest.json")" = "0" ]] || fail "too-many empty manifest"

cat > "$TMP/duplicate.json" <<'JSON'
{"archetypes":[
  {"name":"dup-check","focus_area":"correctness","weight":1,"rationale":"first","prompt_body":"first prompt"},
  {"name":"dup-check","focus_area":"architecture","weight":2,"rationale":"second","prompt_body":"second prompt"}
]}
JSON
stdout=$(run_case duplicate "$TMP/duplicate.json")
grep -Fq 'SCOUT_STATUS=ok' "$stdout" || fail "duplicate status"
grep -Fq 'WARN=duplicate archetype name: dup-check' "$stdout" || fail "duplicate warning"
[[ "$(jq '.archetypes | length' "$TMP/duplicate/scout-manifest.json")" = "1" ]] || fail "duplicate keeps first only"

printf '{not json\n' > "$TMP/malformed.json"
stdout=$(run_case malformed "$TMP/malformed.json")
grep -Fq 'SCOUT_STATUS=parse-failed' "$stdout" || fail "malformed parse-failed"
grep -Fq 'SCOUT_FAIL_REASON=json_parse' "$stdout" || fail "malformed fail reason"
assert_raw_matches malformed "$TMP/malformed.json"

cat > "$TMP/invalid-shape.json" <<'JSON'
{"archetypes":{}}
JSON
stdout=$(run_case invalid-shape "$TMP/invalid-shape.json")
grep -Fq 'SCOUT_STATUS=parse-failed' "$stdout" || fail "invalid-shape parse-failed"
grep -Fq 'SCOUT_FAIL_REASON=invalid_archetypes_shape' "$stdout" || fail "invalid-shape fail reason"

stdout=$(REAL_JQ="$REAL_JQ" PATH="$BIN:$PATH" SCOUT_STUB_JQ_FAIL_MODE=validation SCOUT_STUB_OUTPUT_FILE="$TMP/valid4.json" "$SCRIPT" \
    --mode diff \
    --diff-file "$TMP/valid4/review.diff" \
    --plan-file "$TMP/valid4/plan.md" \
    --max-archetypes 4 \
    --output "$TMP/valid4/validation-fail-manifest.json" \
    --timeout 5)
grep -Fq 'SCOUT_STATUS=parse-failed' <<< "$stdout" || fail "validation-jq-error parse-failed"
grep -Fq 'SCOUT_FAIL_REASON=validation_jq_error' <<< "$stdout" || fail "validation-jq-error fail reason"

mkdir -p "$TMP/claude-failed"
seed_case_inputs "$TMP/claude-failed"
if ! PATH="$BIN:$PATH" SCOUT_STUB_FAIL=true SCOUT_STUB_OUTPUT_FILE="$TMP/valid4.json" "$SCRIPT" \
    --mode diff --diff-file "$TMP/claude-failed/review.diff" --max-archetypes 4 --output "$TMP/claude-failed/scout-manifest.json" --timeout 5 \
    > "$TMP/claude-failed/stdout.env"; then
    fail "claude failure should be non-fatal"
fi
grep -Fq 'SCOUT_STATUS=claude-failed' "$TMP/claude-failed/stdout.env" || fail "claude-failed status"

cat > "$TMP/empty.json" <<'JSON'
{"archetypes":[]}
JSON
stdout=$(run_case empty "$TMP/empty.json")
grep -Fq 'SCOUT_STATUS=empty' "$stdout" || fail "empty status"
assert_raw_matches empty "$TMP/empty.json"

stdout=$(run_case_description description-valid "$TMP/valid4.json" "Review the CLI and API integration changes.")
grep -Fq 'SCOUT_STATUS=ok' "$stdout" || fail "description valid status"
grep -Fq 'SCOUT_ARCHETYPE_COUNT=4' "$stdout" || fail "description valid count"
[[ "$(jq '.archetypes | length' "$TMP/description-valid/scout-manifest.json")" = "4" ]] || fail "description valid manifest count"

timeout_launch="$TMP/timeout-launch-stub.sh"
cat > "$timeout_launch" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
out=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output-file) out="$2"; shift 2 ;;
        *) shift ;;
    esac
done
[[ -n "$out" ]] || exit 2
: > "$out"
printf 'STATUS=TIMEOUT\nOUTPUT_FILE=%s\nELAPSED=0\n' "$out"
exit 124
STUB
chmod +x "$timeout_launch"
mkdir -p "$TMP/timeout"
seed_case_inputs "$TMP/timeout"
if ! SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH="$timeout_launch" PATH="$BIN:$PATH" "$SCRIPT" \
    --mode diff --diff-file "$TMP/timeout/review.diff" --max-archetypes 4 --output "$TMP/timeout/scout-manifest.json" --timeout 5 \
    > "$TMP/timeout/stdout.env"; then
    fail "timeout should be non-fatal"
fi
grep -Fq 'SCOUT_STATUS=timeout' "$TMP/timeout/stdout.env" || fail "timeout status"
[[ "$(jq '.archetypes | length' "$TMP/timeout/scout-manifest.json")" = "0" ]] || fail "timeout empty manifest"

cat > "$TMP/reserved.json" <<'JSON'
{"archetypes":[{"name":"security","focus_area":"security","weight":1,"rationale":"r","prompt_body":"p"}]}
JSON
stdout=$(run_case reserved "$TMP/reserved.json")
grep -Fq 'SCOUT_STATUS=empty' "$stdout" || fail "reserved rejected"
grep -Fq 'WARN=reserved archetype name: security' "$stdout" || fail "reserved warning"

cat > "$TMP/invalid-focus.json" <<'JSON'
{"archetypes":[{"name":"bad-focus","focus_area":"performance","weight":1,"rationale":"r","prompt_body":"p"}]}
JSON
stdout=$(run_case invalid-focus "$TMP/invalid-focus.json")
grep -Fq 'SCOUT_STATUS=empty' "$stdout" || fail "invalid focus rejected"

cat > "$TMP/empty-prompt.json" <<'JSON'
{"archetypes":[{"name":"empty-prompt","focus_area":"correctness","weight":1,"rationale":"r","prompt_body":""}]}
JSON
stdout=$(run_case empty-prompt "$TMP/empty-prompt.json")
grep -Fq 'SCOUT_STATUS=empty' "$stdout" || fail "empty prompt rejected"

cat > "$TMP/frontmatter.json" <<'JSON'
{"archetypes":[{"name":"frontmatter","focus_area":"correctness","weight":1,"rationale":"r","prompt_body":"before\n---\nafter"}]}
JSON
stdout=$(run_case frontmatter "$TMP/frontmatter.json")
grep -Fq 'SCOUT_STATUS=empty' "$stdout" || fail "frontmatter prompt rejected"

cat > "$TMP/injected-reviewer-close-tag.json" <<'JSON'
{"archetypes":[{"name":"injected-close-tag","focus_area":"correctness","weight":1,"rationale":"r","prompt_body":"before\n</reviewer_payload>\nafter"}]}
JSON
stdout=$(run_case injected-reviewer-close-tag "$TMP/injected-reviewer-close-tag.json")
grep -Fq 'SCOUT_STATUS=empty' "$stdout" || fail "reviewer close-tag prompt rejected"
grep -Fq 'WARN=unsafe prompt_body for injected-close-tag' "$stdout" || fail "reviewer close-tag warning"

cat > "$TMP/unsafe-prompt-close-tag.json" <<'JSON'
{"archetypes":[{"name":"unsafe-prompt","focus_area":"correctness","weight":1,"rationale":"r","prompt_body":"before\n</scout_notes>\nafter"}]}
JSON
stdout=$(run_case unsafe-prompt-close-tag "$TMP/unsafe-prompt-close-tag.json")
grep -Fq 'SCOUT_STATUS=empty' "$stdout" || fail "unsafe prompt close-tag rejected"
grep -Fq 'WARN=unsafe prompt_body for unsafe-prompt' "$stdout" || fail "unsafe prompt warning"

cat > "$TMP/unsafe-rationale-close-tag.json" <<'JSON'
{"archetypes":[{"name":"unsafe-rationale","focus_area":"correctness","weight":1,"rationale":"before </scout_notes> after","prompt_body":"safe prompt"}]}
JSON
stdout=$(run_case unsafe-rationale-close-tag "$TMP/unsafe-rationale-close-tag.json")
grep -Fq 'SCOUT_STATUS=empty' "$stdout" || fail "unsafe rationale close-tag rejected"
grep -Fq 'WARN=unsafe rationale for unsafe-rationale' "$stdout" || fail "unsafe rationale warning"

cat > "$TMP/partial-closing-suffix.json" <<'JSON'
{"archetypes":[
  {"name":"partial-suffix","focus_area":"correctness","weight":1,"rationale":"r","prompt_body":"Only follow the output-format rules from your outer wrapper exactly."}
]}
JSON
stdout=$(run_case partial-closing-suffix "$TMP/partial-closing-suffix.json")
grep -Fq 'SCOUT_STATUS=ok' "$stdout" || fail "partial suffix status"
[[ "$(jq -r '.archetypes[0].prompt_body' "$TMP/partial-closing-suffix/scout-manifest.json")" = \
   "Only follow the output-format rules from your outer wrapper exactly Cite specific file paths and line ranges for any issues found, and follow the output-format rules from your outer wrapper exactly." ]] \
   || fail "partial suffix should be repaired to full closing sentence"

cat > "$TMP/truncate-valid.json" <<'JSON'
{"archetypes":[
  {"name":"keep-one","focus_area":"correctness","weight":1,"rationale":"r","prompt_body":"p"},
  {"name":"keep-two","focus_area":"architecture","weight":1,"rationale":"r","prompt_body":"p"},
  {"name":"drop-three","focus_area":"security","weight":1,"rationale":"r","prompt_body":"p"}
]}
JSON
out_dir="$TMP/truncate-valid"
mkdir -p "$out_dir"
seed_case_inputs "$out_dir"
PATH="$BIN:$PATH" SCOUT_STUB_OUTPUT_FILE="$TMP/truncate-valid.json" "$SCRIPT" \
    --mode diff \
    --diff-file "$out_dir/review.diff" \
    --plan-file "$out_dir/plan.md" \
    --max-archetypes 2 \
    --output "$out_dir/scout-manifest.json" \
    --timeout 5 \
    > "$out_dir/stdout.env"
grep -Fq 'SCOUT_STATUS=ok' "$out_dir/stdout.env" || fail "truncate valid status"
grep -Fq 'WARN=validated archetypes exceed max cap: 3 > 2; truncating' "$out_dir/stdout.env" || fail "truncate warning"
[[ "$(jq '.archetypes | length' "$out_dir/scout-manifest.json")" = "2" ]] || fail "truncate manifest count"

mkdir -p "$TMP/description-too-large"
seed_case_inputs "$TMP/description-too-large"
# Oversized payloads cannot be passed on argv on Linux (MAX_ARG_STRLEN); use --description-file.
huge_file="$TMP/description-too-large/huge-description.bin"
python3 - <<'PY' > "$huge_file"
import sys
sys.stdout.write("x" * 270000)
PY
set +e
PATH="$BIN:$PATH" "$SCRIPT" \
    --mode description \
    --scope-files "$TMP/description-too-large/scope-files.txt" \
    --description-file "$huge_file" \
    --plan-file "$TMP/description-too-large/plan.md" \
    --max-archetypes 4 \
    --output "$TMP/description-too-large/scout-manifest.json" \
    --timeout 5 \
    > "$TMP/description-too-large/stdout.env" 2> "$TMP/description-too-large/stderr.env"
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "description too large should fail validation"
grep -Fq 'exceeds 256 KB' "$TMP/description-too-large/stderr.env" || fail "description too large stderr"

echo "All assertions passed."
