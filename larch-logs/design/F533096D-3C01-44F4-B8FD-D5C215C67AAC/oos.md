### FINDING_1: Memory-only Step 3 stalls omit classify argv binding
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The new `checks-child-sigterm` classifier guard depends on `bail == "checks-child-failed"`, `step in {"3","6"}`, and a raw `EXIT_CODE`, but the orchestrator docs and entry macros do not normatively bind or pass those values on memory-only structural checks failures. `stall-recovery.md` Step 18a item 3 documents only `BAIL_FAILURE_DETAIL_LOG` plus `--in-memory-stall-tracking`, not the full classify argv template (`--stall-step`, `--phase`, `--bail-reason`, `--exit-code`). `checks-repair-loop.md` Step 3 Checks Failure Entry Macro mandates reading `REDACTED_LOG_FILE` only; unlike Step 5 resume it never token-scans `EXIT_CODE` from the composite relay. On memory-only stalls (no `ship-pr-state.sh` seed, no `REDACTED_LOG_FILE`), Step 18a can pass `--in-memory-stall-tracking` and still omit bail/step/exit-code on some paths, so `classify()` falls back to `unknown` and the SIGTERM branch never runs in production.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend stall-recovery item 3 with an explicit `stall-recovery classify` template: `--in-memory-stall-tracking "${STALL_TRACKING:-false}"`, `--stall-step "${STALL_STEP}"`, `--phase "${PHASE:-checks}"`, `--bail-reason "${IMPLEMENT_BAIL_REASON:-${FINAL_BAIL_REASON}}"`, `--exit-code "${EXIT_CODE:-unknown}"`, plus validated `BAIL_FAILURE_DETAIL_LOG`. Add one bullet in checks-repair-loop section 4 to bind `STALL_STEP`, `PHASE`, `IMPLEMENT_BAIL_REASON` (from composite `FAILURE_REASON`), and `EXIT_CODE` from the captured composite stdout before skipping to Step 18 when no `REDACTED_LOG_FILE` exists.
  - From Cursor-Innovation: Augment section 1: when routing structural `checks-child-failed` (or related) failures without `REDACTED_LOG_FILE` to Step 18, bind `EXIT_CODE`, `FAILURE_REASON` → `IMPLEMENT_BAIL_REASON`, `STALL_STEP`, and `PHASE` from the composite first line before Step 18a; mirror the binding in stall-recovery.md item 3 classify argv template


Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: `checks-leg-timeout` at Step 3/6 still hits blanket `step-contract`
- **Description**: `checks-leg-timeout` at Step 3/6 still hits blanket `step-contract`. Scenario: Internal `_run_leg_with_timeout` timeout emits `FAILURE_REASON=checks-leg-timeout`, not `checks-child-failed`; the plan only intercepts `checks-child-failed`. Large suites that hit the internal deadline get no retry path
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/larch/state/_classify.py:126-127
- **Phase**: design




Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral

### OOS_2: Internal checks-leg-timeout still hits step-contract after this plan
- **Description**: Internal checks-leg-timeout still hits step-contract after this plan. Scenario: When `_run_leg_with_timeout` fires (`_CHECKS_DEADLINE_MS` = 3h), the composite emits `FAILURE_REASON=checks-leg-timeout`, not `checks-child-failed`. The planned guard keys only on `checks-child-failed`, so that path still returns `contract-failure` / `RESUME_HINT=none` at step 3/6. Long runs that die on the internal leg timer remain terminal.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_commit_route.py:186-190
- **Phase**: design




Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral

### OOS_3: [OUT_OF_SCOPE] Threading raw EXIT_CODE through the generic terminal-state path is dead code under current validation.
- **Description**: [OUT_OF_SCOPE] Threading raw EXIT_CODE through the generic terminal-state path is dead code under current validation.. Scenario: The generic terminal-state validator still rejects negative EXIT_CODE values, so this branch cannot affect the SIGTERM case this PR is trying to fix.
- **Reviewer**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: python/larch/state/_classify.py:276-283; python/larch/state/_validate.py:77-80
- **Phase**: design




Vote tally: YES=0 NO=1 JUDGE_ERROR=1 Result=rejected

### OOS_4: [OUT_OF_SCOPE] The raw-exit plumbing for `_classify_generic_from_terminal_state()` does not affect this `/implement` stall fix, because generic terminal-state validation still rejects negative `EXIT_CODE` values before classification.
- **Description**: [OUT_OF_SCOPE] The raw-exit plumbing for `_classify_generic_from_terminal_state()` does not affect this `/implement` stall fix, because generic terminal-state validation still rejects negative `EXIT_CODE` values before classification.. Scenario: Feature still ships correctly without the generic `/design` seam, so this adds extra surface and test work without changing Step 18a behavior.
- **Reviewer**: Codex-dyn-Stall Classifier
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/state/_classify.py:274-315; python/larch/state/_validate.py:77-82
- **Phase**: design

Vote tally: YES=0 NO=1 JUDGE_ERROR=1 Result=rejected

