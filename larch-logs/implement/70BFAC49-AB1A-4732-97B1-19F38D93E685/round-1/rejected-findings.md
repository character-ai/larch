### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: Plan-review recovery-scope guard is not fully pinned
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-bug-fix-prompts
- **Severity**: minor
- **Concern**: The prompt-template harness checks the affirmative harness/no-repro wording but does not fully pin the negative-scope guard or recovery-surface enumeration in the rendered plan-review prompt. A regression could leave reviewers applying recovery-reproduction requirements to ordinary or non-[BUG] plans while the existing invariant tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-bug-fix-prompts: Add an `assert_contains` against `$plan_review_out` for the full recovery-surface enumeration (or the entire checklist sentence), and optionally a `assert_not_contains` smoke run with a non-`[BUG]` feature fixture to ensure the advisory line remains conditional in wording.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: G-Fix-2 recovery-surface list has duplicated sources of truth
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-bug-fix-prompts
- **Severity**: minor
- **Concern**: The G-Fix-2 recovery-surface enumeration is duplicated in `ARCHITECTURAL_GUIDELINES.md` and `render_plan_review_main`, allowing the guideline and plan-review trigger list to drift while per-file assertions continue to pass. The architectural-guidelines parser also omits the canonical Guidance text from injected output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Centralize the surface list in one shared constant or fragment, or add a cross-file equality assert in the invariants harness.
  - From dyn-dyn-bug-fix-prompts: Derive the checklist parenthetical from the committed G-Fix-2 Guidance bullet at render time (or extend `parse_guideline_entries()` to retain Guidance for G-Fix entries), and pin equality between the rendered prompt and the guideline file in `test-prompt-template-invariants.sh`.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: `[BUG]` class-or-instance guidance is limited to generic specialist tagging
- **Reviewer(s)**: dyn-dyn-bug-fix-prompts
- **Severity**: minor
- **Concern**: The new `[BUG]` class-or-instance instruction is wired only into the `generic` diff-mode row. Homogeneous `test-only`, `docs-only`, or `generated-only` diffs can receive specialist tagging bodies without the requirement, even though those paths are used by the live panel reviewers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bug-fix-prompts: Add the same advisory `[BUG]` class-or-instance sentence to the `test-only` (and, if desired, `docs-only` / `generated-only`) tagging bodies, or stop forwarding a non-`generic` `--diff-mode` for `[BUG]`-sourced reviews so the generic wrapper always carries the rule; add a `test_specialist_tagging_includes_bug_class_or_instance_instruction` counterpart that classifies a harness-only fixture diff as `test-only` and asserts the instruction is still present.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0
