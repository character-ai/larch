### FINDING_1: Waterfall metadata preservation misses unified-diff candidates
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-revision-path-coverage, Codex-dyn-revision-path-coverage
- **Severity**: important
- **Concern**: `revise-plan-with-waterfall.sh` enforces optional trailer preservation only on file-replacement candidates, while the default waterfall path accepts unified diffs first. A valid unified diff can remove `diff_added`, `diff_deleted`, or `mechanical_churn` while leaving `diff_lines`, pass apply and emit-plan validation, and cause later plan-size checks to fall back to legacy total-churn gating.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: After apply_patch_file (both formats), run the same optional-metadata key-preservation check against the applied plan.txt; extend compose_prompt() unified-diff instructions to require preserving the final metadata block; add a unified-diff rejection case to scripts/test-revise-plan-with-waterfall.sh
  - From Codex-Arch: Add the same original-vs-revised final metadata block validation after any successful apply path, including unified-diff, before run_emit_plan_gate; reject and restore when original strict optional keys are missing or malformed in the revised plan
  - From Cursor-Edge: Reuse the same optional-trailer key check after a unified-diff candidate passes `git apply --check`, or reject/continue scanning candidates; extend `compose_prompt` shared Hard rules to require preserving strict optional trailers when the source plan has them
  - From Codex-Edge: Apply the same original-vs-revised final-metadata-block preservation check after any candidate is applied, before run_emit_plan_gate, and restore/reject on failure; add the preservation regression for unified-diff as well as file-replacement
  - From Cursor-Innovation: Run the same strict final-metadata key check on `$PLAN_FILE` after any successful `apply_patch_file` (before `run_emit_plan_gate`), rejecting and restoring when the snapshot had strict optional keys the revision omits; keep the planned file-replacement regression but do not rely on that path alone
  - From Codex-Innovation: Make trailer-preservation validation run on the post-apply PLAN_FILE for every candidate format before accepting the tier; restore and mark invalid when original strict optional keys are missing or malformed, and add a default unified-diff regression in scripts/test-revise-plan-with-waterfall.sh
  - From Cursor-Pragmatic: Metadata preservation validation is scoped to file-replacement candidates only plan-review-loop.sh invokes revise-plan-with-waterfall without --patch-format so tiers 1-3 use default unified-diff; a winning git apply patch can drop diff_added/diff_deleted/mechanical_churn while keeping a valid final diff_lines trailer, EMIT_PLAN still passes, and the post-revise check-plan-size call can set LOOP_STATUS=plan-size-trigger on legacy total churn Run validate_optional_metadata_preservation on the applied plan.txt immediately after apply_patch_file for both patch formats (compare SNAPSHOT vs revised final metadata keys); extend scripts/test-revise-plan-with-waterfall.sh with a default unified-diff preservation case not only file-replacement
  - From Codex-Pragmatic: Move the preservation check to a common post-apply validation path for every candidate format, or also validate unified-diff candidates, and add a unified-diff regression that drops the trailers
  - From Codex-Requirements: Add a post-apply validation for all waterfall candidate formats that compares the original strict optional trailer keys to the resulting plan before accepting the candidate, or add equivalent unified-diff candidate validation plus a regression where a unified diff drops the trailers and is rejected
  - From Cursor-dyn-revision-path-coverage, Codex-dyn-revision-path-coverage: Validate the resulting plan after every candidate apply, regardless of patch format, against the original strict optional trailer key set before declaring the tier ok; cover this in test-revise-plan-with-waterfall.sh with a default unified-diff rejection plus a preserving winner

### FINDING_2: File-replacement preservation test may not exercise the intended path
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The planned waterfall preservation regression may run under the harness default `unified-diff` mode instead of `--patch-format file-replacement`, so it can miss the file-replacement validation layer it is intended to verify.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Harness the preservation case with `--patch-format file-replacement` (matching existing cases 10b–10d) or an equivalent tier-4-only fixture so rejection/preservation assertions exercise the new validation layer

### FINDING_3: Step 2b does not require relief trailers when relying on deletion or mechanical-churn relief
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: Step 2b only says the new trailers MAY be emitted. Plans that need deletion-heavy or mechanical-churn relief can still emit only `diff_lines`, or incomplete optional metadata, causing `check-plan-size.sh` to hard-trigger on total churn.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Revise the Step 2b instruction to require emitting diff_added when using deletion or mechanical relief, and to emit mechanical_churn: true when the plan self-identifies as trivial mechanical churn; keep trailers optional only for legacy/backward-compatible plans

### FINDING_4: Cross-doc trailer grammar may diverge across consumer-facing surfaces
- **Reviewer(s)**: Cursor-dyn-cross-doc-trailer-contract, Codex-dyn-cross-doc-trailer-contract
- **Severity**: important
- **Concern**: The plan centralizes the full optional trailer grammar and scan contract in `check-plan-size.md`, while other edited surfaces receive only partial summaries or references. This can leave consumers with inconsistent rules for accepted regexes, blank-line stopping, duplicate-key precedence, and `PLAN_LINES` subtraction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-cross-doc-trailer-contract, Codex-dyn-cross-doc-trailer-contract: Add the same compact canonical contract to each touched prose surface: exact three regexes, final contiguous block immediately above final diff_lines, stop at first non-matching line including blanks, malformed lines absent and stop scanning, duplicate keys last in file order closest to diff_lines, and PLAN_LINES subtracts only recognized optional metadata trailers. Keep check-plan-size.md authoritative, but do not rely on cross-reference alone.

### FINDING_5: EMIT_PLAN optional trailer path lacks acceptance coverage
- **Reviewer(s)**: Cursor-dyn-acceptance-test-gap, Codex-dyn-acceptance-test-gap
- **Severity**: important
- **Concern**: The new optional trailer format is not tested through `ACTION=EMIT_PLAN`. A plan containing optional trailers above final `diff_lines` could be rejected or produce incorrect `diff-lines.txt` output while the proposed check-plan-size and design-structure tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-acceptance-test-gap, Codex-dyn-acceptance-test-gap: Add one test-emit-plan.sh or test-design-driver.sh case using optional trailers above final diff_lines and assert EMIT_PLAN_STATUS=ok DIFF_LINES=<total> and diff-lines.txt=<total>

### FINDING_6: Gate preservation contract is prose-only and under-tested
- **Reviewer(s)**: Cursor-dyn-acceptance-test-gap, Codex-dyn-acceptance-test-gap
- **Severity**: latent
- **Concern**: Gate A and Gate B preservation acceptance is not mechanically pinned across the prompt surfaces that perform or direct plan rewrites. Implementations can update parser and waterfall behavior while omitting rewrite instructions that preserve or recompute optional trailers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-acceptance-test-gap, Codex-dyn-acceptance-test-gap: Extend scripts/test-design-structure.sh with contains checks for diff_added/diff_deleted/mechanical_churn preservation language in skills/design/SKILL.md, references/approval-gates.md, and references/discussion-rounds.md

### FINDING_7: Plan-review loop lacks regression coverage for revised mechanical plans
- **Reviewer(s)**: Cursor-dyn-acceptance-test-gap, Codex-dyn-acceptance-test-gap
- **Severity**: important
- **Concern**: The failure mode where a revised mechanical plan returns `LOOP_STATUS=plan-size-trigger` is only a spot-check. A regression in the in-loop post-apply path could hard-trigger despite `mechanical_churn: true` without failing the named automated tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-acceptance-test-gap, Codex-dyn-acceptance-test-gap: Convert the spot-check to a test-plan-review-loop.sh case: stub a revision that writes diff_added over threshold plus mechanical_churn true and assert the loop does not emit LOOP_STATUS=plan-size-trigger

### FINDING_8: Gate A and Gate B direct rewrites lack mechanical trailer preservation checks
- **Reviewer(s)**: Cursor-dyn-revision-path-coverage, Codex-dyn-revision-path-coverage
- **Severity**: important
- **Concern**: Gate A and Gate B direct rewrite paths can replace `plan.txt` before emit-plan and plan-size checks without mechanically validating that preexisting optional trailers were preserved or recomputed. If those rewrites drop metadata, later checks cannot distinguish the omission from legacy plans.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-revision-path-coverage, Codex-dyn-revision-path-coverage: Add a minimum post-rewrite check in the Gate A and Gate B rewrite instructions: snapshot the original strict optional trailer keys before the Write/dedup rewrite, then require the revised final metadata block to preserve those keys or explicitly recompute them before ACTION=EMIT_PLAN and Step 2b.5
