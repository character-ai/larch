### FINDING_1: architecture: scripts/implement-bootstrap.sh:635-657
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Phase 3/4 stub dispatch ignores DEFERRED=true and can overwrite a clean bail tail. POSTED=false leaves DEFERRED=true and empty IMPLEMENT_BAIL_REASON; --up-to-phase plan|coder|all then runs phase_plan_materialize and emits not-yet-implemented-phase-3/4, confusing combined-phase callers. Skip later stubs when DEFERRED=true (or no-op stubs without setting bail); add B4-plan/B4-all harness coverage.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/implement-bootstrap.sh:637-657
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] The phase-skip guard is triplicated in main() for plan/coder/all. Future guard changes (e.g. DEFERRED) require three identical edits and invite drift. Extract tracking_allows_later_phases helper and call it from each case arm.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/implement-bootstrap.sh:112-115
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] kv_value_from_block duplicates ship-pr kv_value with a different duplicate-key policy. Tool stdout with repeated keys could parse differently across scripts. Share a lib helper or document first-match semantics; align with ship-pr if duplicates matter.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/implement/scripts/test-implement-bootstrap.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit]  No harness for DEFERRED + multi-phase bootstrap boundary. Deferred post failure on --up-to-phase plan|all is untested; tail-clobber could regress silently. Add B4-plan (and optionally B4-all) asserting DEFERRED=true and empty IMPLEMENT_BAIL_REASON.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] code-quality: skills/implement/SKILL.md:681-688
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Step 0 bootstrap and Branch prefix both call create-branch.sh --check. Extra subprocess and possible KV re-parse on every run. Fold into bootstrap-only parsing when Step 0 collapse continues (Phase 4).
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] code-quality: scripts/write-session-env.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit]  Bash [[ ]] style differs from implement-bootstrap POSIX case tests. Minor portability/consistency concern only; not introduced here. Align styles when touching write-session-env for another reason.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: skills/implement/SKILL.md:296-353
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Step 0 exit-2 handler omits normalized message for STEP_FAILED=issue-number-required-for-resume. Manual bootstrap resume with sentinel but without --issue-number exits 2 with only raw STEP_FAILED=; /implement <N> always passes --issue-number so production path is safe. Add a fourth STEP_FAILED branch and document it in implement-bootstrap.md.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: skills/implement/SKILL.md:605
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Plan F4 asked for an explicit binding behavior-change note for best-effort fork get-issue-context; only a table row exists. Upstream gh fetch failure leaves empty/missing upstream-issue-*.txt with no orchestrator-visible abort; operator may expect old hard-bail semantics. Add an explicit binding behavior change bullet near the bootstrap behavior map.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/implement-bootstrap.md:74
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Contract doc exit table omits STEP_FAILED=issue-number-required-for-resume. Operators reading only .md miss the resume guard exit semantics that code and harness enforce. Extend the exit-code table to list issue-number-required-for-resume.
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: skills/implement/scripts/test-post-tracking-issue.sh:41-63
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Real post-tracking-issue.sh gained --run-id but its dedicated harness was not updated; bootstrap uses a stub only. A regression in --run-id precedence, validation, or sentinel rewrite in post-tracking-issue.sh passes make test-implement-bootstrap while breaking /implement Step 0 metadata posting. Add test-post-tracking-issue cases for --run-id override, invalid --run-id exit 2, and sentinel/marker behavior; update test-post-tracking-issue.md.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: scripts/test-session-env-roundtrip.sh:1-12
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] write-session-env.sh --forked-target is not covered by the roundtrip harness. Invalid --forked-target or a broken FORKED_TARGET= line could regress without failing test-session-env-roundtrip (only caught indirectly via bootstrap). Add roundtrip cases for --forked-target true/false, invalid value, and read-session-env-key FORKED_TARGET.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: docs/linting.md:238
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] linting.md still documents test-implement-bootstrap as Step 0 #1-#5 only. Contributors relying on docs/linting.md underestimate harness scope and may skip tracking regressions when editing Step 0. Update the make test-implement-bootstrap row to #1-#9 and list tracking/bail cases.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh:682-715
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] No harness case for invalid --forked-target argv. Typo --forked-target yes could ship without a targeted regression test (only caught manually). Add B-invalid-forked-target-arg expecting exit 2 and usage text.
- **Suggested revision**: Address the concern above.

### FINDING_14: security: skills/implement/scripts/post-tracking-issue.sh:64-67,94
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] RUN_ID from parent-issue.md session-id or session-env is not re-validated after the CLI --run-id check before embedding in the metadata HTML comment marker. A same-UID tamperer sets parent-issue.md RUN_ID=x--> in a caller that omits --run-id; the marker breaks out of the comment and injects markdown into a GitHub tracking issue. After resolving RUN_ID apply the same ^[A-Za-z0-9._-]+$ check used for --run-id and fail closed before upsert-summary.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/implement-bootstrap.sh:387-396
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Fork-mode get-issue-context.sh is best-effort with stderr only in upstream-context.log; no redacted execution-issues entry. gh flakes or auth errors leave credential-bearing stderr on disk while /implement continues without upstream context, increasing wrong-target work risk. On non-zero exit append a redacted Warning via append-tool-failure.sh; keep best-effort continuation if required by binding.
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: scripts/implement-bootstrap.sh:416-428
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Branch 1 resume skips get-issue-state.sh and trusts a local sentinel. A closed or PR-converted issue can still resume implementation because only Branch 2 checks GitHub state. Re-verify issue state on resume or refuse resume when state is not OPEN.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: skills/implement/SKILL.md:296-353
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] New STEP_FAILED=issue-number-required-for-resume has no SKILL exit-2 handler Resume with parent-issue.md but bootstrap invoked without --issue-number yields exit 2 with only generic abort text Add a dedicated exit-2 branch and operator message for issue-number-required-for-resume
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: skills/implement/SKILL.md:412-427
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Mandatory routing-guard Bash case is comment-only Executing the guard does not skip Step 0 after adopted-issue-closed/is-pr/tracking-init-failed; agent must infer skip from prose Replace with imperative routing prose or a bootstrap KV that downstream Bash blocks test
- **Suggested revision**: Address the concern above.

### FINDING_19: architecture: scripts/implement-bootstrap.sh:637-657
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Phase 3/4 stub guard ignores DEFERRED=true --up-to-phase plan/all after DEFERRED=true can overwrite tail with not-yet-implemented-phase-3 Include DEFERRED=true in the stub skip guard or restrict documented --up-to-phase values
- **Suggested revision**: Address the concern above.

### FINDING_20: code-quality: scripts/implement-bootstrap.md:71-75
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Exit-code table omits new STEP_FAILED tokens Doc readers miss issue-number-required-for-resume and non-OPEN state failures Extend the exit-code table to match script and harness
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] risk-integration: scripts/lint-foreground-markers.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] implement-bootstrap not on Family B denylist SKILL relies on prose for foreground-only; denylist drift from implement-bootstrap.md note Add implement-bootstrap.sh to DENYLIST when ready
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

