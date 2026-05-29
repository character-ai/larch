### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/revise-plan-with-waterfall.sh:28,575-617
- **Concern**: Trailer-preservation validation is scoped to file-replacement only while default patch format is unified-diff. Scenario: plan-review-loop.sh calls revise-plan-with-waterfall.sh with default PATCH_FORMAT=unified-diff; tiers 1-3 can git-apply a patch that drops diff_added/diff_deleted/mechanical_churn while leaving a valid final diff_lines, pass emit-plan, and later check-plan-size falls back to diff_lines > 1500 — undoing mechanical-churn downgrade after between-round revisions
- **Proposed resolution**: After apply_patch_file (both formats), run the same optional-metadata key-preservation check against the applied plan.txt; extend compose_prompt() unified-diff instructions to require preserving the final metadata block; add a unified-diff rejection case to scripts/test-revise-plan-with-waterfall.sh

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/revise-plan-with-waterfall.sh:575-638
- **Concern**: Waterfall preservation enforcement only targets file-replacement candidates. Scenario: An original plan with diff_added/mechanical_churn trailers can be revised by a valid unified diff that drops those trailers; emit-plan still passes because diff_lines remains final, and the next check-plan-size run falls back to total diff_lines, restoring the hard gate the PR is meant to avoid
- **Proposed resolution**: Add the same original-vs-revised final metadata block validation after any successful apply path, including unified-diff, before run_emit_plan_gate; reject and restore when original strict optional keys are missing or malformed in the revised plan

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/revise-plan-with-waterfall.sh:543-617
- **Concern**: Trailer preservation is only validated for file-replacement candidates, but tiers 1–3 try unified-diff first. Scenario: An accepted unified-diff revision can drop `diff_added` / `mechanical_churn` while lowering `diff_lines`; post-apply then sees no hard trigger and no `SOFT_ADVISORY`, silently undoing mechanical gating (failure mode 4 on the primary path)
- **Proposed resolution**: Reuse the same optional-trailer key check after a unified-diff candidate passes `git apply --check`, or reject/continue scanning candidates; extend `compose_prompt` shared Hard rules to require preserving strict optional trailers when the source plan has them

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/revise-plan-with-waterfall.sh:575-638
- **Concern**: Plan only enforces optional-trailer preservation for file-replacement candidates, while the primary waterfall path accepts unified diffs after header/apply/emit checks. Scenario: An original plan with diff_added/diff_deleted/mechanical_churn can receive a valid unified diff that removes those trailers but keeps final diff_lines; current checks would accept it, silently reverting the revised plan to legacy total-churn gating
- **Proposed resolution**: Apply the same original-vs-revised final-metadata-block preservation check after any candidate is applied, before run_emit_plan_gate, and restore/reject on failure; add the preservation regression for unified-diff as well as file-replacement

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/revise-plan-with-waterfall.sh:543-638
- **Concern**: Waterfall trailer preservation is scoped to file-replacement validation only. Scenario: Default `--patch-format` is `unified-diff` (tiers 1–3); a winning git-apply revision can drop `diff_added` / `diff_deleted` / `mechanical_churn` while keeping a valid final `diff_lines:`, so `plan-review-loop.sh` re-check can false-trigger `plan-size-trigger` on deletion-heavy plans
- **Proposed resolution**: Run the same strict final-metadata key check on `$PLAN_FILE` after any successful `apply_patch_file` (before `run_emit_plan_gate`), rejecting and restoring when the snapshot had strict optional keys the revision omits; keep the planned file-replacement regression but do not rely on that path alone

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/revise-plan-with-waterfall.sh:575-638
- **Concern**: Optional trailer preservation is only enforced for file-replacement candidates, but the waterfall’s default path is unified-diff. Scenario: An original plan with diff_added/diff_deleted/mechanical_churn can accept a unified diff that drops those trailers while keeping diff_lines; run_emit_plan_gate still passes, then the next check-plan-size call falls back to legacy diff_lines and can re-trigger plan-size
- **Proposed resolution**: Make trailer-preservation validation run on the post-apply PLAN_FILE for every candidate format before accepting the tier; restore and mark invalid when original strict optional keys are missing or malformed, and add a default unified-diff regression in scripts/test-revise-plan-with-waterfall.sh

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/revise-plan-with-waterfall.sh:463-471
- **Concern**: skills/design/scripts/revise-plan-with-waterfall.sh:575-638. Scenario: scripts/test-revise-plan-with-waterfall.sh:1101-1145
- **Proposed resolution**: Metadata preservation validation is scoped to file-replacement candidates only plan-review-loop.sh invokes revise-plan-with-waterfall without --patch-format so tiers 1-3 use default unified-diff; a winning git apply patch can drop diff_added/diff_deleted/mechanical_churn while keeping a valid final diff_lines trailer, EMIT_PLAN still passes, and the post-revise check-plan-size call can set LOOP_STATUS=plan-size-trigger on legacy total churn Run validate_optional_metadata_preservation on the applied plan.txt immediately after apply_patch_file for both patch formats (compare SNAPSHOT vs revised final metadata keys); extend scripts/test-revise-plan-with-waterfall.sh with a default unified-diff preservation case not only file-replacement

### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/revise-plan-with-waterfall.sh:614-623
- **Concern**: Optional trailer preservation is only enforced for file-replacement candidates. Scenario: A primary unified-diff tier can remove diff_added diff_deleted mechanical_churn while leaving diff_lines valid, so the revised plan falls back to legacy total-churn gating and can re-trigger Split/Cancel
- **Proposed resolution**: Move the preservation check to a common post-apply validation path for every candidate format, or also validate unified-diff candidates, and add a unified-diff regression that drops the trailers

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:101-104
- **Concern**: Waterfall preservation regression omits `--patch-format file-replacement`. Scenario: New validation is specified only for file-replacement candidates in `revise-plan-with-waterfall.sh`, but the harness default is `unified-diff`; a new case run under the default path never executes the validator and can pass while trailer-dropping patches are still accepted
- **Proposed resolution**: Harness the preservation case with `--patch-format file-replacement` (matching existing cases 10b–10d) or an equivalent tier-4-only fixture so rejection/preservation assertions exercise the new validation layer

### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:805
- **Concern**: Step 2b only MAY emit the new trailers, so deletion-heavy or mechanical plans can still fall back to total-churn gating. Scenario: A future #3118-style plan can keep only diff_lines or emit diff_deleted without diff_added, and check-plan-size.sh will still hard-trigger on diff_lines > 1500 despite the feature goal that deletions/mechanical churn avoid Split/Cancel
- **Proposed resolution**: Revise the Step 2b instruction to require emitting diff_added when using deletion or mechanical relief, and to emit mechanical_churn: true when the plan self-identifies as trivial mechanical churn; keep trailers optional only for legacy/backward-compatible plans

### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/revise-plan-with-waterfall.sh:575-617
- **Concern**: Waterfall preservation enforcement is planned only for file-replacement candidates, leaving the default unified-diff path able to drop optional trailers. Scenario: A unified diff candidate can delete diff_added/diff_deleted/mechanical_churn while retaining final diff_lines; git apply and EMIT_PLAN still pass, so a mechanical/deletion-heavy plan regresses to legacy hard gating after the accepted revision
- **Proposed resolution**: Add a post-apply validation for all waterfall candidate formats that compares the original strict optional trailer keys to the resulting plan before accepting the candidate, or add equivalent unified-diff candidate validation plus a regression where a unified diff drops the trailers and is rejected

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-cross-doc-trailer-contract, Codex-dyn-cross-doc-trailer-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:44-68
- **Concern**: The plan only requires the full trailer grammar and scan contract in check-plan-size.md; SKILL.md, flags.md, approval-gates.md, and discussion-rounds.md get partial summaries or references.. Scenario: This can land with divergent consumer docs: SKILL.md only names mechanical_churn: true, flags.md omits blank-stop and last-match-wins, approval-gates.md prefers pointing elsewhere, and discussion-rounds.md only says preserve/recompute. A reader of one surface can miss ^mechanical_churn: (true|false)$, blank lines stopping the block, closest-to-diff_lines duplicate wins, or PLAN_LINES subtracting only recognized optional trailers.
- **Proposed resolution**: Add the same compact canonical contract to each touched prose surface: exact three regexes, final contiguous block immediately above final diff_lines, stop at first non-matching line including blanks, malformed lines absent and stop scanning, duplicate keys last in file order closest to diff_lines, and PLAN_LINES subtracts only recognized optional metadata trailers. Keep check-plan-size.md authoritative, but do not rely on cross-reference alone.

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-acceptance-test-gap, Codex-dyn-acceptance-test-gap
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:111-160; skills/design/scripts/test-emit-plan.sh:22-50; skills/design/scripts/test-design-driver.sh:37-42
- **Concern**: New optional trailer format is not exercised through ACTION=EMIT_PLAN despite acceptance claiming emit-plan.sh design-driver.sh diff-lines.txt contracts unchanged. Scenario: A plan emitted with diff_added/diff_deleted/mechanical_churn above final diff_lines could be rejected or could write the wrong diff-lines.txt while the proposed check-plan-size/design-structure tests still pass; existing emit tests only cover bare diff_lines
- **Proposed resolution**: Add one test-emit-plan.sh or test-design-driver.sh case using optional trailers above final diff_lines and assert EMIT_PLAN_STATUS=ok DIFF_LINES=<total> and diff-lines.txt=<total>

### FINDING_14:
- **Reviewer(s)**: Cursor-dyn-acceptance-test-gap, Codex-dyn-acceptance-test-gap
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:52-73,151-160; scripts/test-design-structure.sh:219-236,330-354
- **Concern**: Gate A/Gate B preservation acceptance is prose-only; proposed test-design-structure additions do not pin approval-gates.md or discussion-rounds.md preservation anchors. Scenario: An implementation can update check-plan-size and waterfall validation but omit the prompt contracts that tell discussion and Gate B rewrites to preserve/recompute trailers; accepted mechanical plans may collapse back to legacy total churn
- **Proposed resolution**: Extend scripts/test-design-structure.sh with contains checks for diff_added/diff_deleted/mechanical_churn preservation language in skills/design/SKILL.md, references/approval-gates.md, and references/discussion-rounds.md

### FINDING_15:
- **Reviewer(s)**: Cursor-dyn-acceptance-test-gap, Codex-dyn-acceptance-test-gap
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:136-147; skills/design/scripts/plan-review-loop.sh:638-646; skills/design/scripts/test-plan-review-loop.sh:1290-1318
- **Concern**: Failure mode for revised mechanical plans returning plan-size-trigger is left as a spot-check. Scenario: plan-review-loop.sh consumes only HARD_TRIGGER_FIRED after revision; a regression in the in-loop post-apply path can surface LOOP_STATUS=plan-size-trigger for mechanical_churn true and would not fail the named automated tests
- **Proposed resolution**: Convert the spot-check to a test-plan-review-loop.sh case: stub a revision that writes diff_added over threshold plus mechanical_churn true and assert the loop does not emit LOOP_STATUS=plan-size-trigger

### FINDING_16:
- **Reviewer(s)**: Cursor-dyn-revision-path-coverage, Codex-dyn-revision-path-coverage
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/revise-plan-with-waterfall.sh:543-638; skills/design/scripts/revise-plan-with-waterfall.md:69-75
- **Concern**: Waterfall trailer-preservation validation is scoped to file-replacement candidates while default unified-diff winners can still drop optional trailers. Scenario: revise-plan-with-waterfall.sh defaults to unified-diff and accepts the first patch that targets plan.txt, applies cleanly, keeps one plan heading, and passes ACTION=EMIT_PLAN; a patch that deletes diff_added/diff_deleted/mechanical_churn but leaves diff_lines can win before tier-4 file-replacement validation ever runs, so the next check-plan-size.sh falls back to legacy total churn
- **Proposed resolution**: Validate the resulting plan after every candidate apply, regardless of patch format, against the original strict optional trailer key set before declaring the tier ok; cover this in test-revise-plan-with-waterfall.sh with a default unified-diff rejection plus a preserving winner

### FINDING_17:
- **Reviewer(s)**: Cursor-dyn-revision-path-coverage, Codex-dyn-revision-path-coverage
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md:131-156; skills/design/references/discussion-rounds.md:126
- **Concern**: Gate A and Gate B direct rewrite paths rely on prompt prose rather than a mechanical preservation check before re-running plan-size. Scenario: Gate B apply-all, one-by-one, and the shared dedup rewrite all replace plan.txt before ACTION=EMIT_PLAN and Step 2b.5; Gate A discussion can also revise plan.txt directly. If those rewrites drop optional trailers, check-plan-size.sh cannot know the old metadata existed and will use legacy diff_lines behavior
- **Proposed resolution**: Add a minimum post-rewrite check in the Gate A and Gate B rewrite instructions: snapshot the original strict optional trailer keys before the Write/dedup rewrite, then require the revised final metadata block to preserve those keys or explicitly recompute them before ACTION=EMIT_PLAN and Step 2b.5
