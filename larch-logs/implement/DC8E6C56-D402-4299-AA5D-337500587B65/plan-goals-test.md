## Goal
Implement issue #5306: [IMPLEMENTING] [BUG] chore(larch-logs) design-run PRs accumulate unmerged: no auto sweep backstop.

## Implementation Plan
## Summary

Automated `chore(larch-logs)` design-run PRs have no durable, automatic merge path, so they accumulate unmerged. The only thing that auto-merges them is a per-PR detached, best-effort `ship design-log` waiter that, by its own documentation, "does not reliably survive the session that launched it." The intended durable backstop, `ship design-log-sweep`, has zero automatic callers anywhere in the repo — running it is a manual operator action. When the detached waiter dies before required CI goes green, nothing else ever merges the PR. On 2026-06-24, 14 such PRs had piled up over ~18 hours, all with green CI, and were cleared only by a manual admin-merge sweep.

## Original report

14 open `chore(larch-logs): design run <id>` PRs accumulated unmerged over ~18h (created 2026-06-23T22:06 → 2026-06-24T06:48): #5239, #5243, #5244, #5246, #5250, #5252, #5268, #5284, #5285, #5287, #5288, #5289, #5290, #5291. Every one had all required CI green and was `mergeable=MERGEABLE`, yet `mergeStateStatus=BLOCKED` with `reviewDecision=REVIEW_REQUIRED`. The backlog was cleared manually with `gh pr merge <n> --admin --squash --delete-branch` (all 14 merged, exit 0). This issue is to root-cause why they were not merged automatically.

Root cause has two layers:

1. **GitHub gate.** `main` has the "Code review" ruleset (id `14887924`) with `required_approving_review_count: 1` and `require_code_owner_review: true`. Automated log PRs never receive a review, so GitHub holds them at `BLOCKED` / `REVIEW_REQUIRED` indefinitely despite green CI. Only an `--admin` merge bypasses this. The separate "CI and branch safety" ruleset (id `14887920`) enforces required status checks with no review requirement and is not the blocker.
2. **larch gap (the actual defect).** The only automatic merge path is the per-PR detached, best-effort `ship design-log` waiter spawned by `_spawn_detached_admin_merge` in `python/design_log_publish_flow.py` (`subprocess.Popen(..., start_new_session=True)`). Its own docstring and `docs/run-logs.md` ("Reconciling stuck design-log PRs") state it "does not reliably survive the session that launched it, so design-log PRs can accumulate unmerged." The intended durable backstop `ship design-log-sweep` (`run_design_log_sweep` in `python/design_log_ship.py`) has no automatic callers anywhere in the repo. `docs/run-logs.md` says to "Run it on demand, or wire it to a recurring sweep (for example via `/loop`) to keep the backlog clear" — i.e., clearing the backlog is a manual operator action.

The sweep backstop was added recently (issue #5213 / PR #5232) but shipped without any automatic scheduler, so the documented "durable backstop" never actually runs unless a human types the command.

## Reproduction scenario

1. Run one or more `/design` sessions that each open a `chore(larch-logs): design run <RUN_ID>` PR on a `larch-logs/design-<RUN_ID>` branch.
2. End the Claude session (close the terminal, let the machine sleep, or otherwise let the parent process group exit) before required CI on the log PR goes green and the detached `ship design-log` waiter completes its admin-merge.
3. Observe that the log PR stays open: `mergeable=MERGEABLE`, `mergeStateStatus=BLOCKED`, `reviewDecision=REVIEW_REQUIRED`, with all required checks passing.
4. Note that nothing ever merges it automatically, because no scheduled or hooked process runs `ship design-log-sweep`. PRs continue to accumulate one per design run.

Observed directly today: 14 PRs over ~18h. Confirmed each was `MERGEABLE` + `BLOCKED` + `REVIEW_REQUIRED` with green required checks, then cleared all 14 with a manual `gh pr merge --admin --squash --delete-branch` (the exact operation the sweep performs).

## Expected behavior

`chore(larch-logs)` design-run PRs with green required CI are admin-squash-merged automatically and durably, independent of whether the originating Claude session is still alive. The backlog of such PRs trends to zero without manual operator intervention.

## Observed behavior

Log PRs accumulate unmerged indefinitely. Each is `mergeable=MERGEABLE` with all required checks green, but held at `mergeStateStatus=BLOCKED` / `reviewDecision=REVIEW_REQUIRED` by the "Code review" ruleset. The detached per-PR waiter is the only automatic merger and does not survive its launching session reliably; the durable sweep that would catch the survivors is never invoked automatically.

## Root cause analysis

Two interacting causes, with the second being the actionable defect:

1. **GitHub review gate (environmental, expected).** The "Code review" ruleset (id `14887924`) on `main` requires one approving review plus code-owner review. Automated log PRs structurally cannot satisfy this, so they require an `--admin` bypass to merge. This is working as configured and is not itself the bug.
2. **Missing durable/automatic invocation of the merge backstop (the defect).** The merge primitive is correct — `_merge_design_log_pr_if_green` / `run_design_log_sweep` call `gh.pr_merge(..., admin=True, merge_method="squash", delete_branch=True)`, which is exactly what cleared all 14 by hand. The gap is orchestration: the only automatic trigger is a detached, best-effort, session-bound waiter (`_spawn_detached_admin_merge`), and the documented durable backstop (`ship design-log-sweep`) has no scheduler, hook, CI workflow, or skill step that runs it. When the waiter dies early, the PR is orphaned with no safety net. This is a process/automation gap, not a code defect in the merge operation.

Confidence: high. The behavior is self-documented in `docs/run-logs.md` ("That waiter does not reliably survive the session that launched it, so design-log PRs can accumulate unmerged") and confirmed empirically by the 14-PR backlog and the successful manual sweep.

## Evidence

- `python/design_log_publish_flow.py` → `_spawn_detached_admin_merge`: spawns the only automatic merge trigger as a detached `subprocess.Popen(..., start_new_session=True)` running `cli.py ship design-log --pr-number <N>`. Docstring: "Best-effort: a launch failure leaves the PR open for manual/CI merge."
- `python/design_log_ship.py` → `run_design_log_sweep` and `_merge_design_log_pr_if_green`: the durable backstop. Merge uses `gh.pr_merge(..., merge_method="squash", admin=True, delete_branch=True)`. Docstring calls it "the durable backstop for the best-effort detached merge waiter ... which does not reliably survive the session that launched it."
- Full-repo search for callers of `design-log-sweep` / `run_design_log_sweep` / `sweep_main` across `skills/`, `hooks/`, `.github/workflows/`, `Makefile`, and cron configs returned no invocation (only the CLI verb registration in `python/cli.py`, the definition, tests, and prose in `docs/run-logs.md`).
- `python/cli.py`: registers verbs `("ship", "design-log")` → `design_log_ship:main` and `("ship", "design-log-sweep")` → `design_log_ship:sweep_main`.
- `docs/run-logs.md`, section "Reconciling stuck design-log PRs": documents the gap in plain language and recommends running the sweep on demand or wiring it to a recurring loop manually.
- GitHub rulesets on `main`: "Code review" (id `14887924`, `required_approving_review_count: 1`, `require_code_owner_review: true`) is the review gate; "CI and branch safety" (id `14887920`) enforces required status checks only.
- Observed backlog: 14 PRs (#5239, #5243, #5244, #5246, #5250, #5252, #5268, #5284, #5285, #5287, #5288, #5289, #5290, #5291), all `MERGEABLE` + `BLOCKED` + `REVIEW_REQUIRED` with green required checks; all cleared by a manual admin-squash-merge equivalent to the sweep.
- The sweep backstop string first appears in git history at the commit for issue #5213 / PR #5232; it shipped without an automatic scheduler.
- Repo state at investigation: `HEAD=3dcecdd1c`, branch `main`.

## Affected files

- `python/design_log_publish_flow.py` — owns `_spawn_detached_admin_merge`, the session-bound best-effort waiter that is the only automatic merge trigger today.
- `python/design_log_ship.py` — owns `run_design_log_sweep` (the durable backstop) and the correct admin-squash merge primitive; the function works but is never invoked automatically.
- `python/cli.py` — registers the `ship design-log` and `ship design-log-sweep` verbs.
- `docs/run-logs.md` — "Reconciling stuck design-log PRs" section; documents the manual-only nature of the backstop and would need updating once an automatic trigger exists.
- Likely target for a new automatic trigger (one of): a `/design` (and/or `/implement`) skill step, a SessionStart/SessionEnd hook under `hooks/`, or a scheduled workflow under `.github/workflows/`.

## Suggested fix(es)

Non-prescriptive; operator to choose direction:

- **Give the documented backstop an automatic trigger.** Run `ship design-log-sweep` from a session-independent place: at the start of every `/design` (and/or `/implement`) run, from a SessionStart hook, or as a scheduled GitHub Actions cron. A scheduled Actions workflow is the most session-independent, but the sweep currently runs under the operator's `gh` auth and needs admin merge rights, so a bot identity would need bypass-actor permission on the "Code review" ruleset.
- **Make the detached waiter durable.** Persist a pending-PR queue and re-spawn the sweep on the next session start so a dead waiter is recovered rather than orphaned.
- **Remove the need for `--admin` on these PRs.** Add the larch bot/app as a bypass actor on the "Code review" ruleset (id `14887924`), or exclude `larch-logs/` head branches from that ruleset, so automated log PRs can merge through the normal path once required CI is green.

Note: the merge primitive itself is not broken — the manual sweep equivalent cleared all 14 PRs cleanly. The fix is about durable/automatic invocation, not the merge operation.

## Open questions

- Preferred trigger surface: scheduled GitHub Actions cron (session-independent, needs a bot identity with bypass/admin merge rights) vs. a SessionStart hook / `/design` step (uses operator `gh` auth, but only fires when the operator runs larch)?
- Should the long-term fix also reduce reliance on `--admin` by granting a bot bypass actor on the "Code review" ruleset, or is admin-merge-by-sweep the intended steady state for these automated log PRs?
- Should `/implement` also trigger the sweep, or is `/design` (the producer of these PRs) the right and sufficient place?

## Test plan
(no test plan section in plan-file)
