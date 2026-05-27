### FINDING_1: code-quality: scripts/implement-bootstrap.sh:533-748
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] phase_plan_materialize is a ~215-line monolith with 14 sequential steps. Phase 4 coder-select absorption will add more branches to the same function increasing regression risk. Extract private step helpers after Phase 4; keep phase_plan_materialize as a thin ordered dispatcher.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/implement-bootstrap.sh:614-651
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] issue_title is read twice from feature-description.txt via head -1. Redundant I/O; theoretical title/slug mismatch if the file changed between reads. Read issue_title once and reuse for slug and goal_text_raw.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/implement-bootstrap.sh:151-156
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Second plan breadcrumb is gated on PLAN_SUMMARY_POSTED not breadcrumb enable flag alone. tracking-issue-summary best-effort failure hides larch:plan posted breadcrumb despite successful plan logging. Always emit second breadcrumb after tail steps or document success-only semantics in implement-bootstrap.md.
- **Suggested revision**: Address the concern above.

### FINDING_4: architecture: scripts/implement-bootstrap.sh:549-611
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] --resume-plan-tail skips dirty-tree re-check inside bootstrap. Orchestrator that skips pre-resume check-mid-run-dirty-tree could resume branch creation on a dirty tree. Re-run dirty checkpoint before resume tail or add harness enforcing orchestrator pre-check contract.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/implement-bootstrap.sh:626-648
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] branch-create-failed covers create-branch and git-current-branch failures. Stall triage cannot distinguish branch-exists vs detached HEAD without reading stderr logs. Document in SKILL (done) or split bail reasons in follow-up if ops need it.
- **Suggested revision**: Address the concern above.

### FINDING_6: correctness: scripts/implement-bootstrap.sh:223-297,549-611; skills/implement/SKILL.md:468
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Dirty-tree recovery re-runs full bootstrap (fresh session-setup tmpdir) while --resume-plan-tail assumes plan/feature files and parent-issue.md remain in the same IMPLEMENT_TMPDIR. First pass materializes under tmpdir A and bails dirty-tree; resume allocates tmpdir B, skips copy/gh/persist, reads empty feature-description.txt, loses HARD flags, misses sentinel, may double-adopt tracking; orchestrator exports IMPLEMENT_TMPDIR=B without plan.txt. Add tmpdir reuse (flag or skip session-setup on resume), copy artifacts/sentinel forward, and test with two distinct tmpdirs.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: scripts/implement-bootstrap.sh:549-611
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Resume tail does not re-run check-mid-run-dirty-tree; only SKILL prose requires a prior clean probe. Orchestrator skips standalone re-check and calls --resume-plan-tail on a still-dirty tree; branch creation proceeds despite checkpoint intent. Re-run checkpoint at resume-tail entry or add structural test for probe-before-resume ordering.
- **Suggested revision**: Address the concern above.

### FINDING_8: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh:957-988
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] B7 resume case reuses one SANDBOX_TMP for all session-setup calls, hiding production fresh-tmpdir behavior. CI passes while production dirty-tree recovery loses artifacts and re-runs Branch 2 adoption. Use two tmpdirs in B7 or stub session-setup to allocate a new dir on second call.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/implement-bootstrap.sh:151-156
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Second breadcrumb gated on PLAN_SUMMARY_POSTED; plan expects both breadcrumbs when crumbs enabled. Best-effort tracking-issue-summary failure suppresses "larch:plan posted" breadcrumb. Emit second breadcrumb unconditionally (or document and test gating).
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: scripts/implement-bootstrap.sh:553-554
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Token/timing mark label differs from plan/SKILL historical string. Ledger queries for "implement Step 0" miss new marks. Restore the historical mark text.
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] architecture: scripts/implement-bootstrap.md:113-114
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Doc table order for gh vs copy does not match implementation order. Debuggers misread failure sequencing. Reorder table rows to match phase_plan_materialize.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/test-implement-structure.sh:356-363
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Structural pins still require plan-materialization token/timing ledger literals in SKILL.md after Phase 3 moved them into implement-bootstrap.sh make lint / test-implement-structure fails with "must retain token-ledger Step 0 — plan materialization mark" even when bootstrap behavior is correct Update test-implement-structure.sh to pin the collapsed bootstrap contract instead of removed SKILL.md fenced marks
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: scripts/test-implement-structure.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent]  No harness enforces plan acceptance "single Bash call for Step 0 #1-16" or bans reintroduced prompt-side helper blocks Future SKILL edits could restore 16 separate Bash blocks; make test-implement-bootstrap still passes Add structural greps for one implement-bootstrap.sh --up-to-phase plan invocation and negative patterns for absorbed helpers outside dirty-tree recovery
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh:711-720
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Missing B3-plan symmetric to B2-plan for adopted-issue-is-pr on --up-to-phase plan Phase 3 could overwrite IMPLEMENT_BAIL_REASON on PR-target plan runs without failing harness Add B3-plan with LARCH_TEST_IS_PR=true and assert_not_contains for Phase 3 bail reasons
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: skills/implement/SKILL.md:464-468
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Dirty-tree orchestrator recovery flow (sentinel pre-check resume-plan-tail) not structurally tested Bootstrap resume-tail tests pass while orchestrator skips re-check or --resume-plan-tail leaving empty BRANCH_NAME and missing plan batches Add structure or routing harness greps/fixture for recovery gate contract
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh:775-785
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] B4-all does not assert plan materialization on DEFERRED=true unlike B4-plan --up-to-phase all could skip phase_plan_materialize when DEFERRED=true without failing tests Extend B4-all with plan.txt feature-description and invoke-log assertions from B4-plan
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh:869
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] B5-plan-green omits assert on token-ledger plan materialization mark Regression removing token-ledger mark while keeping timing-ledger would pass green path Add assert_contains for token-ledger Step 0 plan materialization in invoke log
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] architecture: scripts/implement-bootstrap.sh:904-908
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] resume-plan-tail re-runs phase_tracking before plan tail Possible duplicate tracking metadata on dirty-tree resume in production Evaluate idempotent tracking on resume or skip tracking when RESUME_PLAN_TAIL=true
- **Suggested revision**: Address the concern above.

### FINDING_19: security: skills/implement/SKILL.md:379-386
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] gh-issue-view exit-2 stderr uses only redact-secrets.sh, not the dual pipeline required by SECURITY.md gh CLI errors containing ~/.cache/larch/sessions/... paths reach the operator transcript after secrets-only redaction Pipe gh-issue-view.stderr.log through redact-secrets.sh | redact-tmpdir-paths.sh with the same fail-closed fallback as copy-plan
- **Suggested revision**: Address the concern above.

### FINDING_20: security: scripts/implement-bootstrap.sh:726-727
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] larch-plan summary upsert falls back to unredacted body including absolute PLAN_FILE on redactor failure tracking-issue larch:plan comment may publish full session tmpdir paths to GitHub Skip upsert or post a static pointer-only summary when redaction fails; do not cp raw summary_body_raw to the public boundary
- **Suggested revision**: Address the concern above.

### FINDING_21: security: skills/implement/SKILL.md:379-384
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] gh-issue-view exit-2 handler omits redact-tmpdir-paths.sh Operator transcript may leak session tmpdir paths from gh stderr despite SECURITY.md requiring dual redaction Pipe gh-issue-view.stderr.log through redact-secrets.sh and redact-tmpdir-paths.sh like copy-plan
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: scripts/implement-bootstrap.sh:564-571
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Forked gh issue view without --upstream-repo queries default remote Upstream design issue #N is read from fork origin; feature-description.txt disagrees with Preflight plan.txt Require --upstream-repo when --forked-target true or fail closed with gh-issue-view
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: scripts/implement-bootstrap.sh:609-611
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] resume-plan-tail skips dirty-tree checkpoint inside bootstrap Orchestrator that resumes without a prior clean probe can run create-branch on a still-dirty tree Re-run check-mid-run-dirty-tree at resume entry or fail closed if recovery env still shows RECOVERY_REQUIRED
- **Suggested revision**: Address the concern above.

### FINDING_24: risk-integration: skills/implement/SKILL.md:676-684
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Removed REPO_UNAVAILABLE skip prose without implementer-waterfall guard REPO_UNAVAILABLE runs reach Step 2 without plan.txt; run-step2-dispatch.sh fails with missing plan file Add explicit skip/bail before implementer waterfall when REPO_UNAVAILABLE or plan files missing
- **Suggested revision**: Address the concern above.

### FINDING_25: architecture: scripts/implement-bootstrap.sh:747-747
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Branch breadcrumb claims plan logged when run-step1-plan-log failed Operator sees success breadcrumb while plan-goals-test batch was never written Gate breadcrumb on run-step1-plan-log.sh success or split messages
- **Suggested revision**: Address the concern above.

### FINDING_26: code-quality: scripts/implement-bootstrap.md
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] --resume-plan-tail undocumented in argv/behavior tables Operators reading only implement-bootstrap.md miss dirty-tree resume contract Add argv row and behavior-mapping entry for resume tail
- **Suggested revision**: Address the concern above.

### FINDING_27: correctness: scripts/implement-bootstrap.sh:151-157
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Plan step 13 requires both plan-materialization breadcrumbs when LARCH_QUIET_BREADCRUMBS is set; code emits larch:plan posted only when PLAN_SUMMARY_POSTED=true and tests require suppression on upsert failure. Monitor or transcript tooling expecting the second breadcrumb after every successful branch+log path will not see it when tracking-issue-summary upsert fails; implement-bootstrap.md still documents unconditional emission. Either always emit the second breadcrumb per plan or update plan, implement-bootstrap.md, and acceptance to document summary-posted-only emission.
- **Suggested revision**: Address the concern above.

### FINDING_28: architecture: scripts/implement-bootstrap.md:7-17
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] --resume-plan-tail is required by SKILL dirty-tree recovery but missing from the canonical argv table. Contributors relying on implement-bootstrap.md will not find the resume flag the orchestrator must pass after a clean dirty-tree re-check. Add --resume-plan-tail to the argv table with a short dirty-tree resume behavior note.
- **Suggested revision**: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] risk-integration: skills/implement/SKILL.md:464-468
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] No harness exercises the full prompt-side dirty-tree recovery loop (only bootstrap --resume-plan-tail). Orchestrator could skip re-check or pass wrong args while bootstrap unit tests still pass. Optional follow-up: structural pin or routing fixture for sentinel, re-check, and resume args.
- **Suggested revision**: Address the concern above.

