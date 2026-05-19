## Goal
Port voter-path parse-rate retry, degraded banner, and scoreboard consistency from reviewer path to voter path

## Implementation Plan

Voter-path parity with #2336: parse-rate retry, degraded banner, scoreboard consistency.

### Goal
Port the three mechanisms added to the reviewer path by PR #2336 to the voter path:
(A) parse-rate retry in dispatch-code-voters.sh,
(B) voter parse-rate–driven degraded panel banner in tally-code-votes.sh,
(C) scoreboard row format consistency (short name + always-populated Status column).
Add 6 regression tests.

### Files to modify

1. **scripts/dispatch-code-voters.sh** (Part A — retry)
   - Refactor `check_voter_parse_rate()` (lines 86-141) to return a status string:
     - Print `PARSE_RATE_STATUS=NOT_SUBSTANTIVE` to stdout when >=80% NEUTRAL threshold fires
     - Print `PARSE_RATE_STATUS=OK` when below threshold (currently void/no-op returns)
     - All existing behavior (diag file write, append-tool-failure, larch_err) preserved
   - After voter-1 dispatch (Claude, currently lines 152-163): capture `check_voter_parse_rate` output; if `PARSE_RATE_STATUS=NOT_SUBSTANTIVE`, invoke retry:
     - Prepend the injected prompt prefix to a new prompt file before re-launching
     - Re-invoke `launch-claude-review.sh` with the same args and new prompt file
     - Cap at 1 retry; track with a `voter1_retried=false/true` variable
     - On retry success (parse-rate check returns OK): replace output file, clear diag file
     - On retry failure: preserve original output and diag file
   - After voter-2/3 dispatch (dispatch-with-waterfall.sh, currently lines 224-257): for each output in `outputs_arr`, capture `check_voter_parse_rate`; retry similarly for each not-substantive voter using a re-invocation approach compatible with the existing waterfall
     - Since waterfall owns voter-2/3 dispatch, for retry: directly call the appropriate launcher (codex or cursor) for that single slot
     - Cap at 1 retry per slot
   - Retry injection string (verbatim from issue):
     `IMPORTANT: Your previous attempt produced narrative output instead of structured votes. Each line MUST start with FINDING_N: followed by exactly one of YES, NO, or EXONERATE. Do not output any prose, reasoning, or status updates before, between, or after the vote lines. If you need to verify claims, do so silently. Output ONLY vote lines.`
   - Emit `VOTER_N_PARSE_RATE_STATUS=OK|NOT_SUBSTANTIVE` alongside existing `VOTER_N_STATUS` KV lines
   - Slot identity preserved: no new reviewer slot added; same output path used

2. **scripts/dispatch-code-voters.sh** sibling: **scripts/dispatch-code-voters.md**
   - Update to describe retry behavior and new output keys

3. **skills/review/scripts/tally-code-votes.sh** (Parts B and C)
   - Part B — voter parse-rate banner (insert before current line 244):
     - Read each voter's `${voter_tool}-parse-rate-diag.txt` from `$REVIEW_TMPDIR` if present
     - Compute `VOTER_PARSE_FAILED_COUNT` = count of present diag files
     - Compute `EFFECTIVE_VOTERS = ELIGIBLE_VOTERS - VOTER_PARSE_FAILED_COUNT`
     - Replace `ELIGIBLE_VOTERS` with `EFFECTIVE_VOTERS` in the existing `< 3` banner trigger (line 244)
     - Add new banner after the NOT_SUBSTANTIVE banner (after current line 250):
       ```bash
       if [[ "$VOTER_PARSE_FAILED_COUNT" -gt 0 ]]; then
           printf '**⚠ Degraded code-review panel: %s voter slot(s) emitted narrative-only output (parse-rate ≥80%% NEUTRAL). Voted blocks have inflated NEUT counts; treat results with caution.**\n\n' "$VOTER_PARSE_FAILED_COUNT"
       fi
       ```
     - The diag file naming convention is `${REVIEW_TMPDIR}/${voter_tool}-parse-rate-diag.txt` (already written by dispatch-code-voters.sh)
     - Voter tools to check: `claude`, `codex`, `cursor` (the three known voter tools)
   - Part C — scoreboard row format consistency:
     - The existing live-row renderer (lines ~373-379) uses full filename as reviewer key from `score_rows`
     - The dead-slot renderer (lines ~382-444) uses short label (strips `-output.txt`)
     - Fix: in the live-row `awk` block (~line 373), normalize the reviewer key by stripping the `-output.txt` suffix using the same `sub(/-output\.txt$/, "", label)` pattern
     - Always emit `STATUS=OK` for live rows (so Status column is never blank)
     - Dead-slot rows already populate Status; live rows will now also populate it
     - This makes all rows use the same short-name format with a populated Status column
     - Format: `| short-name | ... | STATUS=OK |` for all live rows
     - Note: the awk block writes the score_rows TSV with full filenames as keys; the normalization happens at render time, not at write time

4. **scripts/dispatch-code-voters.sh** output keys:
   - `VOTER_1_PARSE_RATE_STATUS`, `VOTER_2_PARSE_RATE_STATUS`, `VOTER_3_PARSE_RATE_STATUS` emitted after each voter's check

### Part A retry — implementation approach for voter-2/3

The waterfall dispatch (`dispatch-with-waterfall.sh`) runs voters 2 and 3 as a batch. After parsing `ALL_OUTPUT_FILES` and `ALL_OUTPUT_TOOLS`, for each voter (index 0=voter-2, 1=voter-3):
- Run `check_voter_parse_rate "$output_path" "$tool"` and capture status
- If NOT_SUBSTANTIVE and retries remaining (max 1):
  - Derive which launcher to use: `cursor` → `launch-cursor-review.sh`, `codex` → `dispatch-with-waterfall.sh` (single-slot manifest)
  - Re-invoke with injected prompt prepended to the existing prompt file (write retry prompt to `${REVIEW_TMPDIR}/${tool}-vote-prompt-retry.txt`)
  - Replace the output file on success; clear the diag file on success
- Emit `VOTER_N_PARSE_RATE_STATUS` accordingly

### Testing strategy

**scripts/test-dispatch-code-voters.sh** (extend existing):
- Test 1: Voter parse-rate retry — happy path: stub voter that returns narrative on attempt 1, valid votes on attempt 2; assert final output contains structured votes, no diag file, VOTER_1_PARSE_RATE_STATUS=OK
- Test 2: Voter parse-rate retry — failed: stub that returns narrative on both attempts; assert diag file present, execution-issues contains Warning, VOTER_1_PARSE_RATE_STATUS=NOT_SUBSTANTIVE

**skills/review/scripts/test-tally-code-votes.sh** (extend existing):
- Test 3: Banner — voter parse-rate: fixture with parse-rate-diag.txt present for cursor voter; assert banner appears in voting-tally.md
- Test 4: Banner — combined: parse-rate-failed voter + NOT_SUBSTANTIVE reviewer; assert both banners appear
- Test 5: Scoreboard formatter: 7 reviewer fixture; assert all rows have same short-name format and populated Status column
- Test 6: No-regression: clean fixture (no failures); assert no banners, Status=OK for all rows, normal tally


## Test plan
- `make lint-bash32` after all shell edits
- `bash scripts/test-dispatch-code-voters.sh` passes
- `bash skills/review/scripts/test-tally-code-votes.sh` passes
- `/relevant-checks` passes
