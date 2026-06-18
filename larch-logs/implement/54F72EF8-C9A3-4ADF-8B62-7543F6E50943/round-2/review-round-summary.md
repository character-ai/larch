# Review Round 2

- Mode: `diff`
- 5 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Submodule cleanup failure returns rc=3 instead of rc=2 failed
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-generic-output.txt, dyn-waterfall-contract-output.txt
- **Severity**: important
- **Concern**: After `_post_dispatch_submodule_revert` fires (`revert_count > 0`), if `_cleanup_failed_coder_attempt` returns `False`, `apply_findings_with_coder` still returns `CoderResult(3, tool, "submodule-violation", ...)` at `python/review_and_fix.py:1850-1854`. Cleanup did not verify clean, but the caller emits the terminal submodule outcome. Step 5 can route to the submodule stall path instead of the generic coder-failure / cleanup-failure path used elsewhere (e.g. commit-failure cleanup failure at lines 1867-1870 returns rc=2 `failed`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: On `not _cleanup_failed_coder_attempt(...)`, return `CoderResult(2, tool, "failed", ...)`; reserve rc=3 for the terminal path where cleanup verified clean.
  - From codex-generic-output.txt: Return `CoderResult(2, tool, "failed", ...)` when `_cleanup_failed_coder_attempt` returns false. Keep rc=3 only when cleanup succeeds.
  - From dyn-waterfall-contract-output.txt: Keep `rc=3` and `status=submodule-violation` on both cleanup-success and cleanup-failure paths; distinguish cleanup failure via log detail or a separate KV, not by downgrading the status contract.


### FINDING_2: `_finalize_failed_cleanup` blanket `git restore .` wipes lawful carryover
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-generic-output.txt, dyn-cleanup-safety-output.txt
- **Severity**: important
- **Concern**: `_finalize_failed_cleanup` (`python/review_and_fix.py:818-845`) runs mode-aware patch restore, then unconditional `git restore --staged .` and `git restore .`. The blanket worktree reset returns every tracked path to HEAD/index and can discard lawful pre-coder or MAV staged/unstaged carryover that mode-aware restore just reapplied when verification fails (e.g. full snapshot with staged `carry.txt`, or head-untracked MAV carryover). This conflicts with the plan’s carryover-preservation goal on verification-failure stalls, even though bundled tests may assert empty porcelain without carryover present.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Drop the blanket `git restore .` from finalize; rely on mode-aware restore + unstaging, and only escalate to broader reset if porcelain still blocks rebase after verification.
  - From cursor-specialist-edge-cases-output.txt: Remove git restore .; keep mode-aware restore plus git restore --staged . only per plan
  - From cursor-specialist-testing-output.txt: Remove or narrow worktree-wide git restore . to coder delta paths only; keep mode-aware restore plus git restore --staged .; add carryover-preservation test on finalize path.
  - From codex-generic-output.txt: Remove the blanket `git restore .` and avoid unstaging after reapplying baseline state. Use only the mode-aware restore and untracked-delta cleanup paths, then log any remaining porcelain.
  - From dyn-cleanup-safety-output.txt: Remove the trailing `git restore .` (and the redundant second `git restore --staged .`) from `_finalize_failed_cleanup`. Keep mode-aware restore plus a single best-effort `git restore --staged .`. Limit any worktree-wide reset to `missing` snapshot mode only, if you still want a scorched-earth fallback there.


### FINDING_3: Step 5 stall_reason misclassifies cleanup failure after submodule revert
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Step 5 stall classification (`python/review_and_fix.py:2563-2566`) maps any `revert_count > 0` to `STALL_REASON=submodule-violation`, even when `coder.status` is `"failed"` from cleanup failure. Submodule revert can succeed while subsequent cleanup fails; the stall is labeled `submodule-violation` instead of `coder-failed`, misrouting Step 18a recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Gate on `result.coder.status == "submodule-violation"` only, or require cleanup success before mapping to submodule stall.
  - From cursor-specialist-edge-cases-output.txt: Gate stall_reason on coder.status == submodule-violation only


### FINDING_5: Stale snapshot entry guard returns rc=2 without cleanup/finalize
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-waterfall-contract-output.txt
- **Severity**: important
- **Concern**: The stale-snapshot guard at `apply_findings_with_coder` entry (`python/review_and_fix.py:1828-1835`) returns `CoderResult(2, "none", "failed", ...)` immediately when `pre_head != current_head`, without calling `_cleanup_failed_coder_attempt` or `_finalize_failed_cleanup`. The same condition inside `_cleanup_failed_coder_attempt` (`python/review_and_fix.py:853-863`) invokes `_finalize_failed_cleanup`. On retry with a reused `round_dir`, staged or unstaged coder residue can remain and block rebase while reporting `CODER_TOOL=none`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Call `_finalize_failed_cleanup` before returning rc=2 on the entry stale guard, matching the cleanup helper's stale path.
  - From cursor-specialist-edge-cases-output.txt: Run cleanup/finalize before returning rc=2; add regression test with stale snapshot plus staged files
  - From cursor-specialist-testing-output.txt: Route stale snapshot through _finalize_failed_cleanup before returning rc=2; add a regression test with stale snapshot plus dirty staged tree asserting empty porcelain.
  - From dyn-waterfall-contract-output.txt: Route the entry-path stale-snapshot branch through the same cleanup/finalize helper used mid-waterfall (or call `_finalize_failed_cleanup` before returning `rc=2`), and add a test where HEAD has moved and staged coder residue exists to assert porcelain is empty on exit.


### FINDING_7: Waterfall exits `no-changes` after commit-fail then Codex no-op instead of `main-agent-required`
- **Reviewer(s)**: dyn-waterfall-contract-output.txt
- **Severity**: important
- **Concern**: After a successful coder edit, a failed `_stage_and_commit_round` is cleaned and the waterfall continues, but if the next coder returns `True` with zero mode-aware stage paths, `apply_findings_with_coder` exits immediately with `CoderResult(0, …, "no-changes")` instead of falling through to `rc=4 main-agent-required` (`python/review_and_fix.py:1864-1874`). `test_apply_findings_with_coder_commit_failure_cleans_and_falls_through` locks this in: Cursor edits are rolled back, Codex is a no-op, result is `no-changes` with a clean tree while accepted findings were never committed. Step 5 maps `no-changes` to terminal `complete` (`python/review_and_fix.py:2573-2574`), so the round can finish without applying fixes and without the `coder-main-agent-required` handoff the waterfall is meant to provide when external coders cannot land a commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-waterfall-contract-output.txt: Track a per-round `commit_failed` flag across attempts; when `stage_paths` is empty after a successful coder run, return `no-changes` only if no earlier attempt in the same loop hit commit failure, otherwise `continue` the waterfall so exhaustion ends at `CoderResult(4, "none", "main-agent-required", …)`. Add a regression test that asserts `rc == 4` and `status == "main-agent-required"` for the Cursor-commit-fail → Codex-no-op scenario.


