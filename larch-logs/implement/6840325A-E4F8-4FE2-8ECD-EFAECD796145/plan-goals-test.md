## Goal
Implement issue #5648: [IMPLEMENTING] [BUG] [ship-pr-ci] orchestrator hang at CI-fix/conflict handoff (unobservable).

## Implementation Plan
## Summary

The operator observes (live) the `/implement` main agent **hanging indefinitely** after ship-pr hands off a CI failure or merge conflict — waiting instead of autonomously rebasing/fixing and continuing; a manual nudge ("rebase on latest main / fix CI and continue") usually unblocks it. Observed on Sonnet (200K context); Opus (large context) did better. The committed run logs can **neither reproduce nor cleanly refute** this, because the ship+CI phase has no committed observability (transcript flushes at Step 7a pre-ship; the ship `route-exit` handoff env is never committed). The actionable core is two-fold: **D1** make the handoff observable; **D2** harden the prompt-side ci-fix/conflict continuation so it cannot park. One of four related `[ship-pr-ci]` defects.

## Original report

Verbatim operator report: "main agent seemingly stuck waiting indefinitely in situations where CI showed merge conflicts or test failures. I manually intervened and told it to either rebase on latest main, fix merge issues, and continue, or fix CI problems and continue, which it usually did, unless I ran out of patience, and switched to Opus with large context (these were Sonnet with small 200K context)."

## Reproduction scenario

Not reproducible from committed logs (see Root cause / observability). Live repro: run `/implement --merge` on Sonnet/200K against a change that produces a red required check or a merge conflict at ship; observe whether the orchestrator autonomously executes the ci-fix/conflict continuation (read `ship-pr-ci-fix.md` → repair → re-invoke `step-8-ship.sh`) or parks on "waiting for completion." Capture the ship route-exit handoff (`.ship-route-exit-handoff.env`) and the post-Step-7a transcript to confirm.

## Expected behavior

After ship exits with a ci-fix handoff (`NEXT_ACTION=ci-fix` / `first-fixer-non-health`) or a conflict handoff, the orchestrator deterministically continues: performs the repair/rebase and re-invokes the ship driver, without operator intervention. A genuine `operator-bail` (e.g. `ci-fix-exhausted`) is the only state that should wait for the user.

## Observed behavior

- Live: indefinite wait after a CI conflict/failure; manual nudge required; Sonnet-prone, Opus-better.
- Committed logs: cannot show it. The ship phase produces no breadcrumbs (see sibling `[ship-pr-ci]` observability bug) and `session-transcript.jsonl` flushes at Step 7a (pre-ship), so a hang on the first ship/CI handoff is indistinguishable from a normal truncation.
- A 60-run census found NO committed hang and did NOT confirm the Sonnet correlation — but this is a blind spot, not exoneration: every handoff it could see was in runs that had already continued (survivorship); hung runs leave no trace.

## Root cause analysis

Two coupled problems:

- **D1 (observability — explains why it is undiagnosable):** `session-transcript.jsonl` is flushed/truncated at the Step 7a pre-ship boundary; runs only re-flush past 7a on CI-retry activity (so only *continuing* runs capture handoff turns). The ship route-exit handoff (`.ship-route-exit-handoff.env` / `.step-8-ship-handoff.json`) and post-ship task-output are never committed. Net: the ship/CI/handoff phase — including any hang — is invisible post-hoc.
- **D2 (the hang — suspected mechanism, operator-reported, not log-confirmed):** the CI-failure path is delegated to the prompt-side main agent by design. `ci_monitor.monitor` returns `NEEDS_USER_INPUT "first-fixer-non-health"` (`python/larch/implement/ci_monitor.py:1956-1963`); ship returns to the orchestrator; the ci-fix continuation (`skills/implement/SKILL.md:757`) is heavy and prompt-driven — MANDATORY read `ship-pr-ci-fix.md`, perform autonomous repair, re-invoke `step-8-ship.sh` — all after a background `<task-notification>`, with NO harness forcing function. There is a documented tension: the orchestrator is told to end the turn on premature notifications (SKILL NEVER #8), so distinguishing "ship driver done → run ci-fix" from "premature → wait for next notification" is left to model judgment; `operator-bail` uses `AskUserQuestion` (a legitimate wait). On small-context models the continuation can be dropped → indefinite park. This is consistent with the operator's Sonnet-vs-Opus observation but is NOT confirmed from logs (see D1).

## Evidence

- Operator live report (authoritative for the symptom).
- Code: `ci_monitor.py` `monitor()` first-fixer-non-health handoff; `skills/implement/SKILL.md:757` ci-fix continuation; `SKILL.md:752-760` post-driver branch skeleton; SKILL NEVER #8 premature-notification rule; `implement_dispatch.py:1560` `ship_route_exit_main` + `:1455` `_classify_ship_needs_user_reason`.
- Census (60 runs): no committed hang; "waiting@7a" endings are a flush artifact (present in 76% sonnet vs 94% opus runs); captured handoffs all continued — e.g. run 5F4CE4BD (sonnet): ship driver exit-3 → `NEXT_ACTION=ci-fix` → "Checks pass. Committing, pushing"; older breadcrumb runs show sonnet re-invoking the ship driver up to 12x (A335AEDF). These REFUTE a structural "sonnet can't ci-fix" theory but do not cover the blind spot.

## Affected files

- `python/larch/implement/ci_monitor.py` — `monitor()` CI-failure handoff.
- `skills/implement/SKILL.md` — ci-fix / conflict continuation contract; NEVER #8.
- `skills/implement/references/ship-pr-ci-fix.md`, `conflict-resolution.md`, `ship-pr-exit-matrix.md` — continuation procedures.
- `python/larch/implement/implement_dispatch.py` — `ship_route_exit_main`, the handoff env.
- `python/larch/report/run_logs.py` + the session-transcript flush boundary — observability.

## Suggested fix(es)

- **D1 first (enables diagnosis):** flush/commit the ship phase — move the transcript/log refresh to AFTER the ship route-exit, and persist `.ship-route-exit-handoff.env` + post-ship task-output into the committed run log. Overlaps the sibling `[ship-pr-ci]` observability bug.
- **D2:** reduce reliance on prompt-side continuation at the handoff — e.g. a deterministic driver/wrapper loop that performs ci-fix/reship without returning control to the prompt between iterations, or a stronger forcing function at the ship boundary that disambiguates "driver done → run ci-fix" from "premature notification → wait." Consider an idle-watchdog that surfaces a clear prompt if the orchestrator parks at a handoff.

## Open questions

- Is the hang at the FIRST handoff (invisible) or after some continuation? (Resolvable after D1.)
- Does the premature-notification rule (NEVER #8) cause the agent to end the turn on the ship driver's terminal notification? Instrument to confirm.
- The real Sonnet-vs-Opus hang rate, once D1 lands.

## Test plan
(no test plan section in plan-file)
