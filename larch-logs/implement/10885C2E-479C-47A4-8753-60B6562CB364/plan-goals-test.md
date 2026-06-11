## Goal
Implement issue #4024: [IMPLEMENTING] [BUG] (URGENT) progress report stale step: marks lost when entry fences skipped\n\n[BUG] (URGENT) progress report stale step: marks lost when entry fences skipped.

## Implementation Plan
[BUG] (URGENT) progress report stale step: marks lost when entry fences skipped

## Context

The typed `p` / `progress` report (UserPromptSubmit hook `scripts/hook-progress-report.sh` invoking `python/cli.py progress report`) reported the wrong step in two live runs:

1. **/design run** (larch2 clone, session `claude-design-larch2-t4332vcf`): the orchestrator printed the `🔶 /design 3: plan review` breadcrumb and had `run-step3-review.sh` running in background for 27m (vote artifacts such as `codex-vote-output.txt.events.jsonl` landing in `DESIGN_TMPDIR`), yet `p` reported `design Step 2b — plan — started 21m ago`.
2. **/implement run** (larch1 clone, session `claude-implement-larch1-89g515rg`): the orchestrator was 1.5m into the Step 5 review loop (`run-step5-review.sh` launched, `round-1/` reviewer artifacts already appearing), yet `p` reported `Step 4 — commit implementation — started 6m ago`.

In both cases the report's `last artifact:` line was fresh and correct while the step line was stale. That incongruity is the fingerprint of the failure below.

## Root cause

`python/progress_report.py` derives the step label from the **latest `mark` row in `$TMPDIR/timing-ledger.tsv`** (`_latest_timing_mark`, consumed by `_render_implement` and `_render_design`). Those marks have **single writers that live inside step-entry wrapper fences**:

- design "Step 3 — plan review" mark: written only by `design-step3-entry-state.sh` (called from `design-step3-entry.sh`). Neither `design-step3-state.sh` nor `run-step3-review.sh` writes any mark.
- implement "Step 5 — code review" round-1 mark: written only by `skills/implement/scripts/step-5-entry.sh` (`timing telemetry-mark`). `scripts/run-step5-review.sh` writes its own mark **only when `STEP5_MODE == loop && STARTING_ROUND > 1`** (the resume case), precisely to avoid double-marking round 1.

In both failing transcripts the orchestrator improvised the step entry instead of running the documented wrapper (likely after mid-run context compaction; inference). The design session ran a raw `source` probe, then called the internal helpers `design-step3-state.sh` and `run-step3-review.sh` directly, twice with an invented `--session-env-path` flag (both rejected with usage errors, rc=2), and never ran `design-step3-entry.sh`. The implement session skipped the mandated `step-5-entry.sh` fence and launched `run-step5-review.sh` directly (in background, despite the foreground-only directive). Result in both: no mark for the running step, so every subsequent `p` report shows the previous step until some later wrapper happens to write a mark.

Secondary damage: the rich phase renderings are gated on the step label. `_render_design_plan_review` (round number, reviewers returned, elapsed) fires only when the label matches "Step 3 — plan review", and `_render_step5` only when the label contains "Step 5". A stale label silently downgrades the report to the generic one-liner even while round artifacts are demonstrably fresh.

Related history: #3914/#3916 fixed the run-discovery pointer layer (resume refresh, hook timeout). This bug is in the step-label layer; run discovery worked correctly in both transcripts.

## Prescriptive fix

Three changes plus tests; the normal-path ledger stays byte-identical.

1. **Add a guarded mark mode to the timing CLI.** In `python/timing.py`, extend `timing mark` with an `--if-latest-differs` flag (or sibling subcommand): read the ledger's latest `mark` row first and append only when its label differs from the requested label. Plain `timing mark` semantics stay unchanged for existing callers. Wire through `python/cli.py`.
2. **Self-marking launchers (belt and suspenders).**
   - `scripts/run-step5-review.sh`: replace the `STEP5_MODE == loop && STARTING_ROUND > 1` conditional mark with one unconditional guarded write before the `review-and-fix.sh` dispatch: `LARCH_TIMING_SKILL=implement python3 "$PLUGIN_ROOT/python/cli.py" timing mark --if-latest-differs "Step 5 — code review" || true`. Effects: normal round-1 path skips (label already written by `step-5-entry.sh`); skipped-entry path now writes the missing mark; loop resume still writes (latest label at resume is `Step 5 — review handoff` from `step-5-resume.sh`, which differs), preserving current resume rows.
   - `skills/design/scripts/run-step3-review.sh`: add the same guarded write at the top: `LARCH_TIMING_SKILL=design python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" timing mark --if-latest-differs "design Step 3 — plan review" || true`. Normal path skips (mark already written by `design-step3-entry-state.sh`); improvised path writes it. Note: on auto-continuation entries the latest label is `design Step 3 — auto-continuation entry`, so the guarded write fires and the visible label becomes plan review at loop start; that is more accurate for the operator and acceptable for the timing report.
3. **Staleness fallback in the reporter (defense in depth).** In `python/progress_report.py`: in `_render_implement`, also attempt `_render_step5` when the current `round-N` dir (per `_current_round_dir`) has `round-start-s` or artifacts newer than the latest mark timestamp, even when the label does not contain "Step 5"; in `_render_design`, the same for `plan-review/round-N` and `_render_design_plan_review`. When the fallback wins over a stale label, append one line: `note: step marks stale; phase inferred from round artifacts`. Keep the existing label-driven paths first so behavior is unchanged when marks are healthy.
4. **Tests.**
   - `python/test_timing.py`: `--if-latest-differs` appends on differing label, skips on identical label, appends on empty ledger.
   - `scripts/test-run-step5-review.sh`: extend the existing mark assertion with a round-1 skipped-entry case (no prior "Step 5 — code review" mark; assert the launcher writes it) and a no-duplicate case (prior mark present; assert single row).
   - `skills/design/scripts/test-run-step3-review.sh`: same two cases for the design label.
   - `python/test_progress_report.py`: stale-label scenarios for both skills; assert the rich phase rendering and the staleness note fire when round artifacts are newer than the last mark.

## Acceptance

- With the entry wrappers deliberately skipped and the review launchers invoked directly, `p` reports `Step 5 — code review` / `design Step 3 — plan review` with the rich round rendering.
- With the documented wrapper path, `timing-ledger.tsv` contents are unchanged from today (no duplicate mark rows).
- `make lint`, `make py-test`, and the extended harnesses pass.


## Test plan
(no test plan section in plan-file)
