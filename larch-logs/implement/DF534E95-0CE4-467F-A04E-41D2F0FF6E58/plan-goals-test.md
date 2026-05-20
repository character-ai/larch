## Goal
Add three anti-narrative directives to make_voter_prompt_file to eliminate cursor voter parse-retry rate

## Implementation Plan

### Objective
Add three anti-narrative directives to `make_voter_prompt_file` in `scripts/dispatch-code-voters.sh` so that cursor (and all) voters start from an "Output ONLY vote lines" state on first pass, eliminating the 70-85% parse-retry rate caused by cursor narrating before emitting votes.

### Files to modify

1. **`scripts/dispatch-code-voters.sh`** — `make_voter_prompt_file` function (lines 46-64)
   - After `printf 'Use any provided diff/plan context files to verify the ballot claims before voting.\n'`, insert:
     `printf '**Verify silently** — do not produce narrative output, reasoning explanations, or status updates before, between, or after the vote lines. **Do not invoke any tools** for the verification phase.\n'`
   - Replace `printf 'IMPORTANT: lines that do not start with FINDING_N: followed by YES, NO, or EXONERATE are silently ignored. Use the exact ID from the ballot heading.\n'` with:
     `printf '**Output ONLY vote lines.** Lines that do not start with FINDING_N: followed by YES, NO, or EXONERATE are silently ignored. Use the exact ID from the ballot heading.\n'`

2. **`scripts/test-dispatch-code-voters.sh`** — after the existing first-pass sidecar check (line 177), add three `grep -Fq` assertions on `$TMP/happy/claude-vote-prompt.txt`:
   - `grep -Fq 'Verify silently'`
   - `grep -Fq 'Do not invoke any tools'`
   - `grep -Fq 'Output ONLY vote lines'`
   (These piggyback on the already-executed happy-path invocation; no new script invocation needed.)

### Edge cases
- The retry prompt still prepends its apologetic preamble (unchanged), which is correct — it only makes sense after a failed first attempt.
- Claude and codex first-pass behavior: the new directives are low-risk for them (they already produce structured votes cleanly at 0% parse-retry rate in observed history).
- The `\n` between the new "Verify silently" line and "For every ballot item" block provides a blank line separator for readability (matching the proposed format in the issue).

### Testing strategy
- Run `bash scripts/test-dispatch-code-voters.sh` — the three new assertions will catch future drift from the directive text.
- The existing happy-path parse-retry-sidecar check (line 176-177) already asserts no first-pass retries fire for any voter when stubs return structured output.
- Run `make lint` for the full lint suite including `lint-bash32`.

## Test plan
(no test plan section in plan-file)
