### FINDING_1: [OUT_OF_SCOPE] Missing redactor failure and empty-output publish harness cases
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-shell-flow-output.txt
- **Severity**: important
- **Concern**: Tests do not cover `redact-secrets.sh` nonzero exit or empty redacted output, so regressions could publish or continue without a valid redacted plan body.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-shell-flow-output.txt: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] Missing exit-4 stdout-fallback harness when result-env write fails
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-shell-flow-output.txt
- **Severity**: important
- **Concern**: Tests do not cover the defects-found path where writing `.design-publish-result.env` fails but stdout still emits `VALIDATE_STATUS=defects-found`, risking orchestrator abort instead of shared exit-4 handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-shell-flow-output.txt: Address the concern above.

### FINDING_3: Validator success gate allows unexpected VALIDATE_STATUS values
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-shell-flow-output.txt
- **Severity**: important
- **Concern**: `design-publish.sh` proceeds after validation unless status is defects-found, empty, not-run, or rc nonzero; an exit-0 validator with an unexpected status could reach redaction and publish.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-shell-flow-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] Removed design flags hard-fail legacy automation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-contract-drift-output.txt
- **Severity**: latent
- **Concern**: `--review-budget` and `--force-validate` are now hard errors rather than legacy no-ops, which can break paused, cached, or older automation that still passes them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-contract-drift-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Exit-4 structure pins are incomplete
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-shell-flow-output.txt, dyn-contract-drift-output.txt
- **Severity**: important
- **Concern**: `test-design-structure.sh` lacks several planned grep anchors for exit-4 handling, `set +e` validator capture, stale result-env quarantine, stdout fallback, and unexpected-rc allowance including 4.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-shell-flow-output.txt, dyn-contract-drift-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] empty-v3-fields does not assert review_budget omission
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-contract-drift-output.txt
- **Severity**: nit
- **Concern**: The `empty-v3-fields` write-run-params test no longer asserts `has("review_budget") == false`, so reintroducing that key could pass this case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-contract-drift-output.txt: Address the concern above.

### FINDING_7: Auto-repair validator handler lacks mechanical prose coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The auto-repair-then-escalate SKILL flow has no structure-test pins for repair cap, full `design-publish.sh` re-capture, or avoiding standalone validate-only repair on `composed-plan.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: --skip-validate can publish command-unsafe plans after operator accept
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--skip-validate` bypasses composed-plan command validation while still allowing `larch:plan` publication, so malicious or defective commands may reach downstream `/implement`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_9: Validator override audit logging no longer mandates redaction
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-redaction-path-output.txt
- **Severity**: important
- **Concern**: The SKILL text dropped the explicit `append-tool-failure.sh --redact` contract for Accept/Override validator logs, risking unredacted `validate-plan-commands.log` content in execution issues, run logs, or escalation surfaces.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-redaction-path-output.txt: Address the concern above.

### FINDING_10: Validator stdout and stderr are merged before KV parsing
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-shell-flow-output.txt
- **Severity**: latent
- **Concern**: `design-publish.sh` captures validator stderr into the same stream as stdout and parses last-wins `VALIDATE_STATUS`, so diagnostic or spoofed stderr KVs could theoretically override the real status.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-shell-flow-output.txt: Address the concern above.

### FINDING_11: Auto-repair may silently alter security-sensitive plan content
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The auto-repair flow can edit plan artifacts without operator prompt, potentially changing security-sensitive content before re-validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Step 2b postplan validation surfaces defects with exit 0
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-contract-drift-output.txt
- **Severity**: important
- **Concern**: `design-postplan-emit.sh` exits 0 with `VALIDATE_STATUS=defects-found`; orchestrators that only check `_postplan_rc` may continue with a defective plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-contract-drift-output.txt: Address the concern above.

### FINDING_13: Publish pause path lacks result-env/status handoff
- **Reviewer(s)**: dyn-contract-drift-output.txt
- **Severity**: important
- **Concern**: `design-publish.sh` `exec`s `design-pause-save.sh` on pre-side-effect pause without first writing `.design-publish-result.env` or stdout KVs, so the orchestrator may treat a valid pause as missing result state and abort.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-drift-output.txt: Address the concern above.

### FINDING_14: Publish driver only checks pause once before combined side-effect tail
- **Reviewer(s)**: dyn-pause-publish-output.txt
- **Severity**: important
- **Concern**: Folding validation, redaction, plan write, publish, rename, and marker creation into one `design-publish.sh` process leaves no pause checkpoints before later side effects, despite docs implying finer-grained protection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pause-publish-output.txt: Address the concern above.

### FINDING_15: Validator log diagnosis can expose unredacted plan content
- **Reviewer(s)**: dyn-redaction-path-output.txt
- **Severity**: important
- **Concern**: The auto-repair/escalation flow tells the orchestrator to diagnose from `VALIDATE_LOG_FILE` without requiring redaction or bounded excerpts, so unredacted command lines or flag values may reach prompts, warnings, or chat.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-redaction-path-output.txt: Address the concern above.

### OOS_1: Mechanical publish and fold path otherwise appears sound
- **Reviewer(s)**: dyn-shell-flow-output.txt, dyn-redaction-path-output.txt
- **Severity**: nit
- **Concern**: Reviewers noted the core fold and redacted publish path correctly validate or skip, redact before issue write, abort on defects or redactor failure, and receive defense-in-depth from `named-block-write.sh`.

### OOS_2: Canonical pause prelude has repo-threading inconsistency
- **Reviewer(s)**: dyn-pause-publish-output.txt
- **Severity**: latent
- **Concern**: The general documented two-line pause prelude omits `${REPO:+--repo "$REPO"}` even though Step 5c includes it; this predates the current fold.

### OOS_3: Dedicated Step 5c pause/REPO structure pins are missing
- **Reviewer(s)**: dyn-pause-publish-output.txt
- **Severity**: latent
- **Concern**: Structure coverage relies on generic pause-fence assertions and existing harness tests rather than dedicated Step 5c pause/REPO greps requested by the plan.

### OOS_4: --skip-validate still runs redaction
- **Reviewer(s)**: dyn-redaction-path-output.txt
- **Severity**: nit
- **Concern**: `--skip-validate` skips command validation only; tests confirm redaction still runs, so it does not itself publish unredacted issue content.

### OOS_5: VALIDATE result KVs expose paths and counts, not log bodies
- **Reviewer(s)**: dyn-redaction-path-output.txt
- **Severity**: nit
- **Concern**: Result-env and stdout fallback expose `VALIDATE_*` counts and log path metadata rather than validator log body content.

### OOS_6: redact-secrets coverage limitations are pre-existing
- **Reviewer(s)**: dyn-redaction-path-output.txt
- **Severity**: latent
- **Concern**: Partial redaction coverage for some secret classes is a pre-existing limitation, not introduced by this fold.
