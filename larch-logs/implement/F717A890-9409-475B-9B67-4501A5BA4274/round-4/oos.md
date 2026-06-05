### FINDING_1: [OUT_OF_SCOPE] Post-monitor iteration cap check is unreachable / does not enforce the intended at-cap stall
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-resume-state-output.txt, dyn-github-pr-output.txt, dyn-counter-limits-output.txt, dyn-postmerge-idem-output.txt, dyn-oos-skip-output.txt
- **Severity**: important
- **Concern**: The inner `iteration > SHIP_MERGE_LOOP_MAX_ITERATIONS` check inside the non-merge monitor branch uses the same unmodified `iteration` value as the top-of-loop guard, making that branch unreachable. Reviewers disagreed whether the intended fix is removal or changing the post-monitor guard to enforce an immediate at-cap stall, but all describe the same cap-enforcement ambiguity/dead-code risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove the inner `if iteration > config.SHIP_MERGE_LOOP_MAX_ITERATIONS:` block (lines 1345–1360) entirely; the outer check already provides the required cap-before-monitor semantics.
  - From cursor-specialist-correctness-output.txt: change line 1273 to `if iteration >= config.SHIP_MERGE_LOOP_MAX_ITERATIONS:` so the post-decision cap fires at exactly `MAX`.
  - From cursor-specialist-edge-cases-output.txt: Remove the inner cap check block entirely (diff lines 1345–1360); the top-of-loop Check A enforces the cap correctly on the subsequent iteration.
  - From dyn-resume-state-output.txt: Remove the post-monitor cap block at lines 1273-1288 entirely; the pre-monitor check at line 1211 already handles all cases. If the intent is to let monitor run at exactly `cap` and stall in the same iteration on non-pass/non-merged outcome, move the ENTIRE cap check to after the monitor call inside the `if monitor.action not in {"merge", "already_merged"}:` block using `iteration` AFTER the increment (`iteration + 1 > cap` at the top of the block, before `_write_ship_state`), and delete the pre-monitor check.
  - From dyn-github-pr-output.txt: Remove the duplicate inner `if iteration > config.SHIP_MERGE_LOOP_MAX_ITERATIONS` block at lines 1273–1288; the outer pre-loop guard already enforces the cap correctly (changed from `>=` to `>` to allow one final monitor cycle at the cap).
  - From dyn-counter-limits-output.txt: Change the post-monitor guard to `if iteration >= config.SHIP_MERGE_LOOP_MAX_ITERATIONS` while leaving the top-of-loop guard as `>`.
  - From dyn-postmerge-idem-output.txt: Remove the duplicate cap block at lines 1273-1288 entirely; the sole enforcement point should remain at line 1211 where `iteration > MAX` is checked before every monitor call.
  - From dyn-oos-skip-output.txt: Remove the inner `if iteration > config.SHIP_MERGE_LOOP_MAX_ITERATIONS:` block inside the non-merge action branch; the outer check at the top of the loop already provides the correct cap semantics.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_12: [OUT_OF_SCOPE] Shell-metacharacter validation gaps for state fields such as `PR_TITLE`
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-state-file-output.txt
- **Severity**: latent
- **Concern**: Some fields written to `ship-pr-state.sh`, especially `PR_TITLE`, are only newline-checked and may contain shell metacharacters if any bash consumer sources the state file unsafely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: add allowlist/escape validation for PR_TITLE at the write site, or ensure all bash consumers source with `key="$(grep ...)"` quoting.
  - From dyn-state-file-output.txt: PR_TITLE warrants an explicit allowlist or shell-safe quoting on the write path.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_16: [OUT_OF_SCOPE] Merge-retry results can loop without consuming iteration budget
- **Reviewer(s)**: dyn-counter-limits-output.txt
- **Severity**: latent
- **Concern**: Merge retry outcomes such as CI-not-ready/main-advanced continue without incrementing `iteration`, so a permanent retry condition may bypass the iteration cap indefinitely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-counter-limits-output.txt: worth adding a separate `merge_retry_count` cap or a maximum consecutive merge-retry guard.

Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_3: [OUT_OF_SCOPE] `manifest_status` uses `ctx.run_id` instead of `effective_run_id(ctx)`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-github-pr-output.txt, dyn-postmerge-idem-output.txt
- **Severity**: latent
- **Concern**: `manifest_status` reads the manifest under `ctx.run_id` rather than the effective run id used by `_manifest_path`, so it can miss the actual manifest when state-file `RUN_ID` and context `run_id` diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Replace `ctx.run_id` on line 147 with `effective_run_id(ctx)` (the function is already in the same module), and update the test name/assertion to match.
  - From cursor-specialist-correctness-output.txt: use `effective_run_id(ctx)` consistent with `_manifest_path`.
  - From cursor-specialist-edge-cases-output.txt: Either document this divergence from `effective_run_id` in the function docstring and ensure all callers have already hydrated `ctx.run_id` from state before calling, or align with `effective_run_id` as the plan states and update the test to match.
  - From cursor-specialist-plan-fidelity-output.txt: Use `effective_run_id(ctx)` in the path construction to match the `_manifest_path` contract, or update the plan/docstring to explicitly document why `ctx.run_id` is preferred.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_4: [OUT_OF_SCOPE] `_fresh_resume_plan` accepts counters but always discards them
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-state-output.txt
- **Severity**: nit
- **Concern**: `_fresh_resume_plan` exposes a `counters` parameter even though fresh plans always seed counters to zero. Passing restored counters at call sites is therefore silently ignored and misleading.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove the `counters` parameter from `_fresh_resume_plan`'s signature and all call sites; always construct zeros inline.
  - From cursor-specialist-testing-output.txt: Remove the `counters` parameter entirely since `fresh` always zeros counters per spec.
  - From cursor-specialist-edge-cases-output.txt: Remove the `counters` parameter entirely and remove the `counters=counters` kwargs at all call sites; document the zero-seed invariant clearly in the function signature.
  - From cursor-specialist-plan-fidelity-output.txt: Remove the `counters` parameter from `_fresh_resume_plan` since it is never used; update call sites to omit it.
  - From dyn-resume-state-output.txt: Remove the `counters` parameter from `_fresh_resume_plan` entirely.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_7: [OUT_OF_SCOPE] State validation failures are reported as checkout mismatches
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Non-checkout state validation failures route through checkout-mismatch naming/reasoning, which can mislead users into debugging their git checkout instead of malformed or mismatched state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Introduce a separate `blocked-state-invalid` start value (or at minimum a separate `needs_user_reason` string like `"state-invalid"`) for non-branch validation failures, keeping `"checkout-mismatch"` only for genuine branch/HEAD mismatches and the main/master guard.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

