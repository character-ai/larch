## Goal
Implement issue #5011: [IMPLEMENTING] [BUG] /implement renders final report before stall recovery (premature stalled report).

## Implementation Plan
## Summary

On `/implement`, the final report (Step 17) renders and flushes logs **before** stall recovery (Step 18a) runs. Recoverable stalls therefore display a premature, misleading `— stalled` final report and flush stale logs even when Step 18a's main-agent recovery goes on to complete (and merge) the run. On successful recovery the terminal sequence runs twice, producing a second `— merged` report. The ordering is "report-then-recover" when it should be "recover-then-report".

## Original report

> Root cause why a stall results in the final report being shown first and then the main agent taking over, which is bad for a number of reasons, including logs flushing prematurely and the final report being displayed prematurely. The desired behavior is the main agent taking over, completing the job, and only then the final report and cleanup steps taking place.

## Reproduction scenario

Trigger any recoverable `/implement` stall whose Step 18a recovery completes the run. Concretely:

1. Run `/implement --merge <issue>` where the implementer's code produces a Step 5 `lint-fix-failed` stall — e.g. a pyright/type error that the coder lint-fix loop cannot auto-resolve.
2. The Step 5 `stall` branch sets `STALL_TRACKING=true` and **skips to Step 16**.
3. Observe: Step 16 -> Step 17 renders the `/implement run ... — stalled` final report and flushes logs.
4. Observe: Step 18a stall recovery then classifies the stall and dispatches main-agent recovery, which fixes the failure and completes the run to merge.
5. Observe: a second Step 16/17 pass renders `/implement run ... — merged`.

Reproduced live in run `66A96EAD-3088-4750-AE3A-64A0E11EABBD` (issue #4962, PR #5009, merged).

## Expected behavior

Stall recovery (Step 18a) runs first. The final report and log flush happen exactly once, after the stall resolves, reflecting the true terminal outcome (merged, or terminally stalled). No premature `— stalled` report when recovery goes on to succeed.

## Observed behavior

The terminal sequence Step 16 (rejected findings) -> Step 17 (final report render + log flush) -> Step 18 (which contains Step 18a stall recovery) renders the final report and flushes logs before recovery runs. On successful recovery two final reports are displayed (`stalled`, then `merged`) and logs are flushed twice (stale state, then final state).

## Root cause analysis

The `/implement` terminal control flow is ordered Step 16 -> Step 17 -> Step 18, and the stall-recovery gate (Step 18a) lives **inside** Step 18, so it runs after the final report.

- Stall paths route via "skip to Step 16" / "Continue to Step 16" with `STALL_TRACKING=true` (Step 5 `stall` branch, Step 5 self-review terminal stall, resume/review-fix commit-failed stalls, Step 8 Exit 4).
- `skills/implement/SKILL.md:439` states the ordering directly: "execution skips Steps 3-15 (continuing directly to Step 16, then Step 17, then Step 18a with the coalesced `--bail-reason` for stall classification). Step 12d bail is not terminal — Step 16 (rejected findings) and Step 17 (final report) still run; Step 18a then performs stall classification and recovery gating, and Step 18b runs teardown."
- Step 18a (`SKILL.md:882`) "runs first on every Step 18 entry, before teardown" — but Step 18 itself is after Step 16/17.
- Step 18a recovery can dispatch a main-agent retry (`RESUME_HINT` = `step2-impl` / `step5-review` / `step8-shippr`, per `stall-recovery.md`) that re-enters the pipeline and completes the run. The Step 17 report rendered earlier is therefore premature whenever recovery succeeds.

This is an observation (the order is fixed in the prompt control flow), not an inference: the step markers and the line-439 routing prose make the order explicit.

## Evidence

- `skills/implement/SKILL.md:439` — "continuing directly to Step 16, then Step 17, then Step 18a ..."; "Step 16 (rejected findings) and Step 17 (final report) still run; Step 18a then performs stall classification and recovery gating, and Step 18b runs teardown."
- `skills/implement/SKILL.md:641` — Step 5 `stall` branch: "Skip to Step 16."
- `skills/implement/SKILL.md:592`, `:673`, `:724` — other Step 5/7 terminal-stall paths: "skip to Step 16."
- `skills/implement/references/step5-review-branches.md:19` — `stall` branch ends "Skip to Step 16."
- `skills/implement/references/ship-pr-exit-matrix.md:26` — Exit 4: "Continue to Step 16. ... Let Step 18a classify ..."
- Step-ordering markers in `skills/implement/SKILL.md`: `:844` (`step:16`), `:858` (`step:17`), `:878` (`step:18`), `:882` (Step 18a gate, "runs first on every Step 18 entry, before teardown").
- Live run `66A96EAD-3088-4750-AE3A-64A0E11EABBD` / PR #5009: Step 5 `lint-fix-failed` -> `— stalled` final report rendered + logs flushed -> Step 18a recovery (main Claude fixed pyright errors + a harness-shard partition gap + resolved a rebase conflict with a concurrently-merged PR) -> `admin_merged` -> second `— merged` final report.

## Affected files

- `skills/implement/SKILL.md` — Step 16/17/18 ordering; Step 18a gate (`### Step 18a — Stall recovery gate`); the stall-branch routing prose and the line-439 Step 12d hard-bail routing that pins "Step 16, then Step 17, then Step 18a."
- `skills/implement/references/step5-review-branches.md` — the `stall` branch "Skip to Step 16."
- `skills/implement/references/ship-pr-exit-matrix.md` — Exit 4 "Continue to Step 16."
- `skills/implement/references/stall-recovery.md` — Step 18a recovery procedure (the recovery that completes the job after the report already rendered).
- Likely also `python/closeout.py` / `python/final_report.py` (Step 16/17 render) and `python/ship.py` / `python/run_logs.py` (log-flush timing), depending on which fix shape is chosen.

## Suggested fix(es)

**Primary (reorder): recover-then-report.** On stall paths, run stall recovery (Step 18a) before the final report (Step 16/17):

- When a stall sets `STALL_TRACKING=true`, route to Step 18a stall recovery first (instead of "skip to Step 16").
- If recovery SUCCEEDS (`clear-stall` emits `CLEARED=true`) and re-enters the pipeline, let the natural terminal Step 16/17/18 render the final report ONCE with the true (e.g. merged) outcome.
- If recovery is TERMINAL (no recovery possible), THEN render the Step 16/17 "stalled" report, file the terminal report, and run Step 18b teardown.

**Alternative (surgical): defer the render.** Keep the Step 16 -> 17 -> 18a order but gate Step 17's final-report render + log flush on "no pending recoverable stall": defer/skip the render+flush while `STALL_TRACKING=true` until Step 18a resolves — terminal -> render "stalled" + file terminal report; success -> the post-recovery pipeline renders the real outcome.

Either shape ensures the final report and log flush reflect the true terminal state, rendered once, after the stall resolves.

## Open questions

- Does `/design` have an analogous "report before recovery" ordering (design-failure report vs. recovery/escalation)? The fix may need to apply there too.
- Log-flush specifics: should the pre-Step-17 / pre-ship log flush be deferred on stall paths? Note NEVER #16 blocks post-merge commits, so a late merged-state flush may not be committable — the fix should account for getting the *final* state into the committed run-log before merge, not after.
- Should the duplicate Step 16/17/18 execution be explicitly deduplicated, or is a single post-recovery render the cleaner outcome of the reorder?

## Test plan
(no test plan section in plan-file)
