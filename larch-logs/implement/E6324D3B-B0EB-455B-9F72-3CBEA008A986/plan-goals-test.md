## Goal
Implement issue #6117: [IMPLEMENTING] [BUG] /design escalation-success reporter falls back to compose-status-missing instead of filing or failing loudly.

## Implementation Plan
## Summary

`/design`'s auto error-reporting mechanism (`python/cli.py design failure-report`, implemented in `python/larch/design/design_terminal.py`) is supposed to file a follow-up GitHub issue documenting a run that needed escalation recovery (main-agent tie-break vote, postplan operator prompt, panel degradation, etc.) even when the overall design outcome is `approved`. On a larch dev-clone ("Tier A" / `surface="issue-input"`), the status field that tracks whether that follow-up report was actually filed can end up permanently unset due to several silent-return branches, so the reporter falls back to writing an uninformative local `compose-status-missing` note instead of either filing a real issue or cleanly no-op'ing.

## Original report

I ran `/design` end-to-end for issue #6090 (fixing `/implement`'s post-Step-0 launcher-resolution bug). The run completed successfully: plan drafted, reviewed across 2 rounds with real findings applied each round, Gate C approved, an OOS issue filed (#6110), and the plan published to #6090 (renamed to `[DESIGNED]`). Step 6 cleanup ran and removed the session tmpdir.

During Step 5 finalize, a sidecar file `design-report-gate-sidecars.md` was emitted with this content and surfaced to me as part of the mandatory final-summary emit:

```
### [Bug] /design report fallback required

The /design failure reporter could not safely file an issue.

| Field | Value |
|---|---|
| Outcome | `approved` |
| Reason | `compose-status-missing` |

Use the local artifacts in `DESIGN_TMPDIR` to investigate. This fallback contains no log tail.
```

I asked what this meant. Investigation (below) traced it to a real gap in the reporter's own Tier-A code path, not to anything wrong with the design output itself.

## Reproduction scenario

Not independently reproduced end-to-end (the triggering session's `$DESIGN_TMPDIR` was already cleaned up by Step 6 before I investigated, so the exact runtime env files that would show which specific branch fired are gone). Based on static code reading, the shape that reproduces this:

1. Run `/design` on a larch dev-clone (where `surface` resolves to `"issue-input"`, i.e. Tier A — see `_tier_a_allowed`/`report_surface()` in `design_terminal.py`).
2. Have the run reach a final outcome of `approved` (or `approved-partition`) where `escalation_evidence_present()` is true (a non-empty escalation ledger/fallback/marker file, or an `execution-issues.md` "Tool Failure: record-escalation" heading) but `panel_failure_evidence_present()` is false (i.e., the escalation was something other than a review-panel failure — for example a `main-agent-vote-required`/`main-agent-apply-required`/`postplan-operator-required` event during plan review, which is exactly what "2 rounds, real findings applied, findings needed application" implies).
3. In `compose_report()` (`python/larch/state/_report.py:527-705`), the `surface == "issue-input"` path reaches the final `return 0` at line 705 without ever calling `emit(key="STALL_RECOVERY_REPORT_STATUS", ...)` — that emit only happens for the `dry-run` branch (line 698) or a legacy-test-surfaces branch (line 700-701).
4. `file_tier_a_after_compose()` (`design_terminal.py:535-572`) is the only mechanism meant to backfill that status afterward. It is called unconditionally when `surface == "issue-input"`, both for the escalation-success path (`design_terminal.py:731-732`) and the terminal-failure path (line 675-676).
5. Inside `file_tier_a_after_compose`, at least four branches `return` without ever appending anything to `compose_env` (so the status stays unset): (a) line 542-543, when the `dedup_tier_a_report_main` subprocess itself exits non-zero; (b) line 549-550, when the dedup status is some value other than the expected `{no-match, lookup-failed-open}`; (c) line 567-568, when the `file-failure-report-cross-repo.sh` cross-repo filing subprocess exits non-zero; (d) implicitly, when the final `_run_stall_main(...)` normalization call at line 570 returns non-zero — there is no `else` branch, so nothing is appended.
6. `handle_compose_outcome()` (`design_terminal.py:574-599`) then reads `STALL_RECOVERY_REPORT_STATUS` from `compose_env`, finds it empty, and its one retry path (line 576-582) only re-attempts `file_tier_a_after_compose` when `panel_failure_evidence_present()` is also true. Since the escalation in this scenario was not a panel failure, that condition is false, so no retry happens, and the code falls through to the final catch-all at line 599: `write_fallback_chat("compose-status-missing" if not status else ...)`.

## Expected behavior

The reporter should either successfully file (or dedup-skip) a real escalation-success report, or fail loudly/log clearly which specific step failed and why (helper missing, `gh repo view` unresolved, subprocess exit code, etc.) — not silently collapse every unhandled internal branch into the same generic, non-actionable `compose-status-missing` local note.

## Observed behavior

A local-only sidecar note reading "The /design failure reporter could not safely file an issue" with `Reason: compose-status-missing` and no further diagnostic detail ("This fallback contains no log tail"), surfaced to the operator via the mandatory final-summary sidecar emit, for an otherwise fully successful `/design` run.

## Root cause analysis

Likely root cause, with medium-high confidence from static code reading: `file_tier_a_after_compose()` in `python/larch/design/design_terminal.py` has multiple internal branches that can silently fail to backfill `STALL_RECOVERY_REPORT_STATUS` into `compose_env`, and `handle_compose_outcome()`'s only recovery attempt for a missing status is gated behind `panel_failure_evidence_present()`, which is specific to review-panel failures and does not cover other escalation causes (main-agent vote/apply, postplan operator prompts). Any escalation-success run on a Tier-A (dev-clone) install whose escalation was not a panel failure, combined with any of the four silent-return branches inside `file_tier_a_after_compose` actually firing, reproduces this.

I could not pin down from static reading alone *which* of the four branches fired in my specific run, since the session tmpdir (`design-failure-tier-a-dedup.env`, `design-failure-tier-a-dedup.stderr.log`, `design-failure-tier-a-file.env`, `design-failure-tier-a-file.stderr.log`) was already removed by Step 6 cleanup before I investigated. That diagnostic gap is itself part of the bug: `write_fallback_chat("compose-status-missing")` explicitly tells the operator to "use the local artifacts in DESIGN_TMPDIR to investigate," but by the time the sidecar is actually surfaced to the operator (after Step 6 cleanup has already run), those artifacts are gone in the success/cleanup-eligible case.

## Evidence

- `python/larch/cli.py:239` registers `("design", "failure-report")` → `larch.design.design_lifecycle.failure_report_main`.
- `python/larch/design/design_lifecycle.py:112-128` imports `failure_report_main` from `design_terminal`.
- `python/larch/design/design_terminal.py:679-689`: outcome `approved`/`approved-partition` with no operator sentinel and `escalation_evidence_present()` true proceeds to compose an `escalation-success` report.
- `python/larch/design/design_terminal.py:494-502` (`panel_failure_evidence_present`) vs. `504-512` (`escalation_evidence_present`): two different, non-overlapping evidence checks — the former is a strict subset of escalation causes.
- `python/larch/design/design_terminal.py:574-599` (`handle_compose_outcome`): the retry-then-fallback logic and the final `write_fallback_chat("compose-status-missing" ...)` catch-all.
- `python/larch/design/design_terminal.py:535-572` (`file_tier_a_after_compose`): the four silent-return branches described above.
- `python/larch/design/design_terminal.py:731-732`: unconditional call to `file_tier_a_after_compose(output)` for `surface == "issue-input"` in the escalation-success path.
- `python/larch/state/_report.py:683-705` (`compose_report`): confirms no `STALL_RECOVERY_REPORT_STATUS` emit on the plain `issue-input` non-dry-run path; the function returns 0 at line 705 with no such emit in that branch.
- `scripts/file-failure-report-cross-repo.sh` exists and is executable in this clone, and `gh repo view` resolves `character-ai/larch` successfully in this environment, so the two earliest "helper missing" / "repo unresolved" branches in `dedup_tier_a_report` (`python/larch/state/_report.py:748-757`) are unlikely to be the specific trigger here — the deeper dedup/filing logic past that point is the more likely culprit but was not fully traced.

## Affected files

- `python/larch/design/design_terminal.py` — `handle_compose_outcome`, `file_tier_a_after_compose`, and the escalation-success branch of `failure_report_core` (approx. lines 494-735).
- `python/larch/state/_report.py` — `compose_report` (approx. lines 527-705) and `dedup_tier_a_report` (approx. lines 716+).
- `scripts/file-failure-report-cross-repo.sh` — the cross-repo filing helper invoked from `file_tier_a_after_compose`.
- Step 6 cleanup ordering relative to this reporter (`skills/design/references/finalize-step5.md` / `skills/design/SKILL.md` Step 6) — worth checking whether diagnostic artifacts referenced by the fallback message should be preserved (or copied) when this specific fallback fires, even on an otherwise cleanup-eligible successful run.

## Suggested fix(es)

No concrete fix identified yet; possible directions for `/design` to evaluate:

- Make each silent-return branch inside `file_tier_a_after_compose` emit a distinct, specific status (e.g. `tier-a-dedup-helper-failed`, `tier-a-dedup-status-unexpected:<status>`, `tier-a-file-helper-failed`, `tier-a-normalize-failed`) into `compose_env` instead of returning bare, so `handle_compose_outcome` can report *why* filing didn't happen instead of a generic catch-all.
- Broaden (or replace) the `panel_failure_evidence_present()` gate at `design_terminal.py:576` with a check that covers escalation-success generally (e.g. reuse `escalation_evidence_present()`, which is already known true at this point in the escalation-success branch) so the retry path isn't silently skipped for non-panel escalations.
- When `write_fallback_chat("compose-status-missing")` fires, preserve (or copy into a durable location) the diagnostic files it tells the operator to inspect, rather than letting Step 6 delete `$DESIGN_TMPDIR` out from under that instruction on an otherwise-successful, cleanup-eligible run.

## Open questions

- Which of the four silent-return branches in `file_tier_a_after_compose` actually fired for this specific run? Not determined — the diagnostic env/log files were already cleaned up by Step 6 before this was investigated.
- Is this reproducible reliably, or environment/timing-dependent (e.g. does it depend on `dedup_tier_a_report`'s deeper cross-repo dedup logic past `python/larch/state/_report.py:757`, which was not fully traced)?

## Test plan
(no test plan section in plan-file)
