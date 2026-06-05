### [Plan Review] FINDING_2

### FINDING_2: Scope anchor path may be unreadable to reviewers
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: Passing the original feature path directly can point reviewers or voters at a file outside their sandbox-visible roots, silently degrading scope anchoring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Stage the original feature into a regular file under DESIGN_TMPDIR before brainstorm merging and pass that staged path to the new scout reviewer voter and tally scope-anchor flags; add a regression where the original feature lives outside DESIGN_TMPDIR


### [Plan Review] FINDING_12

### FINDING_12: Render plan-review prompt compatibility lacks byte-level golden coverage
- **Reviewer(s)**: Cursor-dyn-compatibility-harness
- **Severity**: important
- **Concern**: The promised unchanged legacy/default renderer behavior is not pinned by byte-equality tests, allowing whitespace, ordering, or default-path drift to pass grep-only checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-compatibility-harness: Extend test-plan-review-prompt.sh with a case that captures pre-change output once and asserts cmp -s for the full legacy invocation (all current required flags, omitting --feature-file and --baseline-plan-file)


### [Plan Review] FINDING_13

### FINDING_13: Render voter prompt compatibility lacks byte-level golden coverage
- **Reviewer(s)**: Cursor-dyn-compatibility-harness
- **Severity**: important
- **Concern**: The no-flag default output promise for `render-voter-prompt.sh` lacks a pinned cmp/golden mechanism, so default-path consumers can regress silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-compatibility-harness: Add a case that runs render-voter-prompt.sh with the existing required argv only, compares stdout to a committed golden file (or cmp against output captured before the scope-anchor block), matching the cmp pattern in scripts/test-render-run-summary.sh


### [Plan Review] FINDING_14

### FINDING_14: Dispatch plan-voter prompt omission path is not byte-pinned
- **Reviewer(s)**: Cursor-dyn-compatibility-harness
- **Severity**: important
- **Concern**: Tests may only assert absence of new scope-anchor prose when `--scope-anchor-file` is omitted, not that the entire generated prompt remains unchanged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-compatibility-harness: Record healthy-run codex/cursor/claude prompt files without --scope-anchor-file, rerun dispatch without the flag, and cmp -s each prompt; add a second case with --scope-anchor-file that fails cmp and greps the anchor block


### [Plan Review] FINDING_17

### FINDING_17: Cross-stage scope-anchor harness bullets are under-specified
- **Reviewer(s)**: Cursor-dyn-compatibility-harness
- **Severity**: important
- **Concern**: New harness items for dedup, aggregation fallback, and prompt injection protections are described as outcomes without concrete inputs, script entrypoints, or pass predicates, risking weak grep-only coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-compatibility-harness: Spell each bullet as a named case with explicit inputs, invoked script(s), and pass predicates (e.g. dedup output still matches is_scope_reduction_block; aggregate-findings --input-mode plan returns validation-failed; render prompts use cmp or required substrings plus forbidden drift-block when baseline equals plan)


### [Plan Review] FINDING_18

### FINDING_18: Non-design voter prompts lack leak guard
- **Reviewer(s)**: Codex-dyn-compatibility-harness
- **Severity**: important
- **Concern**: Shared voter renderer changes could leak plan-review-only scope-anchor prose or `[SCOPE-REDUCTION]` rubric into `/review` or `/implement` code-voter prompts because only design/plan-voter tests are covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-compatibility-harness: Add a minimal negative assertion in the existing code-voter happy prompt loop that no prompt contains --scope-anchor-file scope-anchor prose or [SCOPE-REDUCTION].### OOS_1:
- **Description**: Step 3 prose still claims brainstorm-merged feature context is passed to scout and panel. Scenario: After scope-anchor wiring lands, inline orchestration text still describes the pre-change contract and can mislead debugging
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:1015
- **Phase**: design


