### OOS_1: [OUT_OF_SCOPE] Dispatcher bail strings remain verbatim until downstream redaction
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Step-2 manifest sanitization keeps `bail_reason` verbatim while the schema allows free-form bail strings; this predates the branch but the new wiring increases reliance on downstream `safe_bail_reason_value()` rather than dispatch-time redaction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] `main-branch-post-dispatch` handoff is not in the public enum or dispatch classifier
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-contract-sync-output.txt, dyn-shell-state-output.txt, dyn-workflow-handoff-output.txt
- **Severity**: important
- **Concern**: Step 2 now mirrors `main-branch-post-dispatch`, but the token is outside `safe_bail_reason_value()` and the documented enum, so the public row renders `redacted`; reviewers also noted classification may fall through or lose intended dispatch-failure recovery, and coverage is only structural.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-correctness-output.txt, dyn-shell-state-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Add token to closed enum plus heuristic if recovery desired or document intentional redaction and add harness assertions.
  - From cursor-specialist-edge-cases-output.txt: Add classify plus bug-body fixture for main-branch-post-dispatch.
  - From dyn-contract-sync-output.txt: Either add `main-branch-post-dispatch` to the closed publication enum (and optionally the dispatch-failure evidence matcher), or stop wiring it into `IMPLEMENT_BAIL_REASON` and document that post-dispatch mismatch bail is intentionally non-publishable/non-classifying.
  - From dyn-contract-sync-output.txt: Add a case that classifies/renders with `--bail-reason main-branch-post-dispatch` (and expected `FAILURE_CLASS` / `| Bail reason | … |` outcome), matching the intended closed-enum policy.
  - From dyn-workflow-handoff-output.txt: Add `main-branch-post-dispatch` to `safe_bail_reason_value`, the documented `BAIL_REASON` enum in `stall-recovery-report.md` / `SECURITY.md`, and a body-render regression (similar to case 13 bail-row tests).


### OOS_3: [OUT_OF_SCOPE] `recovery-out-of-scope` mirror lacks consistent stall routing and allowlist treatment
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-contract-sync-output.txt, dyn-shell-state-output.txt, dyn-workflow-handoff-output.txt
- **Severity**: latent
- **Concern**: `recovery-out-of-scope` is mirrored into `IMPLEMENT_BAIL_REASON`, but it does not consistently set `STALL_TRACKING=true` or route into Step 12d, and it remains outside the public enum, so it may never surface or may render as `redacted`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-contract-sync-output.txt, dyn-shell-state-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Align with other hard-bails or remove mirror if not a stall surface.
  - From dyn-workflow-handoff-output.txt: Either add `STALL_TRACKING=true` plus explicit Step 12d routing (and include `recovery-out-of-scope` in the allowlist if it should appear in reports), or drop the `IMPLEMENT_BAIL_REASON` mirror here and state that recovery scope failure is not a stall-recovery handoff.


### OOS_4: [OUT_OF_SCOPE] Allowlist lint does not validate transform/source metadata drift
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-contract-sync-output.txt, dyn-workflow-handoff-output.txt
- **Severity**: latent
- **Concern**: `cmd_lint` compares only `surface` and `field_key`, so transform/source drift such as `integer-or-unknown` reverting or `bail_reason` semantics diverging across TSV, docs, and runtime would still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-workflow-handoff-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Extend lint to validate transform tokens or add render contract tests.
  - From codex-specialist-testing-output.txt: Compare all four allowlist columns in lint, add code-side source/transform projection, and add a negative drift test.
  - From dyn-contract-sync-output.txt: Extend `cmd_lint` (and `test-stall-recovery-report.sh` case 14) to compare full TSV rows or at least the `transform` column for each `surface`/`field_key`, and fail when TSV, markdown allowlist table, and documented render semantics diverge.


### OOS_5: [OUT_OF_SCOPE] `ci-fix-exhausted` renders as redacted despite being classifier evidence
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-contract-sync-output.txt
- **Severity**: latent
- **Concern**: `ci-fix-exhausted` is a classifier bail token but is not in `safe_bail_reason_value()`, so reports can show `FAILURE_CLASS=ci-fix-exhausted` beside `Bail reason redacted`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add ci-fix-exhausted to safe_bail_reason_value or omit bail row when class already identifies stall.
  - From dyn-contract-sync-output.txt: Address the concern above.


### OOS_6: [OUT_OF_SCOPE] Step-2 legal-actions and hard-bail routing remain contradictory
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-workflow-handoff-output.txt
- **Severity**: important
- **Concern**: The authoritative Step-2 legal-actions matrix can omit `IMPLEMENT_BAIL_REASON` / `FINAL_BAIL_REASON` mirroring and unconditional `STALL_TRACKING=true`, while Step 12d hard-bail routing for pre-ship Step-2 failures is underspecified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Update matrix row 569 to match §2.2:632; pin with structure test grep.
  - From dyn-workflow-handoff-output.txt: Add a short §2.2 “Step 12d hard-bail routing” subsection that names the concrete next steps for pre-ship Step-2 failures (e.g. skip Steps 3–15, continue through Steps 16–17, run Step 18a with in-memory `--bail-reason "${IMPLEMENT_BAIL_REASON:-${FINAL_BAIL_REASON:-}}"` and optional `seed-terminal-state --stall-step 2 --phase …`).
  - From dyn-workflow-handoff-output.txt: Address the concern above.


