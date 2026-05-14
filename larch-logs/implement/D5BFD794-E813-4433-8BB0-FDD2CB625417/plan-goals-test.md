## Goal
Eliminate var-capture stdout bloat in /review scripts; add stdout-size cap assertions to test harnesses

## Implementation Plan

### Goal
Convert var=$(cmd...) capture patterns in skills/review/scripts/*.sh to file-redirect, ensure
every script emits only KEY=VALUE envelope on stdout, add stdout-size cap assertions to test harnesses.

### Audit Findings

1. gather-context.sh (lines 39-40): `out=$(gather-branch-context.sh ...); printf '%s\n' "$out"`
   — captures then re-emits via variable. Fix: call directly without capture.

2. collect-findings.sh (line 138): `collector_out=$(collect-agent-results.sh ... 2>"$log")`
   — captures into variable; NOT re-emitted to stdout (written to files). Still convert per AC#1.
   Also: append_non_ok_collector_results() reads from string variable via heredoc.
   Line 244: `printf '%s\n' "$collector_out" > "..../collector-results.env"` — needs conversion.

3. tally-votes.sh (line 41): `parse_out=$(ballot-parse.sh ...)` — captures potentially-large
   ballot text (FINDING_N_TITLE=, FINDING_N_CONCERN= per finding). Only used for count extraction.

4. dispatch-panel.sh: Already correct (> "$launch_log" 2>&1 pattern). No change.
5. emit-tally.sh, detect-wholesale-rejection.sh, log-phase.sh: Already envelope-only. No change.

### Changes

**File 1: skills/review/scripts/gather-context.sh** (~2 lines)
- Remove `out=$(gather-branch-context.sh ...); printf '%s\n' "$out"` (lines 39-40)
- Replace with direct call: `"$PLUGIN_ROOT/scripts/gather-branch-context.sh" --output-dir "$OUTPUT_DIR"`

**File 2: skills/review/scripts/collect-findings.sh** (~15 lines)
- Add `collector_results_file="$REVIEW_TMPDIR/collector-results.env"` before if-block
- Change `collector_out=$(... 2>"$collector_log")` to `... > "$collector_results_file" 2>"$collector_log"`
- On failure: `cat "$collector_results_file" >> "$collector_log"` replaces `printf '%s\n' "$collector_out" >> ...`
- Rename function to `append_non_ok_collector_results_from_file`, accept filename, use `< "$file"` instead of `<<< "$collector_text"`
- Change call to `append_non_ok_collector_results_from_file "$collector_results_file"`
- Remove line 244 (now writes directly to `collector-results.env`)
- Add `COLLECTOR_OUTPUT_FILE=` to envelope (after COLLECT_OK=true)
- Remove `collector_out=""` initialization

**File 3: skills/review/scripts/tally-votes.sh** (~4 lines)
- Replace `parse_out=$(ballot-parse.sh ...)` with file-redirect:
  `ballot_parse_file="$REVIEW_TMPDIR/ballot-parse.env"`
  `"$SHARED_DIR/ballot-parse.sh" --ballot-file "$FINDINGS_FILE" > "$ballot_parse_file"`
- Replace `count=$(printf '%s\n' "$parse_out" | awk ...)` with:
  `count=$(awk -F= '$1=="FINDING_COUNT"{print $2}' "$ballot_parse_file")`
- Remove `parse_out` variable

**Files 4-10: Test harnesses** (all 7 test scripts, ~4 lines each)
For each `out=$(script ...)` invocation, add after:
```bash
_bytes=${#out}
[[ "$_bytes" -le 2048 ]] || { echo "FAIL: stdout ${_bytes}B > 2KB cap" >&2; exit 1; }
```
For failure-path invocations (expected to emit error envelope): cap at 4096 bytes.

**Files 11-13: Sibling .md updates**
- collect-findings.md: add COLLECTOR_OUTPUT_FILE to envelope list; document file-redirect pattern
- gather-context.md: confirm envelope-only (no capture mention needed)
- tally-votes.md: note ballot-parse output is file-backed

### Testing Strategy
- Run /relevant-checks after all changes
- Each test harness runs in CI via make lint; size assertions will fail fast if any script re-emits sub-command bodies

## Test plan
(no test plan section in plan-file)
