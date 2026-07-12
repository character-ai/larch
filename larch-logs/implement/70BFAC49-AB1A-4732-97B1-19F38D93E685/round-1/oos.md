### FINDING_4: [OUT_OF_SCOPE] Architectural-guidelines injection omits G-Fix-2 Guidance
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-bug-fix-prompts
- **Severity**: minor
- **Concern**: Pre-existing parser behavior strips `Guidance:` bullets from injected architectural-guidelines blocks. Reviewers therefore see G-Fix-2 Why/Deviate text but not its executable-reproduction Guidance text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-bug-fix-prompts: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_5: [OUT_OF_SCOPE] Rendered architectural-guidelines output is not pinned for G-Fix-2
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: The harness pins G-Fix-2 in the source file but does not verify that the rendered architectural-guidelines output contains the G-Fix-2 entry. A parser regression could omit it while the file-level assertion still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Assert a G-Fix-2 fragment inside `$plan_review_out` when guidelines are rendered.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_6: [OUT_OF_SCOPE] Plan-review `[BUG]` detection uses a literal title substring
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Plan-review `[BUG]` detection uses a literal substring while `bug_title_match` normalizes lifecycle prefixes and case, so retitled or case-variant bug titles may receive inconsistent close-criteria treatment. This is a pre-existing convention and the feature specification chose literal `[BUG]`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_7: [OUT_OF_SCOPE] Non-generic specialist renders omit the class-or-instance instruction
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The class-or-instance instruction is omitted for non-generic specialist renders, including test-only `[BUG]` diffs. The plan explicitly scoped delivery to the generic diff-specialist path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_8: [OUT_OF_SCOPE] Unknown diff modes can raise a `KeyError`
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: `_specialist_tagging` indexes `table[diff_mode]` without a fallback. An unexpected `diff_mode` could therefore break review rendering. This is a pre-existing pattern unchanged by the branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_9: [OUT_OF_SCOPE] Plan-review scoping sentence is not pinned by the invariant harness
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The plan-review overbroad-scoping guard sentence is not pinned by prompt-template invariant tests. A future edit could remove the scoping line while retaining the main harness/no-repro checklist, causing reviewers to over-require recovery reproduction on ordinary or non-[BUG] plans.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add assert_contains pins for the scoping sentence in test-prompt-template-invariants.sh and optionally in test_render_plan_review_tsv_contract_hardening.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_10: [OUT_OF_SCOPE] Design acceptance does not mechanically verify reviewer behavior
- **Reviewer(s)**: dyn-dyn-bug-fix-prompts
- **Severity**: minor
- **Concern**: The feature acceptance condition expects a structure harness to fail checklist expectations for a `[BUG]` recovery-surface plan without a reproduction, but the implementation only asserts that advisory text is present. Operational close criteria remain prompt-dependent without a mechanical behavior backstop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bug-fix-prompts: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_11: [OUT_OF_SCOPE] Specialist agent output formats may conflict with wrapper instructions
- **Reviewer(s)**: dyn-dyn-bug-fix-prompts
- **Severity**: minor
- **Concern**: Hand-maintained specialist agents provide their own output-format sections while `_specialist_tagging()` appends a conflicting `### In-Scope Findings` bullet contract. The new `[BUG]` line is added only to the wrapper, increasing the chance that reviewers follow the agent body format and treat the class-or-instance request as non-binding metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bug-fix-prompts: Address the concern above.
Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false
