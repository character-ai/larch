### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/design/test_design_oos.py:231-290
- **Concern**: Relabel test file from MAY_UPDATE to UPDATED. Scenario: parametrize rows and the skip-already-filed assert pin exact em-dash breadcrumb literals; leaving tests optional lets pytest fail after production string updates
- **Proposed resolution**: Change ### MAY_UPDATE to ### UPDATED for python/tests/design/test_design_oos.py and state that all four pinned breadcrumb literals must be updated in the same change ## Findings 1. **correctness** (`python/tests/design/test_design_oos.py:231-290`): The plan marks the test file `### MAY_UPDATE` but `test_step5b_prepare_skip_marks_complete` and the skip-already-filed assert hard-pin the old `oos filing —` breadcrumbs. Those updates are required, not optional; relabel the file `### UPDATED` and list all four literals as mandatory. ## Out-of-scope (worth tracking) 1. **[OUT_OF_SCOPE]** `skills/design/references/design-outline.md:79`: Mandatory Step 1d.7 execution still instructs printing `outline — auto-approved` on `--skip-approve`. Until #6294 updates that line, operators can still see an em-dash even after SKILL.md:249 is fixed. 2. **[OUT_OF_SCOPE]** `skills/design/references/finalize-step5.md:49,53`: Markdown still mirrors the Step 5b warning strings with em-dashes. Python owns runtime output today, but orchestrator-side replay from finalize-step5 could still emit dashes if wrappers are bypassed. 3. **[OUT_OF_SCOPE]** `python/larch/design/design_step5b.py:151`: `_maybe_timing_mark(label="design Step 5 — finalize")` sits outside the plan’s 168–269 window but may surface in timing output; same readability scrub could extend there in a follow-up.




Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: [OUT_OF_SCOPE] design-outline.md still carries the em-dash auto-approve literal after SKILL.md:249 is fixed
- **Description**: [OUT_OF_SCOPE] design-outline.md still carries the em-dash auto-approve literal after SKILL.md:249 is fixed. Scenario: Step 1d.7 carve-out routes auto-approve printing through SKILL.md, so runtime is fixed, but the reference duplicate can confuse future outline edits and drift from the colon form
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/design-outline.md:79
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

