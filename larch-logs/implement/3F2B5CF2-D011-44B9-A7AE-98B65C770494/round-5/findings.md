### FINDING_1: tier-4 status merge ranking is inverted
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `tier4_rank` / `merge_tier4_status` can select a less severe tier-4 outcome over a worse one, so final tier-4 status may be misleading or mapped incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_2: file-replacement extraction drops legitimate standalone fences
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `extract_file_replacement_candidate` drops every line equal to ``` inside `## Plan` blocks, which can truncate valid plan content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_3: stale numbered candidate patches can survive re-extract
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: only the primary `*-candidate.patch` is removed before re-extraction, so stale numbered candidates may still be selected if they pass `git apply --check`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_4: diff-git-only patches are rejected by header validation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `validate_unified_headers` requires `---` / `+++` headers even when a valid `diff --git a/plan.txt b/plan.txt` header is present, causing unnecessary fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] passive summaries omit ok-fallback
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Gate passive-summary prose/table does not mention `ok-fallback`, so operators may miss that file replacement was used instead of the standard diff path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] missing end-to-end ok-fallback integration coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: multi-round integration does not exercise the real revise waterfall with tier-4 `ok-fallback`, so wiring regressions between `revise-plan-with-waterfall.sh` and `plan-review-loop.sh` could pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: tier-4 success tests only cover Codex winning
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: tier-4 fallback tests do not cover Cursor or Claude winning after earlier tier-4 failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: snapshot-failure harness does not assert revise.env preservation
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: the snapshot-failure test does not verify that `revise.env` survives failure snapshotting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: python3 dependency in case8d is unguarded
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: case8d requires `python3` without checking availability, so the harness can fail before testing the intended path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: tier-4 file replacement can overwrite plan with weak validation
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: tier-4 file replacement can fully overwrite `plan.txt` after diff tiers fail with only structural/trailer validation, allowing accepted edits or required coverage to be dropped while continuing as `ok-fallback`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_11: file-replacement extractor accepts ambiguous multiple plan blocks
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: file-replacement extraction keeps the last `## Plan` block with a `diff_lines` trailer, so appended plan blocks can supersede the intended revision.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: git apply --recount can accept miscounted hunks
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: using `git apply --recount` relaxes hunk header integrity and may apply miscounted or ambiguous patches that strict mode would reject.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: multi-candidate unified-diff selection can choose partial or unintended patches
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-awk-diff-extraction-output.txt
- **Severity**: important
- **Concern**: the unified-diff candidate path selects the first valid candidate according to filesystem/glob order rather than reliably choosing the best or documented encounter-order patch, so an early/minimal/partial candidate can win.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-awk-diff-extraction-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] emit-plan lacks plan body safety checks
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `EMIT_PLAN` checks only the `diff_lines` trailer and not plan body safety, leaving malicious plan text as a pre-existing downstream risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_15: tier-4 overwrites earlier raw launcher outputs
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: tier-4 reuses the same launcher output filenames, so corrupt tier 1-3 outputs can be lost from forensic artifacts after fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: post-apply failure can conflict with ok-fallback round summary
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `revise_status=ok-fallback` can coexist with terminal `LOOP_STATUS=emit-plan-failed`, making round summary and Gate B status disagree unless the split is aligned or documented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: implementation diverges from explicit plan constraint for file replacement
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: the plan required file-replacement `extract_patch` to remain `cp "$output" "$patch"`, but implementation uses `extract_file_replacement_candidate`; this may be justified but needs an approved plan amendment or conditional compliance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_18: inter-hunk blank-line extraction truncates patches with multiple blank lines
- **Reviewer(s)**: dyn-awk-diff-extraction-output.txt
- **Severity**: nit
- **Concern**: the awk extractor only peeks one line ahead for blank lines between hunks, so two consecutive blank lines can truncate later hunks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-awk-diff-extraction-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] reviewed commit and ok-fallback wiring notes
- **Reviewer(s)**: dyn-awk-diff-extraction-output.txt
- **Severity**: nit
- **Concern**: reviewer noted branch commit context and stated that the awk extractor and tier-4/`ok-fallback` wiring match the issue plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-awk-diff-extraction-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] candidate start and false-start behavior validated
- **Reviewer(s)**: dyn-awk-diff-extraction-output.txt
- **Severity**: nit
- **Concern**: reviewer noted that `is_candidate_start` and early false-start advancement behave as intended for reviewed cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-awk-diff-extraction-output.txt: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] duplicate extraction is acceptable when validation order is reliable
- **Reviewer(s)**: dyn-awk-diff-extraction-output.txt
- **Severity**: nit
- **Concern**: reviewer noted that fenced-block plus full-response scanning can emit duplicate candidates by design, and that the risky part is validation order rather than double scanning alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-awk-diff-extraction-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] no-candidate behavior is deterministic
- **Reviewer(s)**: dyn-awk-diff-extraction-output.txt
- **Severity**: nit
- **Concern**: reviewer noted deterministic behavior when no candidates are found.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-awk-diff-extraction-output.txt: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] trailing markdown list lines remain a pre-existing fragility
- **Reviewer(s)**: dyn-awk-diff-extraction-output.txt
- **Severity**: nit
- **Concern**: trailing markdown `- item` lines are only excluded if preceded by a blank line; without that blank, they can be treated as hunk body lines, which reviewer classified as pre-existing LLM-format fragility.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-awk-diff-extraction-output.txt: Address the concern above.
