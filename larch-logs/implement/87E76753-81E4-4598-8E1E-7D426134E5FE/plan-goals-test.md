## Goal
Separate problem-quality from fix-quality in review voting; preserve per-reviewer fix proposals verbatim for the coder

## Implementation Plan

**Goal**: Separate problem-quality from fix-quality in the review voting protocol; preserve per-reviewer fix proposals verbatim for the coder.

### Files to modify

1. `agents/orchestrator-aggregator.md`
   - Replace single `Suggested revision: <minimal fix direction>` field with a per-reviewer attributed list
   - New field name: `Suggested revisions (informational for voters; coder decides):`
   - Format: `  - From <slot>: <verbatim text from that reviewer>`
   - Add instruction: quote each reviewer's fix verbatim; merge two bullets only when wording is literally identical; never paraphrase across distinct proposals

2. `docs/voting-process.md`
   - In the voter table, update NO definition from:
     "The finding is incorrect, trivial, or would cause more harm than good."
   - To:
     "The problem is not real or not worth raising in this PR. **Do not vote NO because you dislike the proposed fix** — fix proposals are informational; the coder will design the actual fix."

3. `scripts/dispatch-code-voters.sh` — `make_voter_prompt_file` function
   - Add line after EXONERATE instruction: "Do NOT vote NO solely because you dislike or distrust the proposed fix — fix proposals are informational; the coder decides the exact change. Vote NO only when the stated problem is not real or not worth raising."

4. `skills/review-and-fix/scripts/review-and-fix.sh` — `compose_coder_prompt` function
   - After the `Suggested revision` reference, add a coder-instruction sentence: "Each finding may list one or more suggested revisions from different reviewers. Design a fix guided by those proposals, but decide the exact change yourself. Stay minimal — fix the stated problem; do not expand scope beyond what reviewers raised."

5. `skills/review/scripts/aggregate-findings.sh` — Python validator (`validate_py`)
   - Add a check: for each merged output FINDING block that has a `Suggested revisions` sub-list, verify that each `From <slot>:` bullet's text appears (as a substring, case-insensitive, after stripping punctuation) somewhere in the input block(s) for that finding's source slots. Flag (emit to stderr) when a bullet's content can't be traced back to any input for that slot.

### Edge cases
- The validator check must tolerate the new `Suggested revisions` format AND the old `Suggested revision:` single-line format (for backward compat during transition).
- The `dispatch-code-voters.sh` change must not duplicate the EXONERATE guidance already present.
- The `review-and-fix.sh` change only affects the `compose_coder_prompt` function's file directive (the function is invoked when findings contain `Suggested revision` references).


## Test plan
- Run `/relevant-checks` (pre-commit + agent-lint)
