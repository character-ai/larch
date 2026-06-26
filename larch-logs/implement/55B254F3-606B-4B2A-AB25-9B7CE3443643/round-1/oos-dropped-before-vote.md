### OOS_1: [OUT_OF_SCOPE] Post-round check removal and dead-code cleanup correctly implemented
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Post-apply `_run_relevant_checks_captured` and the lint-fix while-loop are removed from `_step5_post_round_gates`; dead helpers (`_run_relevant_checks_captured`, `_run_lint_fix_loop`, lint snapshot/commit helpers, `_lint_fix_max_attempts`) have no remaining production callers; and the call site drops the unused `implement_tmpdir` argument.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_2: [OUT_OF_SCOPE] Convergence gates preserved after check removal
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Convergence logic (skip-ratio, substantiality, round cap) is preserved. The plan’s “return `(None, None, True)` unconditionally” line was oversimplified; the feature only required removing checks, not those gates.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_3: [OUT_OF_SCOPE] Step 6 and MAV/coder handoff still run full validation; mid-loop stall routing removed by design
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Step 6 (`checks-commit-route --checks-site step6`) and the MAV/coder handoff path (`checks-step5-resume`) are untouched, so full-suite validation still runs at dedicated checkpoints. The main behavioral change is intentional: a `fix-applied` round that breaks tests but is not “substantial” can reach `STEP5_REVIEW_STATUS=complete` and advance to Step 6 instead of stalling mid-round. That is the accepted trade-off in the issue, not a logic error in this diff.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_4: [OUT_OF_SCOPE] `skills/implement/SKILL.md` still documents post-round checks in the absorbed Step 5 loop
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Skill prose still says the absorbed Step 5 loop “internalizes … post-round captured relevant checks, lint-fix repair” and that `complete` already ran `python/cli.py checks run-relevant` / `python/cli.py checks lint-fix`. After this change that is only true for MAV/coder handoff (`checks-step5-resume`), not the normal `fix-applied` → `complete` path (which relies on Step 6). `SKILL.md` is not in the diff; orchestration still runs Step 6 checks, so this is documentation drift, not a functional regression from this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Update the parenthetical to note checks run at Step 6 (and on MAV/coder resume), not inside post-round gates.

### OOS_5: [OUT_OF_SCOPE] Stale shard assignments for deleted Step 5 tests
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-dyn-review-loop-regression-output.txt
- **Severity**: latent
- **Concern**: `python/shard-assignments.json` still lists nodeids for deleted tests (`test_step5_checks_wiring_passes_repo_site_and_binary_presence`, `test_step5_lint_fix_clean_baseline_inline_commit_noops_post_loop`, `test_step5_post_round_gates_lint_fix_attempt_cap`). Sharded CI ignores missing nodeids, so builds should not fail; it is maintenance debt until the map is refreshed or rebalanced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Regenerate or manually prune those entries on merge.

### OOS_6: [OUT_OF_SCOPE] No positive regression test that `fix-applied` skips post-round checks
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Removing the old lint-fix tests satisfies the plan, but there is no positive test asserting that `_step5_post_round_gates` no longer invokes checks on `fix-applied` (e.g., mocking `checks.run_relevant_checks` and asserting it is never called). Existing tests cover cap-hit and bulk-skip continuation only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Optional thin test with a minimal `RoundResult` to lock in the new default-complete contract and guard against reintroducing post-apply checks.

### OOS_7: [OUT_OF_SCOPE] Review rounds may run on a known-broken tree before Step 6
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: If a round’s coder apply breaks tests but convergence gates allow another round (`gate_continue=True`), later rounds run a full review panel on a broken tree before Step 6 catches the failure. That wastes tokens/time but matches the issue’s stated tradeoff (defer checks to Step 3/6). Intentional performance change, not a missing check gate.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_8: [OUT_OF_SCOPE] Convergence stall routing at cap lacks regression coverage after test deletions
- **Reviewer(s)**: dyn-dyn-review-loop-regression-output.txt
- **Severity**: latent
- **Concern**: Convergence coverage after the deletion only exercises `cap-hit` and bulk-skip `continue`. There is no regression test for `bulk-skip-ratio-cap` stall at cap, the non-substantial `complete` path, or substantial `continue` when `round_num < round_cap`. Production logic is unchanged aside from the removed checks prefix, but stall routing at cap is now unguarded by tests.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_9: [OUT_OF_SCOPE] Stall-recovery and reference docs still describe `lint-fix-*` paths the normal post-round gate no longer emits
- **Reviewer(s)**: dyn-dyn-review-loop-regression-output.txt
- **Severity**: latent
- **Concern**: `LINT_FIX_BAIL_REASON_TOKENS`, stall-recovery `lint-fix-bail-token` classification, and Step 5 stall logging still document `lint-fix-*` paths that `_step5_post_round_gates` no longer emits. That remains correct for MAV / `checks-step5-resume` repair and historical resumes, but operators debugging Step 5 may look for those tokens after per-round applies and not find them.
- **Suggested revisions (informational for voters; coder decides)**:

