## Goal
Implement issue #5217: [IMPLEMENTING] [BUG] /implement ship-pr: redundant CI-triggering pushes and a false no-ci-checks-observed stall when the branch is behind main.

## Implementation Plan
## Summary

The `/implement` ship-pr driver (`python/ship.py`) makes **multiple head-moving pushes on a single fresh run** and, when the feature branch is **behind `main`**, **rebases mid-CI and then falsely stalls with exit 4 `no-ci-checks-observed` even though CI actually succeeds**. These are two distinct but related defects in the same push/CI-monitor pipeline.

## Required invariant (the fix target)

**On a run whose CI passes on the first try, the entire run must produce EXACTLY ONE push** — the original push, containing **both the main code change and the flushed run logs together** in a single commit.

- The run logs must be flushed/committed **into that same single push**, not pushed separately afterward.
- The **only** additional pushes permitted are CI-failure remediation pushes: CI fails → ship-pr bails to the main agent → the main agent fixes the CI issue → one more push. No CI failure ⇒ no second push.
- A branch being **behind `main` is not a reason to push again**. A behind-`main` branch is mergeable via squash (empirically confirmed: PR #5214 was `mergeable=MERGEABLE` while behind `main`), so the happy path must **not** rebase/force-push.

Today the happy path violates this: a fresh, behind-`main` run emits up to **three** head-moving pushes (`pr-prep`, `post-ensure-pr`, `rebase`) before the first CI run can even finish.

## Two bugs

1. **Redundant head-moving pushes.** A fresh run emits a second `Flush+Push` (`post-ensure-pr`) almost immediately after the first (`pr-prep`), then a third (`rebase`) when behind `main`. Each moves `HEAD` and re-triggers CI.
2. **False `no-ci-checks-observed` stall.** After the rebase force-push to a new head SHA, the CI monitor grants only a **120s** empty-checks window for GitHub to register checks, vs **300s** on the initial head. The window expires before GitHub attaches checks to the force-pushed head, so the driver exits **4** `no-ci-checks-observed` — while the checks then register and pass green (false negative).

## Symptoms

- Ship-pr log shows two `Flush+Push` breadcrumbs back-to-back (`pr-prep` then `post-ensure-pr`), the second firing almost immediately after the first and before the first CI run completes.
- On a behind-`main` branch, a third `Flush+Push` (`rebase`) force-pushes a new head, then the run exits **4** with `detail=no-ci-checks-observed` / `outcome=STALLED`.
- The PR's CI subsequently runs and goes **fully green**, so the stall is a **false negative**, not a real CI failure. The run is left as a stalled PR requiring manual merge.

## Context (reproduction run)

- Run `712C403F-464E-4937-9459-179BB7C9A9DF` (`/im --emergency 5209`), PR #5214, issue #5209.
- Committed run logs: `larch-logs/implement/712C403F-464E-4937-9459-179BB7C9A9DF/`.
- The feature branch was **behind `origin/main`** (other PRs merged into `main` during the run).

Observed ship-pr breadcrumbs (single fresh run):

```
ship.py: pr-prep: postbump/Flush+Push        # flush logs + push  (head-moving)
ship.py: pr-create: PR                         # create PR
ship.py: post-ensure-pr: Flush+Push            # flush logs + push  (head-moving, ~immediately after)
ci_monitor: CI pending after 88s -> rebase     # CI was running (pending) on the original head
ship.py: rebase: Flush+Push                    # rebase force-push -> NEW head SHA
ci_monitor: CI NO_CHECKS after 126s -> bail (no-ci-checks-observed)
EXIT 4 / outcome=STALLED
```

The original head's CI was `pending` (i.e. **already running and healthy**). The mid-flight rebase discarded it, created a new head, and the monitor bailed before GitHub re-registered checks on that head. The checks then ran green and the PR had to be merged manually (admin squash — CI was green, only branch-protection review blocked).

## Root cause — Bug 1: redundant head-moving pushes

The fresh-run path in `ship.py` `run_ship` performs **two** log-flush-and-push operations, plus a third on rebase:

1. **`pr-prep` phase** — `run_logs.flush_logs_pre(...)` commits run logs, then the `postbump` step pushes the branch (`_breadcrumb("pr-prep", "postbump/Flush+Push")`).
2. **`pr-create` phase** — `pr.ensure_pr(...)` creates the PR on the already-pushed branch.
3. **`post-ensure-pr` phase** — `_post_ensure_flush_and_push(...)` runs **another** `run_logs.flush_logs_pre(...)` (a second commit) and `push.push_branch(...)` (a second push). On `open-pr` **resume** it already skips the re-flush (`skip_reflush = resume.start == "open-pr"`, the issue #5186 fix), but on a **fresh** run it still re-flushes and re-pushes.
4. **`rebase` phase** — `_ship_rebase_phase(...)` does a pre-rebase `flush_logs_pre` plus `rebase.rebase_and_push(...)` (force-push) whenever the merge loop decides to rebase.

The second flush exists because PR-creation-dependent log content (the `final-summary.md` `PR_NUMBER`/`PR_URL`, accrued token/timing) is not knowable until **after** the first push creates the PR. So `_post_ensure_flush_and_push` re-commits that delta and pushes again, moving `HEAD` and re-triggering CI right after the PR-creation push.

This **contradicts the documented contract** in `skills/implement/SKILL.md` (Step 7a "Pre-ship log flush"), which states the driver should fold `final-summary.md` with **placeholder** PR fields into the **pre-PR** commit, and then refresh the live PR URL **"via API only — no second commit, no second push."** The implementation performs a second commit and push on fresh runs.

## Root cause — Bug 2: false `no-ci-checks-observed` stall

Two interacting causes in `python/ci_monitor.py`:

**(a) The monitor rebases while CI is healthy and pending.** `ci_monitor.decide()` returns `rebase` whenever `status == "pending"` **and** the branch is `behind`:

```python
if status.status == "pending":
    return Decision(action="rebase" if behind else "wait")
```

Because the branch was behind `main`, the monitor rebased **while CI was still running** on the original head. This **throws away an in-flight, healthy CI run** and creates a brand-new head SHA that must re-register checks from scratch. (The rebase was also unnecessary: the branch was squash-mergeable while behind `main`.)

**(b) The post-rebase empty-checks window is too short.** `_empty_checks_params_for_monitor()` grants the **initial** head a generous startup deadline but a **head-changed** (rebased/force-pushed) head only the short post-fix grace:

```python
if current_head != last_monitored_head:
    return config.CI_WAIT_POST_FIX_EMPTY_CHECKS_GRACE_SEC, 0   # 120s grace
if initial_startup_deadline_available:
    return 0, config.CI_WAIT_INITIAL_EMPTY_CHECKS_GRACE_SEC     # 300s deadline
return 0, 0
```

Relevant `python/config.py` values:

- `CI_WAIT_INITIAL_EMPTY_CHECKS_GRACE_SEC = 300` (initial head)
- `CI_WAIT_POST_FIX_EMPTY_CHECKS_GRACE_SEC = 120` (head changed, e.g. after rebase)

A **force-pushed head faces the same GitHub check-registration latency as a brand-new PR**, but is given **120s instead of 300s**. When GitHub took longer than ~120s to attach the workflow run to the force-pushed head, the empty-checks grace path emitted `CI_WAIT_BAIL_NO_CHECKS_OBSERVED` and the driver exited 4 — even though the checks then registered and passed.

This is the same class of failure as the issue #5186 "perpetual `no-ci-checks-observed` loop," but reached on a **fresh** run via the rebase head-change rather than a resume re-flush.

## How the two interact

The redundant pushes (Bug 1) and the mid-CI rebase (Bug 2) compound: each head-moving push re-triggers CI on a new head, and the monitor's habit of rebasing a pending-but-behind branch guarantees at least one force-push whose checks have not registered when the short 120s window expires. The single up-to-date push the invariant demands would avoid both.

## Suggested fix

Make the happy path satisfy the **one-push invariant** and remove the false stall:

1. **Collapse to a single pre-PR flush+push (enforces the invariant; Bug 1).** Make the `pr-prep` flush the **sole** log-commit point: commit `final-summary.md` with **placeholder** PR fields into the pre-PR commit so code + logs ride the PR's initial push together. On **fresh** runs, make `_post_ensure_flush_and_push` **push-only / no-op** (mirror the existing `open-pr` `skip_reflush` path) and move the live-PR-URL refresh to **API-only** (`final-report write --comment-only`), per the already-documented `SKILL.md` contract. Eliminates the `post-ensure-pr` head move.

2. **Never rebase on the happy path (Bug 2a).** A behind-`main` branch is squash-mergeable (confirmed on PR #5214), so do **not** rebase/force-push when CI is pending or passing. In `ci_monitor.decide()`, when `status == "pending"`, return `wait` (not `rebase`) even if `behind`; let CI finish on the original head and merge. If a repo genuinely enforces "branch must be up to date before merge," perform **one up-front rebase BEFORE the `pr-prep` flush+push** (so the single push is already on an up-to-date head) rather than a mid-flight rebase. Either way, first-try CI success ⇒ no extra push.

3. **Give a rebased/force-pushed head the full startup grace (defensive backstop; Bug 2b).** For the rare case a force-push does occur (e.g. a genuine merge conflict requiring a rebase), `_empty_checks_params_for_monitor()` should grant a force-pushed head the generous `CI_WAIT_INITIAL_EMPTY_CHECKS_GRACE_SEC` (300s) startup deadline instead of the 120s post-fix grace, because the new head must re-register checks from scratch. This prevents the premature `no-ci-checks-observed` bail even when a rebase is unavoidable.

Fixes 1 and 2 together deliver the invariant: on first-try CI success, **exactly one push for the whole run**. Fix 3 hardens the unavoidable-rebase path against the registration race.

## Affected files / symbols

- `python/ship.py` — `run_ship` (`pr-prep` / `pr-create` / `post-ensure-pr` phases), `_post_ensure_flush_and_push`, `_ship_rebase_phase`.
- `python/ci_monitor.py` — `decide` (pending+behind → rebase), `_empty_checks_params_for_monitor` (120s vs 300s), `_startup_deadline_step` (`no-ci-checks-observed` bail).
- `python/config.py` — `CI_WAIT_INITIAL_EMPTY_CHECKS_GRACE_SEC`, `CI_WAIT_POST_FIX_EMPTY_CHECKS_GRACE_SEC`, `CI_WAIT_BAIL_NO_CHECKS_OBSERVED`, `CI_MONITOR_MAX_REBASES`.
- `skills/implement/SKILL.md` — Step 7a "Pre-ship log flush" contract ("no second commit, no second push"), which the implementation currently violates on fresh runs.

## Notes / open questions

- **Idempotency / squash-merge.** The single pre-PR commit must still carry token/timing/transcript log data into the squash-merge tree (the stated reason the post-ensure flush exists). Folding it into the one pre-PR commit with placeholder PR fields satisfies this.
- **Branch-protection up-to-date rule.** If any repo requires up-to-date-before-merge, prefer the **single up-front rebase** (before the first push/CI) over mid-flight rebases, preserving the one-push invariant.
- **Prior art.** Related: #5186 (resume re-flush loop), #4924 / #4867 / #4866 (empty-checks grace tuning). This issue is the **fresh-run rebase** variant those did not cover.
- Reproduced on larch `51.3.13`, run `712C403F-464E-4937-9459-179BB7C9A9DF`, PR #5214.

## Test plan
(no test plan section in plan-file)
