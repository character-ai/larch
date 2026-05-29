#!/usr/bin/env bash
# Regression harness for scout-dynamic-archetypes.sh.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
SCRIPT="$REPO_ROOT/scripts/scout-dynamic-archetypes.sh"
export CLAUDE_PLUGIN_ROOT="$REPO_ROOT"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-scout-dynamic-archetypes.XXXXXX")
GOOD_PROMPT_OVERRIDE="$REPO_ROOT/.scout-prompt-override-harness.$$"
trap 'rm -rf "$TMP"; rm -f "$GOOD_PROMPT_OVERRIDE"' EXIT
printf 'Plan-review scout preamble override line for harness.\n' >"$GOOD_PROMPT_OVERRIDE"

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
grep -q 'You are a read-only reviewer' || exit 7
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
grep -Fq 'SCOUT_STATUS=ok' "$stdout" || fail "too-many status"
grep -Fq 'WARN=validated archetypes exceed max cap: 5 > 4; truncating' "$stdout" || fail "too-many truncate warning"
grep -Fq 'SCOUT_ARCHETYPE_COUNT=4' "$stdout" || fail "too-many count"
[[ "$(jq '.archetypes | length' "$TMP/too-many/scout-manifest.json")" = "4" ]] || fail "too-many manifest count"

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
huge_file="$TMP/description-too-large/huge-description.bin"
python3 - <<'PY' > "$huge_file"
import sys
sys.stdout.write("x" * 300000)
PY
desc_launch="$TMP/description-stub-launch.sh"
cat > "$desc_launch" <<STUB
#!/usr/bin/env bash
set -euo pipefail
[[ -n "\${SCOUT_CLAUDE_ARGV_LOG:-}" ]] && printf '%s\n' "\$*" >>"\$SCOUT_CLAUDE_ARGV_LOG"
exec "$REPO_ROOT/scripts/launch-claude-subprocess.sh" "\$@"
STUB
chmod +x "$desc_launch"
PATH="$BIN:$PATH" SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH="$desc_launch" SCOUT_STUB_OUTPUT_FILE="$TMP/valid4.json" "$SCRIPT" \
    --mode description \
    --scope-files "$TMP/description-too-large/scope-files.txt" \
    --description-file "$huge_file" \
    --plan-file "$TMP/description-too-large/plan.md" \
    --max-archetypes 4 \
    --output "$TMP/description-too-large/scout-manifest.json" \
    --timeout 5 \
    > "$TMP/description-too-large/stdout.env"
grep -Fq 'SCOUT_STATUS=ok' "$TMP/description-too-large/stdout.env" || fail "large description-file should succeed"
staged_desc="$TMP/description-too-large/staged-context/description.txt"
[[ -f "$staged_desc" ]] || fail "description file not staged"
staged_desc_bytes=$(wc -c < "$staged_desc" | tr -d '[:space:]')
[[ "$staged_desc_bytes" -gt 262144 ]] || fail "staged description fixture size $staged_desc_bytes"
grep -Fq 'staged --description-file' "$TMP/description-too-large/stdout.env" || fail "large description-file should emit staged WARN"
grep -Fq "$staged_desc" "$TMP/description-too-large/staged-context/scout-dynamic-archetypes-prompt.md" || fail "prompt must reference staged description path"
grep -Fq '<reviewer_description>' "$TMP/description-too-large/staged-context/scout-dynamic-archetypes-prompt.md" && fail "prompt must not embed bulk description"

mkdir -p "$TMP/description-text-inline-cap"
seed_case_inputs "$TMP/description-text-inline-cap"
huge_inline=$(python3 - <<'PY'
import sys
sys.stdout.write("x" * 270000)
PY
)
set +e
PATH="$BIN:$PATH" "$SCRIPT" \
    --mode description \
    --scope-files "$TMP/description-text-inline-cap/scope-files.txt" \
    --description-text "$huge_inline" \
    --plan-file "$TMP/description-text-inline-cap/plan.md" \
    --max-archetypes 4 \
    --output "$TMP/description-text-inline-cap/scout-manifest.json" \
    --timeout 5 \
    > "$TMP/description-text-inline-cap/stdout.env" 2> "$TMP/description-text-inline-cap/stderr.env"
inline_rc=$?
set -e
[[ "$inline_rc" -eq 2 ]] || fail "inline description-text over 256 KB should fail validation"
grep -Fq 'description-text exceeds 256 KB' "$TMP/description-text-inline-cap/stderr.env" || fail "inline cap stderr"

mkdir -p "$TMP/large-diff"
seed_case_inputs "$TMP/large-diff"
python3 - <<'PY' >> "$TMP/large-diff/review.diff"
import sys
sys.stdout.write("diff --git a/big b/big\n+" + "x" * 300000 + "\n")
PY
large_launch="$desc_launch"
PATH="$BIN:$PATH" SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH="$large_launch" SCOUT_STUB_OUTPUT_FILE="$TMP/valid4.json" "$SCRIPT" \
    --mode diff \
    --diff-file "$TMP/large-diff/review.diff" \
    --plan-file "$TMP/large-diff/plan.md" \
    --max-archetypes 4 \
    --output "$TMP/large-diff/scout-manifest.json" \
    --timeout 5 \
    > "$TMP/large-diff/stdout.env" 2> "$TMP/large-diff/stderr.env"
large_diff_rc=$?
[[ "$large_diff_rc" -eq 0 ]] || fail "large diff should not fail size gate"
grep -Fq 'SCOUT_STATUS=ok' "$TMP/large-diff/stdout.env" || fail "large diff scout status"
grep -Fq 'staged --diff-file' "$TMP/large-diff/stdout.env" || fail "large diff should emit staged WARN"

# --prompt-override-file: must be a regular file under CLAUDE_PLUGIN_ROOT (max 256KB).
mkdir -p "$TMP/prompt-override-good"
seed_case_inputs "$TMP/prompt-override-good"
set +e
PATH="$BIN:$PATH" "$SCRIPT" \
    --mode description \
    --scope-files "$TMP/prompt-override-good/scope-files.txt" \
    --description-text "override acceptance" \
    --plan-file "$TMP/prompt-override-good/plan.md" \
    --max-archetypes 0 \
    --output "$TMP/prompt-override-good/scout-manifest.json" \
    --prompt-override-file "$GOOD_PROMPT_OVERRIDE" \
    --timeout 5 \
    >"$TMP/prompt-override-good/stdout.env" 2>"$TMP/prompt-override-good/stderr.env"
ov_good_rc=$?
set -e
[[ "$ov_good_rc" -eq 0 ]] || fail "prompt override under plugin root with max 0 should succeed"
grep -Fq 'SCOUT_STATUS=empty' "$TMP/prompt-override-good/stdout.env" || fail "prompt override good: expected empty scout"

mkdir -p "$TMP/prompt-override-outside"
seed_case_inputs "$TMP/prompt-override-outside"
printf 'x\n' >"$TMP/prompt-override-outside/bad-override.txt"
set +e
PATH="$BIN:$PATH" "$SCRIPT" \
    --mode description \
    --scope-files "$TMP/prompt-override-outside/scope-files.txt" \
    --description-text "x" \
    --plan-file "$TMP/prompt-override-outside/plan.md" \
    --max-archetypes 0 \
    --output "$TMP/prompt-override-outside/scout-manifest.json" \
    --prompt-override-file "$TMP/prompt-override-outside/bad-override.txt" \
    --timeout 5 \
    >"$TMP/prompt-override-outside/stdout.env" 2>"$TMP/prompt-override-outside/stderr.env"
ov_out_rc=$?
set -e
[[ "$ov_out_rc" -eq 2 ]] || fail "prompt override outside CLAUDE_PLUGIN_ROOT must exit 2"
grep -Fq 'FAILURE_REASON=prompt-override-invalid' "$TMP/prompt-override-outside/stdout.env" \
    || fail "prompt override outside root: expected FAILURE_REASON on stdout"

mkdir -p "$TMP/prompt-override-symlink"
seed_case_inputs "$TMP/prompt-override-symlink"
sym_ov="$REPO_ROOT/.scout-override-symlink.$$"
ln -sf "$GOOD_PROMPT_OVERRIDE" "$sym_ov"
set +e
PATH="$BIN:$PATH" "$SCRIPT" \
    --mode description \
    --scope-files "$TMP/prompt-override-symlink/scope-files.txt" \
    --description-text "x" \
    --plan-file "$TMP/prompt-override-symlink/plan.md" \
    --max-archetypes 0 \
    --output "$TMP/prompt-override-symlink/scout-manifest.json" \
    --prompt-override-file "$sym_ov" \
    --timeout 5 \
    >"$TMP/prompt-override-symlink/stdout.env" 2>"$TMP/prompt-override-symlink/stderr.env"
ov_sym_rc=$?
set -e
rm -f "$sym_ov"
[[ "$ov_sym_rc" -eq 2 ]] || fail "prompt override symlink must exit 2"
grep -Fq 'FAILURE_REASON=prompt-override-invalid' "$TMP/prompt-override-symlink/stdout.env" \
    || fail "prompt override symlink: expected FAILURE_REASON on stdout"

mkdir -p "$TMP/prompt-override-oversize"
seed_case_inputs "$TMP/prompt-override-oversize"
huge_ov="$REPO_ROOT/.scout-prompt-override-oversize.$$"
python3 - <<PY >"$huge_ov"
import sys
sys.stdout.write("z" * 262145)
PY
set +e
PATH="$BIN:$PATH" "$SCRIPT" \
    --mode description \
    --scope-files "$TMP/prompt-override-oversize/scope-files.txt" \
    --description-text "x" \
    --plan-file "$TMP/prompt-override-oversize/plan.md" \
    --max-archetypes 0 \
    --output "$TMP/prompt-override-oversize/scout-manifest.json" \
    --prompt-override-file "$huge_ov" \
    --timeout 5 \
    >"$TMP/prompt-override-oversize/stdout.env" 2>"$TMP/prompt-override-oversize/stderr.env"
ov_big_rc=$?
set -e
rm -f "$huge_ov"
[[ "$ov_big_rc" -eq 2 ]] || fail "prompt override over 256KB must exit 2"
grep -Fq 'FAILURE_REASON=prompt-override-invalid' "$TMP/prompt-override-oversize/stdout.env" \
    || fail "prompt override oversize: expected FAILURE_REASON on stdout"

codex_tier_stub="$TMP/codex-tier-stub.sh"
cat > "$codex_tier_stub" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
[[ -n "${SCOUT_CODEX_ARGV_LOG:-}" ]] && printf '%s\n' "$*" >>"$SCOUT_CODEX_ARGV_LOG"
if printf '%s\n' "$@" | grep -Fq -- '--tool cursor'; then
    exit 99
fi
out=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) out="${2:?}"; shift 2 ;;
        *) shift ;;
    esac
done
[[ -n "$out" ]] || exit 2
if [[ "${SCOUT_CODEX_CAP_HIT:-false}" == "true" ]]; then
    printf 'cap hit prose\n' >"$out"
    printf 'STATUS=cap_hit\n' >"${out}.cap-hit"
    printf '0\n' >"${out}.done"
    exit 0
fi
if [[ "${SCOUT_CODEX_PROSE:-false}" == "true" ]]; then
    printf 'not json prose\n' >"$out"
    printf '0\n' >"${out}.done"
    exit 0
fi
cat "${SCOUT_CODEX_JSON_FILE:?SCOUT_CODEX_JSON_FILE required}" >"$out"
printf '0\n' >"${out}.done"
exit 0
STUB
chmod +x "$codex_tier_stub"

mkdir -p "$TMP/waterfall-codex-win"
seed_case_inputs "$TMP/waterfall-codex-win"
export SCOUT_CODEX_ARGV_LOG="$TMP/waterfall-codex-win/codex-argv.log"
export SCOUT_CLAUDE_ARGV_LOG="$TMP/waterfall-codex-win/claude-argv.log"
PATH="$BIN:$PATH" \
    SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_SH="$codex_tier_stub" \
    SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH="$desc_launch" \
    SCOUT_CODEX_JSON_FILE="$TMP/valid4.json" \
    SCOUT_STUB_OUTPUT_FILE="$TMP/malformed.json" \
    "$SCRIPT" \
    --mode diff \
    --diff-file "$TMP/waterfall-codex-win/review.diff" \
    --plan-file "$TMP/waterfall-codex-win/plan.md" \
    --max-archetypes 4 \
    --output "$TMP/waterfall-codex-win/scout-manifest.json" \
    --codex-present true \
    --cursor-present true \
    --timeout 5 \
    >"$TMP/waterfall-codex-win/stdout.env"
grep -Fq 'SCOUT_STATUS=ok' "$TMP/waterfall-codex-win/stdout.env" || fail "codex tier should win waterfall"
cmp -s "$TMP/valid4.json" "$TMP/waterfall-codex-win/scout-manifest.json.raw" || fail "codex raw should be winner"
grep -Fq -- '--tool codex' "$SCOUT_CODEX_ARGV_LOG" || fail "codex tier must use --tool codex"
grep -Fq -- '--tool cursor' "$SCOUT_CODEX_ARGV_LOG" && fail "scout must not invoke --tool cursor"

mkdir -p "$TMP/waterfall-fallthrough"
seed_case_inputs "$TMP/waterfall-fallthrough"
export SCOUT_CLAUDE_ARGV_LOG="$TMP/waterfall-fallthrough/claude-argv.log"
PATH="$BIN:$PATH" \
    SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_SH="$codex_tier_stub" \
    SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH="$desc_launch" \
    SCOUT_CODEX_PROSE=true \
    SCOUT_STUB_OUTPUT_FILE="$TMP/valid4.json" \
    "$SCRIPT" \
    --mode diff \
    --diff-file "$TMP/waterfall-fallthrough/review.diff" \
    --plan-file "$TMP/waterfall-fallthrough/plan.md" \
    --max-archetypes 4 \
    --output "$TMP/waterfall-fallthrough/scout-manifest.json" \
    --codex-present true \
    --timeout 5 \
    >"$TMP/waterfall-fallthrough/stdout.env"
grep -Fq 'SCOUT_STATUS=ok' "$TMP/waterfall-fallthrough/stdout.env" || fail "codex prose should fall through to claude"
cmp -s "$TMP/valid4.json" "$TMP/waterfall-fallthrough/scout-manifest.json.raw" || fail "claude should supply winning raw"
grep -Fq -- '--read-tools' "$SCOUT_CLAUDE_ARGV_LOG" || fail "claude tier must pass --read-tools"

mkdir -p "$TMP/waterfall-cap-hit-cleanup"
seed_case_inputs "$TMP/waterfall-cap-hit-cleanup"
PATH="$BIN:$PATH" \
    SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_SH="$codex_tier_stub" \
    SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH="$desc_launch" \
    SCOUT_CODEX_CAP_HIT=true \
    SCOUT_STUB_OUTPUT_FILE="$TMP/valid4.json" \
    "$SCRIPT" \
    --mode diff \
    --diff-file "$TMP/waterfall-cap-hit-cleanup/review.diff" \
    --plan-file "$TMP/waterfall-cap-hit-cleanup/plan.md" \
    --max-archetypes 4 \
    --output "$TMP/waterfall-cap-hit-cleanup/scout-manifest.json" \
    --codex-present true \
    --timeout 5 \
    >"$TMP/waterfall-cap-hit-cleanup/stdout.env"
grep -Fq 'SCOUT_STATUS=ok' "$TMP/waterfall-cap-hit-cleanup/stdout.env" || fail "stale cap-hit must not block claude winner"
[[ ! -f "$TMP/waterfall-cap-hit-cleanup/scout-manifest.json.raw.cap-hit" ]] || fail "cap-hit sidecar should be removed before claude tier"

mkdir -p "$TMP/waterfall-exhausted"
seed_case_inputs "$TMP/waterfall-exhausted"
printf 'still not json\n' >"$TMP/codex-bad.raw"
PATH="$BIN:$PATH" \
    SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_SH="$codex_tier_stub" \
    SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH="$desc_launch" \
    SCOUT_CODEX_PROSE=true \
    SCOUT_STUB_OUTPUT_FILE="$TMP/malformed.json" \
    "$SCRIPT" \
    --mode diff \
    --diff-file "$TMP/waterfall-exhausted/review.diff" \
    --plan-file "$TMP/waterfall-exhausted/plan.md" \
    --max-archetypes 4 \
    --output "$TMP/waterfall-exhausted/scout-manifest.json" \
    --codex-present true \
    --timeout 5 \
    >"$TMP/waterfall-exhausted/stdout.env"
grep -Fq 'SCOUT_STATUS=empty' "$TMP/waterfall-exhausted/stdout.env" || fail "multi-tier probe exhaustion should be empty"
grep -Fq 'SCOUT_FAIL_REASON' "$TMP/waterfall-exhausted/stdout.env" && fail "probe exhaustion must not set SCOUT_FAIL_REASON"
[[ "$(jq -c . "$TMP/waterfall-exhausted/scout-manifest.json")" == '{"archetypes":[]}' ]] || fail "probe exhaustion manifest"

claude_fail_launch="$TMP/waterfall-probe-claude-fail-launch.sh"
cat > "$claude_fail_launch" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf 'STATUS=ERROR\nELAPSED=0\n'
exit 7
STUB
chmod +x "$claude_fail_launch"
mkdir -p "$TMP/waterfall-probe-claude-fail"
seed_case_inputs "$TMP/waterfall-probe-claude-fail"
PATH="$BIN:$PATH" \
    SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_SH="$codex_tier_stub" \
    SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH="$claude_fail_launch" \
    SCOUT_CODEX_PROSE=true \
    "$SCRIPT" \
    --mode diff \
    --diff-file "$TMP/waterfall-probe-claude-fail/review.diff" \
    --plan-file "$TMP/waterfall-probe-claude-fail/plan.md" \
    --max-archetypes 4 \
    --output "$TMP/waterfall-probe-claude-fail/scout-manifest.json" \
    --codex-present true \
    --timeout 5 \
    >"$TMP/waterfall-probe-claude-fail/stdout.env"
grep -Fq 'SCOUT_STATUS=claude-failed' "$TMP/waterfall-probe-claude-fail/stdout.env" || fail "codex prose + claude launch fail should surface claude-failed"
grep -Fq 'SCOUT_FAIL_REASON' "$TMP/waterfall-probe-claude-fail/stdout.env" && fail "launcher failure must not set SCOUT_FAIL_REASON"

codex_fail_launch="$TMP/waterfall-codex-fail-launch.sh"
cat > "$codex_fail_launch" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf 'STATUS=ERROR\nELAPSED=0\n'
exit 7
STUB
chmod +x "$codex_fail_launch"
mkdir -p "$TMP/waterfall-codex-fail-claude-win"
seed_case_inputs "$TMP/waterfall-codex-fail-claude-win"
PATH="$BIN:$PATH" \
    SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_SH="$codex_fail_launch" \
    SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH="$desc_launch" \
    SCOUT_STUB_OUTPUT_FILE="$TMP/valid4.json" \
    "$SCRIPT" \
    --mode diff \
    --diff-file "$TMP/waterfall-codex-fail-claude-win/review.diff" \
    --plan-file "$TMP/waterfall-codex-fail-claude-win/plan.md" \
    --max-archetypes 4 \
    --output "$TMP/waterfall-codex-fail-claude-win/scout-manifest.json" \
    --codex-present true \
    --timeout 5 \
    >"$TMP/waterfall-codex-fail-claude-win/stdout.env"
grep -Fq 'SCOUT_STATUS=ok' "$TMP/waterfall-codex-fail-claude-win/stdout.env" || fail "codex launch fail should fall through to claude winner"

mkdir -p "$TMP/waterfall-both-launch-fail"
seed_case_inputs "$TMP/waterfall-both-launch-fail"
PATH="$BIN:$PATH" \
    SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_SH="$codex_fail_launch" \
    SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH="$claude_fail_launch" \
    "$SCRIPT" \
    --mode diff \
    --diff-file "$TMP/waterfall-both-launch-fail/review.diff" \
    --plan-file "$TMP/waterfall-both-launch-fail/plan.md" \
    --max-archetypes 4 \
    --output "$TMP/waterfall-both-launch-fail/scout-manifest.json" \
    --codex-present true \
    --timeout 5 \
    >"$TMP/waterfall-both-launch-fail/stdout.env"
grep -Fq 'SCOUT_STATUS=claude-failed' "$TMP/waterfall-both-launch-fail/stdout.env" || fail "both tiers launch fail should surface last-tier claude-failed"

mkdir -p "$TMP/waterfall-exit0-empty"
seed_case_inputs "$TMP/waterfall-exit0-empty"
empty_launch="$TMP/waterfall-exit0-empty-launch.sh"
cat > "$empty_launch" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
out=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output-file) out="$2"; shift 2 ;;
        --output) out="$2"; shift 2 ;;
        *) shift ;;
    esac
done
: >"${out:?}"
printf 'STATUS=OK\nELAPSED=0\n'
exit 0
STUB
chmod +x "$empty_launch"
PATH="$BIN:$PATH" \
    SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_SH="$codex_tier_stub" \
    SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH="$empty_launch" \
    SCOUT_CODEX_PROSE=true \
    "$SCRIPT" \
    --mode diff \
    --diff-file "$TMP/waterfall-exit0-empty/review.diff" \
    --plan-file "$TMP/waterfall-exit0-empty/plan.md" \
    --max-archetypes 4 \
    --output "$TMP/waterfall-exit0-empty/scout-manifest.json" \
    --codex-present true \
    --timeout 5 \
    >"$TMP/waterfall-exit0-empty/stdout.env"
grep -Fq 'SCOUT_STATUS=empty' "$TMP/waterfall-exit0-empty/stdout.env" || fail "exit-0 empty tier raw should contribute to probe exhaustion (empty)"

mkdir -p "$TMP/staged-900k-diff"
seed_case_inputs "$TMP/staged-900k-diff"
python3 - <<'PY' >"$TMP/staged-900k-diff/review.diff"
import sys
sys.stdout.write("diff --git a/big b/big\n+" + "x" * 900000 + "\n")
PY
PATH="$BIN:$PATH" SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH="$desc_launch" SCOUT_STUB_OUTPUT_FILE="$TMP/valid4.json" "$SCRIPT" \
    --mode diff \
    --diff-file "$TMP/staged-900k-diff/review.diff" \
    --plan-file "$TMP/staged-900k-diff/plan.md" \
    --max-archetypes 4 \
    --output "$TMP/staged-900k-diff/scout-manifest.json" \
    --timeout 5 \
    >"$TMP/staged-900k-diff/stdout.env"
grep -Fq 'SCOUT_STATUS=ok' "$TMP/staged-900k-diff/stdout.env" || fail "~900 KB staged diff should succeed"
grep -Fq 'staged --diff-file' "$TMP/staged-900k-diff/stdout.env" || fail "~900 KB staged diff should emit staged WARN"

mkdir -p "$TMP/staged-over-1mb-diff"
seed_case_inputs "$TMP/staged-over-1mb-diff"
python3 - <<'PY' >"$TMP/staged-over-1mb-diff/review.diff"
import sys
sys.stdout.write("diff --git a/big b/big\n+" + "x" * 1048600 + "\n")
PY
PATH="$BIN:$PATH" SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH="$desc_launch" SCOUT_STUB_OUTPUT_FILE="$TMP/valid4.json" "$SCRIPT" \
    --mode diff \
    --diff-file "$TMP/staged-over-1mb-diff/review.diff" \
    --plan-file "$TMP/staged-over-1mb-diff/plan.md" \
    --max-archetypes 4 \
    --output "$TMP/staged-over-1mb-diff/scout-manifest.json" \
    --timeout 5 \
    >"$TMP/staged-over-1mb-diff/stdout.env"
grep -Fq 'SCOUT_STATUS=ok' "$TMP/staged-over-1mb-diff/stdout.env" || fail ">1 MB staged diff should fail-open with stub launcher"
grep -Fq 'staged --diff-file' "$TMP/staged-over-1mb-diff/stdout.env" || fail ">1 MB staged diff should emit staged WARN over cap"

mkdir -p "$TMP/codex-no-description-text-argv"
seed_case_inputs "$TMP/codex-no-description-text-argv"
codex_huge_file="$TMP/codex-no-description-text-argv/huge-description.bin"
cp -f "$huge_file" "$codex_huge_file"
export SCOUT_CODEX_ARGV_LOG="$TMP/codex-no-description-text-argv/codex-argv.log"
PATH="$BIN:$PATH" \
    SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_SH="$codex_tier_stub" \
    SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH="$desc_launch" \
    SCOUT_CODEX_JSON_FILE="$TMP/valid4.json" \
    "$SCRIPT" \
    --mode description \
    --scope-files "$TMP/codex-no-description-text-argv/scope-files.txt" \
    --description-file "$codex_huge_file" \
    --plan-file "$TMP/codex-no-description-text-argv/plan.md" \
    --max-archetypes 4 \
    --output "$TMP/codex-no-description-text-argv/scout-manifest.json" \
    --codex-present true \
    --timeout 5 \
    >"$TMP/codex-no-description-text-argv/stdout.env"
grep -Fq -- '--description-text' "$SCOUT_CODEX_ARGV_LOG" && fail "codex tier must not pass --description-text on --prompt-file launches"
grep -Fq -- '--codex-add-dir' "$SCOUT_CODEX_ARGV_LOG" || fail "codex tier must pass --codex-add-dir"

mkdir -p "$TMP/max-zero-no-stage"
seed_case_inputs "$TMP/max-zero-no-stage"
huge_diff="$TMP/max-zero-no-stage/huge.diff"
python3 - <<'PY' >"$huge_diff"
import sys
sys.stdout.write("diff --git a/big b/big\n+" + "x" * 300000 + "\n")
PY
set +e
PATH="$BIN:$PATH" "$SCRIPT" \
    --mode diff \
    --diff-file "$huge_diff" \
    --plan-file "$TMP/max-zero-no-stage/plan.md" \
    --max-archetypes 0 \
    --output "$TMP/max-zero-no-stage/scout-manifest.json" \
    --timeout 5 \
    >"$TMP/max-zero-no-stage/stdout.env" 2>"$TMP/max-zero-no-stage/stderr.env"
max_zero_rc=$?
set -e
[[ "$max_zero_rc" -eq 0 ]] || fail "max-archetypes 0 should succeed"
grep -Fq 'SCOUT_STATUS=empty' "$TMP/max-zero-no-stage/stdout.env" || fail "max-archetypes 0 status"
[[ ! -d "$TMP/max-zero-no-stage/staged-context" ]] || fail "max-archetypes 0 must not stage context"

implement_root="$TMP/implement-tmp-root"
mkdir -p "$implement_root"
cp "$diff_file" "$implement_root/outside.diff"
mkdir -p "$TMP/staging-outside"
cp "$scope_file" "$TMP/staging-outside/scope-files.txt"
cp "$plan_file" "$TMP/staging-outside/plan.md"
PATH="$BIN:$PATH" IMPLEMENT_TMPDIR="$implement_root" SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH="$desc_launch" SCOUT_STUB_OUTPUT_FILE="$TMP/valid4.json" "$SCRIPT" \
    --mode diff \
    --diff-file "$implement_root/outside.diff" \
    --plan-file "$TMP/staging-outside/plan.md" \
    --max-archetypes 4 \
    --output "$TMP/staging-outside/scout-manifest.json" \
    --timeout 5 \
    >"$TMP/staging-outside/stdout.env"
[[ -f "$TMP/staging-outside/staged-context/diff.txt" ]] || fail "outside diff not staged"
grep -Fq "$TMP/staging-outside/staged-context/diff.txt" "$TMP/staging-outside/staged-context/scout-dynamic-archetypes-prompt.md" || fail "prompt must use staged diff path"
grep -Fq '<reviewer_diff>' "$TMP/staging-outside/staged-context/scout-dynamic-archetypes-prompt.md" && fail "prompt must not embed diff"

prompt_path="$TMP/staging-outside/staged-context/scout-dynamic-archetypes-prompt.md"
grep -Fq 'Read the file at' "$prompt_path" || fail "prompt must reference Read tool paths"
grep -Fq 'review.diff' "$prompt_path" && fail "prompt must not reference raw review.diff basename from caller path"

echo "All assertions passed."
