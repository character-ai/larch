### FINDING_14: security: skills/implement/scripts/post-tracking-issue.sh:64-67,94
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] RUN_ID from parent-issue.md session-id or session-env is not re-validated after the CLI --run-id check before embedding in the metadata HTML comment marker. A same-UID tamperer sets parent-issue.md RUN_ID=x--> in a caller that omits --run-id; the marker breaks out of the comment and injects markdown into a GitHub tracking issue. After resolving RUN_ID apply the same ^[A-Za-z0-9._-]+$ check used for --run-id and fail closed before upsert-summary.
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: scripts/implement-bootstrap.sh:387-396
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Fork-mode get-issue-context.sh is best-effort with stderr only in upstream-context.log; no redacted execution-issues entry. gh flakes or auth errors leave credential-bearing stderr on disk while /implement continues without upstream context, increasing wrong-target work risk. On non-zero exit append a redacted Warning via append-tool-failure.sh; keep best-effort continuation if required by binding.
- **Suggested revision**: Address the concern above.


### FINDING_17: risk-integration: skills/implement/SKILL.md:296-353
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] New STEP_FAILED=issue-number-required-for-resume has no SKILL exit-2 handler Resume with parent-issue.md but bootstrap invoked without --issue-number yields exit 2 with only generic abort text Add a dedicated exit-2 branch and operator message for issue-number-required-for-resume
- **Suggested revision**: Address the concern above.


### FINDING_18: correctness: skills/implement/SKILL.md:412-427
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Mandatory routing-guard Bash case is comment-only Executing the guard does not skip Step 0 after adopted-issue-closed/is-pr/tracking-init-failed; agent must infer skip from prose Replace with imperative routing prose or a bootstrap KV that downstream Bash blocks test
- **Suggested revision**: Address the concern above.


### FINDING_20: code-quality: scripts/implement-bootstrap.md:71-75
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Exit-code table omits new STEP_FAILED tokens Doc readers miss issue-number-required-for-resume and non-OPEN state failures Extend the exit-code table to match script and harness
- **Suggested revision**: Address the concern above.


### FINDING_22: correctness: skills/implement/SKILL.md:30
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Invariant #4 still documents deferred=true for larch-log.sh init failure. Plan and code use IMPLEMENT_BAIL_REASON=tracking-init-failed without DEFERRED; readers following Invariant #4 may continue plan materialization after a stall instead of Step 18 cleanup. Rewrite Invariant #4 to match tracking-init-failed + STALL_TRACKING=true and reserve DEFERRED=true for POSTED=false only.
- **Suggested revision**: Address the concern above.


### FINDING_23: correctness: skills/implement/SKILL.md:336-353
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Exit-2 handler lacks routing for STEP_FAILED=issue-number-required-for-resume. Resume with parent-issue.md but no --issue-number aborts with bare exit 2 and no operator-facing message. Add _ib_sf branch and document in Step 0 exit-2 prose and implement-bootstrap.md.
- **Suggested revision**: Address the concern above.


### FINDING_24: correctness: scripts/implement-bootstrap.md:74
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Exit-code table omits issue-number-required-for-resume. Contract doc understates resume fail-closed behavior exercised by the harness. Add STEP_FAILED row for issue-number-required-for-resume.
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: skills/implement/SKILL.md:296-353
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Step 0 exit-2 handler omits normalized message for STEP_FAILED=issue-number-required-for-resume. Manual bootstrap resume with sentinel but without --issue-number exits 2 with only raw STEP_FAILED=; /implement <N> always passes --issue-number so production path is safe. Add a fourth STEP_FAILED branch and document it in implement-bootstrap.md.
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: scripts/implement-bootstrap.md:74
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Contract doc exit table omits STEP_FAILED=issue-number-required-for-resume. Operators reading only .md miss the resume guard exit semantics that code and harness enforce. Extend the exit-code table to list issue-number-required-for-resume.
- **Suggested revision**: Address the concern above.


