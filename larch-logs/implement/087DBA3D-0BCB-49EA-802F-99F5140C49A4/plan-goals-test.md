## Goal
Implement issue #5646: [IMPLEMENTING] [BUG] [ship-pr-ci] merged runs are recorded as bailed/partial in committed logs.

## Implementation Plan
## Summary

`/implement` runs that successfully create AND merge their PR into `main` are recorded in their own committed run log as `Outcome: bailed` (`final-summary.md`) and `status: partial` (`manifest.json`), and never upsert an implement `larch:final-summary` comment on the tracking issue. The merge outcome exists **only in git history**. The committed run log — documented as the single source of truth — misreports successful merges as failures.

This is the concrete form of the operator-reported "ship-pr fails to notice successful CI completion." One of four related `[ship-pr-ci]` defects.

## Original report

Operator observed (live) that ship-pr seemed not to register successful CI completion / merge. A run-log audit cross-checked committed run outcomes against live GitHub state and found merged PRs whose runs self-report `bailed`.

## Reproduction scenario

1. Run `/implement --merge` on an issue and let it merge cleanly.
2. After merge, read `larch-logs/implement/<RUN_ID>/final-summary.md` (the `- **Outcome**:` line) and `manifest.json` (`status`), and the tracking issue's `larch:final-summary` comment.

Observed: `Outcome: bailed`, `status: partial`, and the `larch:final-summary` comment reflects the `/design` run (or is absent), not the implement merge.

## Expected behavior

The committed `final-summary.md` outcome reflects the terminal state (or at minimum an unambiguous in-progress label, not a failure word); `manifest.status` is not a failure-looking value for a merged run; and the implement `larch:final-summary` comment is upserted with the merged PR number/URL.

## Observed behavior

- `final-summary.md`: `- **Outcome**: bailed` for runs that merged.
- `manifest.json`: `status: partial`; `steps_ran` claims `step8`/`step9a1`; `stalled_at_step: null`.
- Tracking issue `larch:final-summary`: shows the `/design` run, or is absent — not the implement merge.

## Root cause analysis

Committed `final-summary.md` / `manifest.json` are **pre-terminal snapshots** (the in-progress manifest is documented in `docs/run-logs.md`: the post-merge `done` update lands in `$IMPLEMENT_TMPDIR` after the last log-commit window). Two candidate mechanisms, not yet disambiguated (needs the `[ship-pr-ci]` observability fix to confirm — the ship phase has no committed trail today):

- **B1 (favored):** the pre-PR / CI-retry log commit renders the outcome as `bailed`/`stalled` (a failure word, not an in-progress label) and is never refreshed in-tree after the post-merge terminal update; the implement `larch:final-summary` upsert (docs say API-only post-merge) does not occur. Census corroboration: `stalled`/`bailed` reads as a finalizer label for "run-log committed while the agent is still mid-flight" — 8 of 11 `stalled` runs were actively committing CI fixes / resolving conflicts in their last committed turn.
- **B2 (alternative):** the orchestrator turn genuinely ended `bailed` and the PR merged via the driver / a detached admin-merge path outside the recorded outcome.

## Evidence

- Verified: PR #5625 (run FFE6049C) and PR #5627 (run 79778D9A) both MERGED 2026-06-27; both runs' `final-summary.md` say `Outcome: bailed`; each run's log dir was introduced by its own merge commit (`ba369f129 "Fixes #5604: ... (#5625)"`; `499e2555a "Fixes #5606: ... (#5627)"`).
- #5604 `larch:final-summary` comment = `## /design run ... — approved` (created 07:28); no implement final-summary comment exists despite PR #5625 merging at 08:54.
- Census (60 newest runs): `final-summary` Outcome = `bailed` 48 / `stalled` 11 / none 1; `manifest.status` = `partial` 57 / `in-progress` 2 / `done` 1; `stalled_at_step` = `null` in ALL 60; `steps_ran` claims `step8` even where the transcript truncated at Step 7a (a declared field, not an execution record).

## Affected files

- `python/larch/implement/ship.py` — terminal-state write + final-summary write timing (`_write_terminal_state`, `_publish_post_pr_terminal_snapshot`, the postmerge phase).
- `python/cli.py render run-summary` / `final-report write` — outcome rendering and the `larch:final-summary` upsert.
- `python/larch/report/run_logs.py` — committed snapshot timing.
- `docs/run-logs.md` — documents the in-progress manifest; the `bailed` final-summary outcome is the surprising deviation.
- Downstream consumers that read outcome/status: `audit-runs`, `report-tokens`, `fluff-analysis`.

## Suggested fix(es)

- Render the committed pre-terminal `final-summary.md` with an unambiguous non-failure label (e.g. `shipping` / `in-progress`), never `bailed`, when the run is still progressing through ship.
- Ensure the implement `larch:final-summary` comment is upserted post-merge (API-only) so the tracking issue reflects the merged PR.
- Populate `stalled_at_step` and make `steps_ran` reflect actual execution; or document clearly that committed outcome is provisional and git / the issue comment is authoritative.

## Open questions

- B1 vs B2: does the orchestrator turn genuinely end `bailed`, or is the committed artifact a frozen pre-terminal snapshot of a run that went on to merge? Disambiguate once the ship phase has committed observability.
- Is the post-merge implement `larch:final-summary` upsert attempted-and-failing, or never attempted?

## Test plan
(no test plan section in plan-file)
