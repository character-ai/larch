### FINDING_1: Unused write_collect_one_nit helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `write_collect_one_nit()` is dead helper code in `skills/design/scripts/test-plan-review-loop.sh`; new tests call `write_collect one_nit` directly, leaving maintainers unclear about the intended helper API.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_2: Important-reset tests omit important-count assertions
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The new streak/reset harness does not fully assert `IMPORTANT_ACCEPTED_COUNT` across `round-summary.env`, stdout, and `.step3-plan-review-result.env`, so regressions in important-finding counting or severity propagation could pass while only `CONVERGENCE_STREAK` remains checked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: Duplicated dispatch stub helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `write_dispatch_round2_degraded` near-duplicates existing one-slot dispatch helpers, increasing maintenance cost if slot manifest behavior changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Dedup test extracts pipeline with brittle awk/eval
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The section-aware dedup test extracts `_run_post_apply_pipeline` via `awk` and `eval`, which can truncate or fail under harmless function formatting changes and produce false positives or unrelated harness failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: Separate important round-2 collect stub duplicates collect modes
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `write_collect_important_round2` duplicates the existing `write_collect` mode pattern instead of extending it, increasing harness duplication without adding capability.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Unplanned redact-tmpdir changes on branch
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Changes to `scripts/redact-tmpdir-paths.sh` are outside the stated #3143 plan/scope and add unrelated tmpdir redaction behavior to the acceptance surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Redundant or imprecise dedup documentation
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `skills/design/references/plan-review.md` contains redundant or potentially misleading dedup prose, including wording that may imply bash-native regex dedup despite the implementation using embedded Python and an intentionally divergent loop-vs-Gate-B behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: H1 Constraints protection can leak into later H2 sections
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: After a `# Constraints` heading, protection does not clear on later `##` non-Constraints headings, so duplicate lines outside the intended Constraints chapter may remain undeduped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: Dedup pipeline test does not exercise full loop post-apply path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Section-aware dedup is tested through an extracted helper rather than a full loop post-apply path, so bugs in emit/validate ordering or snapshot paths may not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Accepted-count threshold reset lacks coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No test covers `ACCEPTED_COUNT` above the convergence threshold resetting the streak, leaving high accepted-count rounds without CI coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: Language-tagged code fences are not recognized
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Fence detection only toggles on a bare triple-backtick line, so language-tagged fences such as ```bash may allow headings inside code blocks to affect Constraints protection and dedup behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_12: Constraints prefix match overprotects related headings
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `startswith("constraints")` also treats headings such as `Constraints-related notes` as protected Constraints sections, widening loop-vs-Gate-B divergence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: macOS var/folders nested temp paths may leak
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Nested segment handling was added for `/tmp` redaction rules but not mirrored for macOS `/var/folders/.../T/...` rules, so nested temp paths may leak into published design logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Unclosed trailing fence disables later Constraints protection
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: An unclosed trailing code fence disables Constraints protection for the rest of the file, so later constraint duplicates may collapse after a missing closing fence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: Two-round streak case omits round-2 streak summary assertion
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The two-round streak case does not assert the round-2 `round-summary.env` `CONVERGENCE_STREAK` value, leaving a minor gap against the plan’s per-round summary coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] run-logs docs may still mention revise.env
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `docs/run-logs.md` may still describe `revise.env` after the allowlist removed it, which could mislead operators about published run-log files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
