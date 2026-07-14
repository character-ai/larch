## Goal
Implement issue #7208: [IMPLEMENTING] bug-treadmill [FEATURE] 6972.3: /analyze-bugs sweep stage wiring, report merge, and fail-closed state commit.

## Implementation Plan
## Plan

## Approach

Run sweep preparation and executable agent-ingestion fences after prefetch but before the existing ledger and deep stages. The existing Stage 3 report remains the sole final rendering entrypoint, merging the validated sweep artifact with legacy results only after all enabled analysis stages complete. It creates or extends the combined follow-up body for sweep-only survivors, then writes sweep state last. Mark capped reports as incomplete coverage rather than treating skipped commits as permanently omitted.

## Files to modify/create

### UPDATED: .claude/skills/analyze-bugs/SKILL.md

- Add `--sweep` and `--sweep-max N` to the argument hint and flag allowlist.
- Parse sweep controls before prefetch, forward only legacy prefetch arguments to the existing prefetch command, and reject `--sweep-max` without `--sweep`.
- Default `--sweep-max` to `20`; reject non-positive or invalid values before Task dispatch.
- Keep the existing clean, synced `main` preflight.
- After Stage 0 prefetch establishes the active run directory and before existing ledger and deep stages, add sweep stages:
  - S0 invokes `python3 python/cli.py analyze-bugs sweep prepare` in a shell fence and requires its non-zero exit to abort before any Task dispatch.
  - S1 dispatches one finder per selected bundle, captures each agent's JSONL-only response into the fixed `RUN_DIR/sweep-finder.jsonl`, then invokes `python3 python/cli.py analyze-bugs sweep ingest-finder` in a shell fence.
  - S1 requires successful Python ingest and exact accepted coverage before refuter dispatch or any legacy ledger/deep stage; it reads `REFUTER_QUEUE_PATH` and `REFUTER_QUEUE_COUNT` only from the ingest command's KVs.
  - S2 dispatches one refuter per row in `REFUTER_QUEUE_PATH`, captures JSONL-only responses into the fixed `RUN_DIR/sweep-refuter.jsonl`, then invokes `python3 python/cli.py analyze-bugs sweep ingest-refuter` in a shell fence.
  - S2 requires successful Python ingest and exact queue-key coverage before continuing to legacy stages.
  - For zero selected merges, skip finder dispatch and finder parsing but still run the successful prepare and finder-ingest fences that create an empty queue.
  - For a zero-length refuter queue, skip refuter dispatch and raw refuter capture but still run the successful refuter-ingest fence that writes the zero-candidate validated artifact.
- Continue with the existing Stage 1 ledger and Stage 2 deep work. Keep the existing Stage 3 report as the single final rendering and state-commit step that merges legacy and sweep results.
- Stop without changing sweep state after Task failure, malformed JSONL, rejected rows, missing coverage, stale-tip identity failure, or final report failure.
- Print the selected count, skipped count, pending-frontier count, incomplete-coverage status when capped, and sweep cost estimate.
- Keep the existing approval prompt. On approval, invoke `/issue` once with the combined follow-up body and do not pass `--no-dedup`.
- Document `sweep-state.json` beside `ledger.jsonl`, its pending-SHA frontier, and the first-run 48-hour window.
- Set expectations clearly: static sweep can find contract breaks, wrong field or key names, and logic errors. It cannot establish that main is bug-free or detect timing failures, vendor CLI drift, GitHub-state failures, or other runtime-only defects.

### UPDATED: python/larch/issue/analyze_bugs.py

- Extend the existing report path to consume a validated sweep-result artifact when present.
  - Preserve the existing Stage 3 report as the only final render after ledger and deep stages complete.
  - Verify the artifact's pinned tip and selected-manifest identity before merging it with legacy results.
  - Add a `Sweep candidates` table with merge, file, symbol, severity, confidence, and description.
  - Print selected count, skipped count, pending-frontier count, and an explicit incomplete-coverage notice when pending work remains.
  - Print a distinct `ANALYZE_BUGS_SWEEP_COST_ESTIMATE=...` line based on bounded finder and refuter inputs using the existing Sonnet rate lookup.
  - Add surviving candidates to the existing `follow-up-issue.md`.
  - When sweep survivors exist but legacy follow-ups are empty, create `follow-up-issue.md` with a sweep section and emit its path in report output.
  - Preserve the non-sweep report path and do not create sweep state or sweep-only follow-up output without a validated sweep artifact.
  - Write `sweep-state.json` last, only after the final report, follow-up body, and other sweep artifacts complete successfully.
  - Advance the discovery watermark to the pinned `origin/main` tip and persist all unselected eligible SHAs as `pending_shas`, so capped work is retried rather than discarded.

### UPDATED: python/tests/issue/test_analyze_bugs.py

- Prove state remains absent or unchanged after finder failure, refuter failure, and report generation failure end to end.
- Prove a completed final report advances the discovery watermark and writes the pending frontier only after report artifacts exist.
- Test resumable capped coverage end to end: a capped run persists skipped eligible SHAs, a later run selects pending SHAs before newly enumerated lower-priority work, and no eligible skipped SHA is silently lost when the discovery watermark advances.
- Test final Stage 3 report output for `Sweep candidates`, the sweep cost line, skipped-count logging, incomplete coverage, and inclusion in the combined follow-up body.
- Test sweep-only survivors create `follow-up-issue.md`, emit its path, and remain approval-gated with dedup enabled.
- Verify sweep-only, sweep-plus-legacy, capped-resumption, and legacy report fixtures.
- Test that sweep flags are not forwarded to prefetch.

## Edge cases

- A first sweep with no commits in 48 hours completes with zero findings, does not require finder or refuter raw result files, and records the pinned tip with an empty pending frontier.
- A later sweep with only excluded commits completes and advances the discovery watermark with no pending work.
- A capped sweep records every unselected eligible SHA, reports incomplete coverage, and retries that frontier on later sweeps.
- Sweep-only surviving candidates still produce a follow-up body for the existing approval-gated filing path.
- Existing non-sweep runs neither read nor write sweep state.

## Failure modes

- Report or follow-up-body failure leaves the prior sweep marker and pending frontier intact.
- `/issue` filing failure does not rewrite sweep analysis state because analysis completed before the separately approval-gated mutation.
- A stale pinned tip, state identity mismatch, or invalid sweep artifact aborts rather than mixing evidence from different main revisions.
- Task failure, malformed JSONL, rejected rows, or missing coverage stop the run without changing sweep state.

## Testing strategy

- Run `python3 -m pytest python/tests/issue/test_analyze_bugs.py -q`.
- Run the changed-file Python lint and type checks through `make py-lint`.
- Verify sweep-only, sweep-plus-legacy, capped-resumption, and legacy report fixtures.
- Verify the acceptance history fixture: a flush commit, a release commit, and two real merges, where only the real merges are swept.

## Acceptance

- Run `python3 -m pytest python/tests/issue/test_analyze_bugs.py -q`.
- Run the changed-file Python lint and type checks through `make py-lint`.
- Verify sweep-only, sweep-plus-legacy, capped-resumption, and legacy report fixtures.
- On the acceptance history fixture, only the real merges are swept; skipped-count logging appears when merges exceed `--sweep-max`.
- `.claude/skills/analyze-bugs/SKILL.md` documents the flag, the state file, and the expectation-setting paragraph.

diff_added: 230
diff_deleted: 15
mechanical_churn: false
diff_lines: 245

## Test plan
(no test plan section in plan-file)
