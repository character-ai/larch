### [Plan Review] FINDING_5

### FINDING_5: Folding `step-5b` into Step 5c removes last pause boundary before publish
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Concern**: Folding `step-5b` into the Step 5c publish fence removes the last pause boundary before `design-publish.sh`. When `.pause-requested` is set after OOS filing but before publish, the proposed no-pause Step 5c fence still proceeds to write the plan block, publish logs, and possibly rename the issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Keep the step-5b sentinel as a standalone boundary, or add an explicit pause-check before design-publish.sh after writing step-5b if that fence becomes the host


### [Plan Review] FINDING_9

### FINDING_9: `assert_step2a_entry_simple_guard` left unchanged after sentinel relocation
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan moves `.completed/step-2a` and `step-2a.5` out of the Step 2a entry fence but leaves `assert_step2a_entry_simple_guard` unchanged. Implementing items 6–8 removes the literals that guard requires inside the SIMPLE branch of the first fence after `<!-- step:2a —`; `make test-design-structure` fails while `SKILL.md` prose still claims the entry fence is the primary marker site.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Update the harness (and anti-pattern #1 / SIMPLE skip prose) so artifacts stay pinned in the Step 2a entry guard while `step-2a` is asserted in the `### 2a.5` prelude fence and `step-2a.5` in the Step 2b prelude fence; drop the “unchanged” claim on line 61


### [Plan Review] FINDING_10

### FINDING_10: Stale SIMPLE routing and edge-case prose after sentinel relocation
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Edge-case text and multiple SIMPLE routing sites still say Step 2a entry writes `step-2a` / `step-2a.5` in one turn after items 6–8 relocate those writes. Resume/skip prose and anti-pattern #1 can mislead the orchestrator on SIMPLE fresh runs and paused repair even if fences are edited.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Align edge-case § SIMPLE fresh run with the 2a.5 / 2b host-fence contract and update anti-pattern #1, § SIMPLE branch, § 2a.2, and the 2a.5 skip note to name the new write sites


