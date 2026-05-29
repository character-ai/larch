### FINDING_1: Gate A/B rewrites can lose optional trailers before emit
- **Reviewer(s)**: Cursor-Edge, Cursor-dyn-revision-preservation, Codex-dyn-revision-preservation
- **Severity**: important
- **Concern**: Gate A/B direct rewrites and Gate B post-apply/dedup guidance preserve optional size trailers only by prompt/prose, so a rewrite can drop `diff_added`, `diff_deleted`, or `mechanical_churn` while leaving `diff_lines` valid. That makes Step 2b.5 fall back to legacy total-diff behavior, and current structure checks may still pass because they grep for prose rather than exercising the rewrite path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Exempt the final contiguous metadata block immediately above required `diff_lines:` from semantic dedup, or rerun the same snapshot/strict-trailer validation after dedup and before `ACTION=EMIT_PLAN`; mirror the carve-out in `skills/design/SKILL.md` Gate B surfaces.
  - From Cursor-dyn-revision-preservation: Add a minimal script-owned validation point before ACTION=EMIT_PLAN on Gate A and Gate B direct rewrites, reusing the same strict final metadata snapshot/validate helper as waterfall; add one focused harness that starts with optional trailers, performs a rewrite that drops them, and asserts the pre-emit path rejects or repairs it
  - From Codex-dyn-revision-preservation: Add a minimal script-owned validation point before ACTION=EMIT_PLAN on Gate A and Gate B direct rewrites, reusing the same strict final metadata snapshot/validate helper as waterfall; add one focused harness that starts with optional trailers, performs a rewrite that drops them, and asserts the pre-emit path rejects or repairs it

### FINDING_2: Plan review loop dedup can undo waterfall trailer preservation
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `revise-plan-with-waterfall.sh` may validate optional trailers before emitting, but `plan-review-loop.sh` then runs post-apply dedup before `check-plan-size`. An adjacent duplicate trailer-shaped body line can cause the authoritative final trailer to be removed or mis-parsed, restoring legacy hard gating.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add plan-review-loop.sh to the change set: snapshot strict optional trailer keys before dedup and re-validate (or restore from pre-dedup snapshot) after dedup, reusing the same contract as revise-plan-with-waterfall; document failure mode #10 and extend test-plan-review-loop (non-stub revise or fixture plan with adjacent duplicate trailer-shaped body line) so LOOP_STATUS=plan-size-trigger cannot regress silently

### FINDING_3: Files-to-modify heading is not a concrete path
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The plan’s files-to-modify section uses a vague combined heading instead of exactly one concrete path per `NEW`/`UPDATED`/`REWRITTEN` heading, which can make downstream scoping malformed or cause an implementer to miss the docs update.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Split it into exact headings, e.g. skills/design/scripts/revise-plan-with-waterfall.sh and skills/design/scripts/revise-plan-with-waterfall.md, and remove the "sibling docs/prompts if present" wording

### FINDING_4: Legacy byte-for-byte wording conflicts with additive output keys
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The plan says legacy plans reproduce current behavior byte-for-byte, but the proposed helper always emits four new keys on exit 0. That can lead an implementer to omit `DIFF_ADDED`, `DIFF_DELETED`, `MECHANICAL_CHURN`, and `SOFT_ADVISORY` for legacy plans, contradicting the output contract and tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Change the summary to say legacy trigger decisions and existing keys remain unchanged, while exit-0 output gains additive keys
  - From Codex-Requirements: Change the summary to say legacy trigger decisions and existing keys remain unchanged, while exit-0 output gains additive keys

### FINDING_5: Mechanical churn acceptance criterion is overbroad
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The acceptance text says `mechanical_churn: true` yields `HARD_TRIGGER_FIRED=false` and `SOFT_ADVISORY=true` without limiting that behavior to downgraded diff-side triggers. This conflicts with the plan’s rule that plan-body crossings still hard-trigger and under-threshold mechanical churn has no advisory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Qualify the acceptance criterion: mechanical_churn true downgrades only a diff-side hard trigger; plan-body hard triggers remain hard, and SOFT_ADVISORY is true only when a diff trigger was actually downgraded
  - From Codex-Requirements: Qualify the acceptance criterion: mechanical_churn true downgrades only a diff-side hard trigger; plan-body hard triggers remain hard, and SOFT_ADVISORY is true only when a diff trigger was actually downgraded

### FINDING_6: Skill authoring surface omits exact trailer parse contract
- **Reviewer(s)**: Cursor-dyn-contract-drift, Codex-dyn-contract-drift
- **Severity**: important
- **Concern**: The proposed `skills/design/SKILL.md` Step 2b and Step 2b.5 prose omits exact optional-trailer regexes, blank-line/non-match scan stop behavior, and duplicate last-match-wins semantics. Designers may emit malformed or ambiguous trailers that silently fall back to legacy total-diff behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-contract-drift: Add a compact pointer in the Step 2b trailer bullet and Step 2b.5 parse text to the exact grammar: final contiguous block above final diff_lines, regexes ^diff_added: [0-9]+$, ^diff_deleted: [0-9]+$, ^mechanical_churn: (true|false)$, blanks/non-matches stop scanning, duplicate keys choose the last match in file order closest to diff_lines
  - From Codex-dyn-contract-drift: Add a compact pointer in the Step 2b trailer bullet and Step 2b.5 parse text to the exact grammar: final contiguous block above final diff_lines, regexes ^diff_added: [0-9]+$, ^diff_deleted: [0-9]+$, ^mechanical_churn: (true|false)$, blanks/non-matches stop scanning, duplicate keys choose the last match in file order closest to diff_lines

### FINDING_7: Flags reference omits trailer boundary and duplicate semantics
- **Reviewer(s)**: Cursor-dyn-contract-drift, Codex-dyn-contract-drift
- **Severity**: important
- **Concern**: The planned `flags.md` summary includes the grammar and new keys but not the blank-line/non-match scan stop rule or duplicate-key last-match-wins semantics, leaving exactly the drift cases ambiguous.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-contract-drift: Extend the planned flags.md summary with one sentence naming blank-line/non-match scan stop and duplicate-key last-match-wins closest to final diff_lines; keep the full regex detail delegated to check-plan-size.md if preferred
  - From Codex-dyn-contract-drift: Extend the planned flags.md summary with one sentence naming blank-line/non-match scan stop and duplicate-key last-match-wins closest to final diff_lines; keep the full regex detail delegated to check-plan-size.md if preferred

### FINDING_8: Gate B preservation prose omits final-block parse invariants
- **Reviewer(s)**: Cursor-dyn-contract-drift, Codex-dyn-contract-drift
- **Severity**: important
- **Concern**: Gate B rewrite guidance says to preserve strict optional keys but does not require them to remain in the final contiguous metadata block immediately above `diff_lines`, with no blank separator, or define duplicate-key winner semantics. A rewrite can appear to preserve trailers while changing which values `check-plan-size.sh` uses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-contract-drift: Add the same minimal preservation invariant to Gate B: preserved or recomputed optional trailers must be in the final contiguous metadata block immediately above final diff_lines, no blank separator, with duplicates resolved by the closest-to-diff_lines value
  - From Codex-dyn-contract-drift: Add the same minimal preservation invariant to Gate B: preserved or recomputed optional trailers must be in the final contiguous metadata block immediately above final diff_lines, no blank separator, with duplicates resolved by the closest-to-diff_lines value

### FINDING_9: Discussion rewrite preservation omits final-block parse invariants
- **Reviewer(s)**: Cursor-dyn-contract-drift, Codex-dyn-contract-drift
- **Severity**: important
- **Concern**: Post-plan discussion rewrite guidance says to preserve optional trailers in the final block but omits blank-line scan stop and duplicate last-match-wins semantics. A discussion rewrite can strand trailers above a blank line or invert duplicates, causing Step 2b.5 to ignore or misread the intended relief.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-contract-drift: Add the same minimal post-rewrite guard used for Gate B: strict optional trailers must remain in the final contiguous block with no blank/non-trailer boundary before diff_lines, and duplicate optional keys use the closest-to-diff_lines match
  - From Codex-dyn-contract-drift: Add the same minimal post-rewrite guard used for Gate B: strict optional trailers must remain in the final contiguous block with no blank/non-trailer boundary before diff_lines, and duplicate optional keys use the closest-to-diff_lines match

### FINDING_10: Spoof-resistance fixture does not pin the winning metadata block
- **Reviewer(s)**: Cursor-dyn-harness-completeness, Codex-dyn-harness-completeness
- **Severity**: important
- **Concern**: The proposed spoof-resistance test says prose or fenced `mechanical_churn: true` and `diff_added: 0` are ignored, but does not specify conflicting real final metadata values or assert which block wins. A parser that incorrectly scans body text could still pass a weak fixture.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-harness-completeness: Make the case fixture explicit: put mechanical_churn: true and diff_added: 0 in body prose or a fenced block, then put conflicting strict trailers in the final metadata block, and assert DIFF_ADDED, MECHANICAL_CHURN, HARD_TRIGGER_FIRED, TRIGGER_REASONS, and SOFT_ADVISORY from the final block.
  - From Codex-dyn-harness-completeness: Make the case fixture explicit: put mechanical_churn: true and diff_added: 0 in body prose or a fenced block, then put conflicting strict trailers in the final metadata block, and assert DIFF_ADDED, MECHANICAL_CHURN, HARD_TRIGGER_FIRED, TRIGGER_REASONS, and SOFT_ADVISORY from the final block.

### FINDING_11: Plan review loop test may not prove revision path ran
- **Reviewer(s)**: Cursor-dyn-harness-completeness, Codex-dyn-harness-completeness
- **Severity**: important
- **Concern**: The proposed `plan-review-loop` extension can pass by only asserting the loop does not emit `LOOP_STATUS=plan-size-trigger`. If the fixture skips accepted findings or skips revision, a converged or skipped path could satisfy the negative assertion without exercising post-revision size validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-harness-completeness: Require the test to use an accepted-finding multi-round fixture like the existing plan-size test, assert REVISE_STATUS=ok or a sentinel written by the revise stub, assert the final plan contains the optional trailers, then assert LOOP_STATUS is not plan-size-trigger.
  - From Codex-dyn-harness-completeness: Require the test to use an accepted-finding multi-round fixture like the existing plan-size test, assert REVISE_STATUS=ok or a sentinel written by the revise stub, assert the final plan contains the optional trailers, then assert LOOP_STATUS is not plan-size-trigger.
