## Goal
Implement issue #6059: [IMPLEMENTING] [BUG] Ship-time architectural-guidelines note dropped on HEAD drift; recovery retry….

## Implementation Plan
## Summary

During `/implement` Step 8+ ("ship PR"), the orchestrator's staged Architectural Guidelines assessment ("Consulted ARCHITECTURAL_GUIDELINES.md; no deviations identified.") was dropped and replaced with the generic fallback message `The architectural guideline note was dropped because HEAD drifted after staging.`, on a clean, single-shot run with no CI-fix or conflict-resolution retries — **despite the ship-time refresh-retry recovery fix from #5969/PR #5997 being verifiably present in the run's tree** (confirmed via `git merge-base --is-ancestor`). This is a residual gap in the already-"fixed" ship-time pin path (`ship_guidelines.py`), not a recurrence of #5969's original logic-inversion bug, and not the same call site as the more recent closeout-path issues #6021/#6034.

## Original report

root cause of The architectural guideline note was dropped because HEAD drifted after staging.

## Reproduction scenario

Not deterministically forced (depends on real concurrent upstream activity), but the mechanical shape, confirmed against this exact run:

1. Run `/implement --merge <issue-N>` on an issue whose plan touches files covered by `ARCHITECTURAL_GUIDELINES.md`.
2. Step 7a's "Architectural guidelines (Phase A — staging)" runs: the main agent reads `ARCHITECTURAL_GUIDELINES.md`, compares it against the materialized implementation diff (fingerprinted against `origin/main` at that instant), and stages a clean assessment via `step-architectural-guidelines-write-staged.sh`.
3. Step 8+ invokes `python/cli.py ship pr` (`python/larch/implement/ship.py`). On the fresh (first-time) path, `finalize.postbump()` runs unconditionally before PR creation: it calls `_retry_fetch(remote="origin", ref="main")` then `git.rebase(...)` onto the freshly fetched `origin/main` (`python/larch/state/finalize.py`, `_rebase_no_push`).
4. If `origin/main` gained new commits between step 2 (Phase A staging) and step 3's fetch — plausible and observed in this very run, where a sibling round-X issue's PR had merged to `main` only minutes earlier — the rebase changes HEAD's SHA and/or the effective merge-base against `origin/main`.
5. `ship.py` then calls `_pin_and_load_guidelines_note(head_sha=<post-rebase HEAD>, base_ref="origin/main", repo_root=...)` immediately before `compose_pr_body(...)`. The live diff fingerprint no longer matches the fingerprint stored at staging time, so `pin_note_from_staged` fails on the first attempt (expected/correct — this is real drift). Per the #5969 fix, `refresh_staged_assessment_for_current_head` then unconditionally recomputes the live diff/fingerprint and re-stamps the staged sidecar, returning `True` (confirmed by reading the current source: it no longer bails on a fingerprint mismatch, only on missing inputs or I/O errors). `_pin_and_load_guidelines_note` then retries `pin_note_from_staged`, which recomputes the live diff **a third, independent time** via `_staged_fingerprint_valid` and compares it against what the refresh step (the *second* independent computation) just wrote.
6. In this run, that retry still failed and the drop notice was rendered — meaning the second and third independent live-diff computations must have disagreed, which is only possible if the repository state (`origin/main` and/or HEAD) changed again in the narrow window between them.

Concretely observed: `/implement --merge 5978` (this session), RUN_ID `8D812696-8581-4C0C-AEF3-8F6634D73683`, PR #6058, merged as `admin_merged`. Step 7a / Phase A staged a clean assessment right after a manual rebase onto `b6924719b` ("Fixes #5979"). The final run summary nonetheless showed:

```
## Architectural guidelines

The architectural guideline note was dropped because HEAD drifted after staging.
```

`git merge-base --is-ancestor b75ab8ae0 HEAD` (where `b75ab8ae0` is "Fixes #5969: Implement issue #5969 (#5997)") returns true against this run's final merge commit `c683af997` — the #5969 fix was present the entire time, 43 commits ahead of the branch point I rebased onto. This is a busy shared repo: 8 other issues in the same "md-to-py-XI" round were open/landing around the same time as this run (e.g. #5979, #5980), which is exactly the kind of concurrent-upstream-activity condition needed to trigger a second drift inside the narrow refresh-then-retry window.

## Expected behavior

When Phase A staged a valid assessment and the orchestrator's own diff intent has not changed, the note should survive an intervening mechanical rebase-onto-latest-main (no real content conflict), even under realistic concurrent-upstream-activity conditions on a shared repo — i.e., the ship-time recovery path should not depend on the repository staying perfectly static across three independent `git diff`/`merge-base` subprocess calls. If the note is dropped anyway, a diagnostic trace should reliably reach the committed run log (`larch-logs/implement/<run-id>/execution-issues.md`) so operators can audit why after the fact.

## Observed behavior

The staged "no deviations identified" assessment was replaced by the generic drop notice in both the PR body and the final run summary. `larch-logs/implement/8D812696-8581-4C0C-AEF3-8F6634D73683/` (the committed run log for this exact run) contains no `execution-issues.md` file at all, and the final summary reported `Warnings: 0`, even though the code path that renders the drop notice is proven (by existing unit tests) to also append a warning to `execution-issues.md` on this exact fallback.

## Root cause analysis

**Confirmed NOT a recurrence of #5969**: #5969 ("staged-assessment refresh returns False on fingerprint drift, so the ship-time retry never recovers") was fixed by commit `b75ab8ae0` (PR #5997), which changed `refresh_staged_assessment_for_current_head` (`python/larch/core/architectural_guidelines.py`) to unconditionally recompute and re-stamp the staged assessment on drift, rather than bailing when the live fingerprint differs from the stored one. Reading the current source confirms this fix is in place, and `git merge-base --is-ancestor b75ab8ae0 HEAD` confirms it was present in this run's tree throughout. **Also confirmed NOT the same call site as #6021** ("closeout-time guideline pin lacks refresh retry on drift" — `python/larch/state/closeout.py`'s best-effort pin, used only for stall/closeout-only flows) or **#6034** ("Terminal-stall closeout path never pins" — `step_16_16a` in `python/larch/report/final_report.py`, the terminal-unrecoverable-stall path). This run reached the normal green Step 16/17 path with `NEXT_ACTION=complete` on the very first `ship pr` invocation — no stall, no CI-fix, no resume — so the closeout call sites in #6021/#6034 were never even reached.

Likely root cause (traced from source; the precise trigger for *this* run is not independently confirmed because no diagnostic trace survived — see Evidence):

`ship_guidelines._pin_and_load_guidelines_note` (`python/larch/implement/ship_guidelines.py:95-155`) performs up to **three independent** live-diff/fingerprint computations without caching or reusing any single result:
1. The initial `pin_note_from_staged` → `_staged_fingerprint_valid` computes live diff #1 and compares to the staged fingerprint (from Phase A staging time). Fails on genuine drift — correct.
2. `refresh_staged_assessment_for_current_head` computes live diff #2 (independently, a fresh `git merge-base` + `git diff`) and unconditionally re-stamps the staged sidecar with it (the #5969 fix). This is expected to succeed.
3. The retried `pin_note_from_staged` → `_staged_fingerprint_valid` computes live diff #3 (independently, yet another fresh `git merge-base` + `git diff`) and compares it to what step 2 just wrote.

Steps 2 and 3 are only guaranteed to agree if the repository (`origin/main` local ref and `HEAD`) is perfectly static between them. `finalize.postbump()` (`python/larch/state/finalize.py`, `_retry_fetch` + `git.rebase` in `_rebase_no_push`) runs an unconditional fresh fetch + rebase onto `origin/main` immediately before this whole sequence, on every fresh `ship pr` invocation (`python/larch/implement/ship.py` lines ~327-349) — and on a shared, actively-developed repo (confirmed here: sibling round-X issues #5979/#5980 landing around the same time), a second commit landing on `origin/main` between computations #2 and #3 is a real, non-hypothetical possibility, not just a theoretical race.

Existing test coverage for the recovery path (`test_pin_and_load_guidelines_note_recovers_when_diff_changes_with_repo` in `python/tests/implement/test_ship.py`) only proves recovery succeeds when `materialize_implementation_diff` is mocked to return a **fixed, non-moving** value across all internal calls — it does not exercise the case where the live diff is itself a moving target across the three internal recomputations.

Separately, the mechanical warning that should accompany this fallback (`_log_guidelines_ship_warning` appending to `execution-issues.md` under `Warnings`, proven by `test_pin_and_load_guidelines_note_returns_drop_notice_on_fingerprint_mismatch`) did not reach the committed run log for this run, removing the only mechanism that could have confirmed, after the fact, whether a second concurrent drift (vs. some other, as-yet-unidentified cause) actually occurred.

## Evidence

- `python/larch/core/architectural_guidelines.py:32` — `DROPPED_NOTE_MESSAGE` (the exact fallback text observed).
- `python/larch/core/architectural_guidelines.py:471-514` — `refresh_staged_assessment_for_current_head`: confirmed current source no longer bails on fingerprint mismatch (the #5969 fix), only on missing inputs or I/O errors.
- `python/larch/implement/ship_guidelines.py:95-155` — `_pin_and_load_guidelines_note`: up to three independent live-diff computations (initial check, refresh, retry check), none of which reuse a prior result.
- `python/larch/implement/ship.py:327-416` — fresh-path sequence: `postbump_preflight` → `finalize.postbump` (fetch + rebase onto `origin/main`) → `compose_head_sha = git.try_rev_parse(...)` → `_pin_and_load_guidelines_note(...)` → `compose_pr_body(...)`.
- `python/larch/state/finalize.py` — `_retry_fetch`, `_rebase_no_push`, `postbump` (unconditional fetch+rebase-onto-`origin/main` on the fresh path).
- `python/tests/implement/test_ship.py:4777-4809` — `test_pin_and_load_guidelines_note_recovers_when_diff_changes_with_repo`: proves recovery only under a mocked, non-moving live diff; does not exercise a moving/unstable live diff across the three internal calls.
- `python/tests/implement/test_ship.py:4758-4774` — `test_pin_and_load_guidelines_note_returns_drop_notice_on_fingerprint_mismatch`: proves the drop-notice fallback and its accompanying `execution-issues.md` warning string (which did not appear in this run's committed log).
- Live evidence, this session: `/implement --merge 5978` (RUN_ID `8D812696-8581-4C0C-AEF3-8F6634D73683`, PR https://github.com/character-ai/larch/pull/6058, merged `admin_merged`). Phase A staged a clean assessment right after rebasing onto `b6924719b` ("Fixes #5979"); the final run summary nonetheless rendered the drop notice. `larch-logs/implement/8D812696-8581-4C0C-AEF3-8F6634D73683/` (committed to `main`) has no `execution-issues.md` and the run reported `Warnings: 0`.
- `git merge-base --is-ancestor b75ab8ae0 HEAD` (where `b75ab8ae0` = "Fixes #5969: Implement issue #5969 (#5997)", committed 2026-07-01 21:56:44 -0700) returns true against this run's merge commit `c683af997` — the #5969 fix was present throughout this run, 43 commits ahead of the rebase branch point.
- Related history (same bug family, all `[DONE]`/closed, none currently open): #5675 (original), #5754 (postmerge git-checkout-main variant), #5337 (implement Phase B variant), #5969 (ship-time refresh-returns-False fix, confirmed present here), #6021 (closeout-time best-effort pin lacks refresh retry — different call site, `closeout.py`), #6034 (terminal-stall closeout path never pins at all — different call site, `step_16_16a`). None of these cover the ship-time three-independent-computation race identified here.

## Affected files

- `python/larch/implement/ship_guidelines.py` — `_pin_and_load_guidelines_note`'s three independent live-diff computations are the mechanism that can disagree under real concurrent drift.
- `python/larch/implement/ship.py` — sequences `postbump()` (which can rebase/advance HEAD via a fresh fetch) immediately before `_pin_and_load_guidelines_note()` / `compose_pr_body()`, creating the drift window in the first place.
- `python/larch/state/finalize.py` — `postbump` / `_rebase_no_push` / `_retry_fetch`: the unconditional fetch+rebase that can move HEAD and the merge-base after Phase A staging.
- `python/larch/core/architectural_guidelines.py` — `pin_note_from_staged`, `refresh_staged_assessment_for_current_head`, `_staged_fingerprint_valid`: the fingerprint comparison and refresh primitives; confirmed correct per the #5969 fix, but each independently re-derives the live diff.
- `python/tests/implement/test_ship.py` — existing coverage proves the fallback and a mocked-stable recovery, but not a moving/unstable live-diff recovery scenario across three independent calls.
- `larch-logs/implement/8D812696-8581-4C0C-AEF3-8F6634D73683/` — committed run log missing the `execution-issues.md` trace that should accompany this fallback.

## Suggested fix(es)

1. Compute the live diff **once** per `_pin_and_load_guidelines_note` call and reuse that single value for both the initial validity check and the refresh, instead of up to three independent `git diff`/`merge-base` subprocess calls that can each observe a different repo state. This removes the internal race entirely rather than just narrowing its window.
2. If a single-computation redesign is not desired, make the recovery robust to a second drift: loop the refresh+pin cycle a small bounded number of times (e.g. 2-3) until the live diff stabilizes, rather than exactly one retry.
3. Guarantee that `execution-issues.md` warnings appended during Step 8+ (after Step 7a's "primary" pre-ship flush) reliably reach the committed run log — e.g., verify Step 18's teardown "safety net" flush actually captures late Step-8-appended entries, or have the ship driver flush execution-issues immediately after logging this specific warning. This is the same observability gap noted in this issue's own audit trail (this run has `Warnings: 0` and no committed `execution-issues.md` despite the code path being proven to log a warning on this fallback).
4. Consider persisting enough diagnostic detail (compared fingerprints, base ref, head shas at each computation) in the dropped-note artifact or execution-issues entry so an operator can distinguish "second concurrent drift" from any other cause after the fact, without needing to reconstruct the timeline from source the way this issue had to.

## Open questions

1. Is a single-live-diff-computation redesign (suggested fix 1) preferable to a bounded retry loop (suggested fix 2), given `ship pr`'s already-long fixed timeouts and the cost of extra `git diff`/`merge-base` subprocess calls? The single-computation approach also removes a class of bug (three independently-reasoned-about call sites) rather than just narrowing the race window.
2. Should `execution-issues.md` warnings appended during Step 8+ have a guaranteed flush-to-committed-log path independent of Step 7a's "primary" flush and Step 18's "safety net", given this run shows the safety net did not catch this entry? This observability gap has now affected at least two issues in this family (this one, and the audit trail note in #6021's own evidence section referencing OOS_1/run-statistics showing "0 OOS filed" for a related gap).
3. Given the frequency of this bug family (5+ prior closed issues, one titled "~90% of runs"), would a structural test that runs `ship_guidelines._pin_and_load_guidelines_note` under a genuinely mutating fake repo (e.g. a fixture that advances `origin/main` between the mocked calls) be a worthwhile permanent regression guard, versus the current fixed-mock test?

## Test plan
(no test plan section in plan-file)
