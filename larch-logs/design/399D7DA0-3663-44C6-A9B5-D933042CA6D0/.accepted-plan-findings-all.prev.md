### FINDING_1: close-stale lacks explicit orchestration step and approval gate
- **Reviewer(s)**: Cursor-Arch, Codex-Pragmatic
- **Severity**: important
- **Concern**: The plan wires `close-stale` into oos-2 but does not define when the orchestrator should invoke it relative to oos-4 operator approval or oos-5 apply, and it introduces a mutating close path before the existing oos-4 approval step. A run can either finish with fully-stale sources left open because closure timing is undefined, or close source issues without operator confirmation if stale items are misclassified during actuality check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit SKILL step (for example oos-2 tail or a short pre-oos-5 step): collect fully-stale source numbers during oos-2, then after the oos-4 scheme is approved call combine-issues close-stale --repo "$REPO" --issues "<csv>" --reason not planned [--comment-file ...] before dependency phases; state whether operator confirmation is required.
  - From Codex-Pragmatic: Collect stale-only source issues in oos-2, show them in the oos-4 proposal, and invoke combine-issues close-stale only after explicit approval in the apply or close phase.


### FINDING_2: oos-2 global all-stale halt leaves fully-stale sources open
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-dyn-cli-wire-contract
- **Severity**: important
- **Concern**: oos-2 still halts with "nothing to combine" when every item in every fetched `[OOS]` issue is stale, and mixed runs (some fully-stale sources plus active items) never close fully-stale sources because they never enter apply or close-sources. The new `close-stale` branch is not reconciled with the existing global halt or with per-issue close timing, so fully-stale sources such as #4253 and #4224 can remain open and invert the skill goal of reducing open issue count.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In oos-2, replace the global stop: after actuality, close-stale each fully stale source (no combined host), then stop with a tally. Do not leave them open.
  - From Cursor-Pragmatic: Replace line 163 halt with: collect per-issue fully-stale sources during the loop; batch `close-stale` before oos-3 when the list is non-empty; if no actual items remain after closes, stop with a tally. Continue combination when any actual items remain.
  - From Cursor-dyn-cli-wire-contract: In oos-2 replace the global stop with collecting fully-stale source numbers and invoking `combine-issues close-stale` (batched or per issue). Continue only when no actual items remain.


### FINDING_3: close-stale --reason accepts values gh rejects
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `close-stale` accepts arbitrary `--reason` text but `gh issue close` only allows `completed` or `not planned`. An operator or SKILL example passing free text (e.g. `stale`) makes `gh issue close` fail; stale issues stay open with `PARTIAL=true`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Validate --reason against {completed, not planned} before any close (mirror gh). Document not planned for stale closure in SKILL oos-2.


### FINDING_4: oos-5 SOURCE_TO_COMBINED_JSON_FRAGMENT merge omits multi-host array upgrade
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: oos-5 fragment merge rules only show scalar mappings per apply. When one source is split across combined hosts, blind merge overwrites earlier fragments (e.g. `{"1":99}` then `{"1":100}`) instead of promoting to a sorted unique array, breaking `plan-inherited` remap and `close-eligible` partitioning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Specify merge: first fragment sets scalar; repeat key upgrades to sorted unique array per _parse_source_to_combined. Add a test with two defer-close applies for the same source.
  - From Cursor-Requirements: Mandate merge-on-accumulate: first fragment sets scalar; later fragment for same key promotes to sorted unique array per _parse_source_to_combined


### FINDING_5: _classify_edge blanket non-open blocker guard blocks satisfied classification
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: Current `_classify_edge` lines 346-347 classify any non-open blocker as `unknown` before a `satisfied` check for closed blockers can run. Adding a satisfied branch without removing or reordering that guard leaves closed blockers permanently `unknown`, preserving the primary bug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Remove or replace blocker issue is not known open with: closed -> satisfied; other non-open -> unknown; then existing safe/exception for open blockers.
  - From Cursor-Requirements: Reorder _classify_edge: after metadata exists, return satisfied when blocker state is closed; only then apply unknown for other non-open blocker states; keep open-blocker safe/exception logic unchanged


### FINDING_7: close-stale SKILL contract omits required --reason and comment-file content
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Goal A adds `close-stale` with required `--reason` and optional `--comment-file`, but oos-2 only says to use `close-stale` without specifying reason or comment content. The orchestrator must guess values, so stale closure is not deterministic or auditable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Document --reason not planned and require a redacted comment-file summarizing that issue's stale discard lines before invoking close-stale


### FINDING_9: SKILL omits close-stale output parsing and tally integration
- **Reviewer(s)**: Codex-dyn-cli-wire-contract
- **Severity**: important
- **Concern**: `close-stale` defines `CLOSED_ISSUES` and `PARTIAL` output, but the SKILL update omits parsing and tally instructions. When `close-stale` skips or fails one stale issue it returns zero with `PARTIAL=true` and `WARNING`, but oos docs may still count only `close-sources` output and omit left-open stale sources from source-closed and left-open summaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-cli-wire-contract: Add oos-2/oos-10 instructions to invoke close-stale with required args, parse CLOSED_ISSUES and PARTIAL from stdout plus WARNING from stderr, and include close-stale results in source-closed and left-open tallies


### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/skills/combine-issues/SKILL.md:163-165
- **Concern**: [SCOPE-REDUCTION] oos-2 global all-stale terminal branch not revised alongside close-stale. Scenario: Plan adds per-source close-stale but leaves the existing global branch that prints All [OOS] items are stale — nothing to combine and stops; after close-stale runs that message hides stale closures and can still read as zero net reduction
- **Proposed resolution**: Replace line 163-165 with a terminal branch that runs only after per-source close-stale, reports CLOSED_ISSUES from close-stale, then exits without entering oos-3 when no actual items remain



