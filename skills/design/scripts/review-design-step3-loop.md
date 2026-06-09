# review-design-step3-loop.sh

**Consumer**: `skills/design/scripts/run-step3-review.sh --mode loop`.

## Purpose

Runs the `/design` Step 3 multi-round plan-review loop inside one Bash process. It is sourced by `run-step3-review.sh` after the shared single-round function is defined, then exposes `run_design_step3_loop()`.

## Contract

The loop emits a final `STEP3_REVIEW_LOOP_STATUS` envelope and exits only on:

- terminal statuses: `complete`, `cap-hit`, `panel-failed`, `tally-error`, `degraded-empty-collector`, `postplan-failed`
- main-agent/operator bail-outs: `main-agent-vote-required`, `main-agent-apply-required`, `per-round-approval-required`, `postplan-operator-required`

Carry-through KVs include `ROUNDS_COMPLETED`, `FINAL_ROUND_NUM`, `ACCEPTED_COUNT`, `DEGRADED_PANEL`, optional `SCOPE_ANCHOR_FILE`, `PLAN_REVIEW_CONTINUE_REASON`, `POSTPLAN_RC`, and `DEDUP_RC`.

## Resume phases

For round `N`, `$DESIGN_TMPDIR/.step3-round-N.phase` records one of:

- `awaiting-apply` — review/tally has completed; accepted findings have not been applied.
- `awaiting-revise` — the reviser is running or was interrupted before a confirmed apply.
- `awaiting-post-apply` — the reviser applied findings; mechanical dedup/postplan must settle.
- `awaiting-postplan-operator` — in-loop postplan returned rc 10/12/13/14; prompt-side operator handling is required. Non-plan-changing Override/Continue writes `$DESIGN_TMPDIR/.postplan-operator-continue-N` before resume; the loop consumes the marker, runs HARD snapshots when applicable, and promotes to `awaiting-continuation`.
- `awaiting-continuation` — apply/postplan is settled; only `plan-review-continuation.sh` runs.

Every bail-out resumes with:

```bash
run-step3-review.sh --design-tmpdir "$DESIGN_TMPDIR" --mode loop --starting-round "$N"
```

`run-step3-review.sh` validates that a resume for an already consumed round has phase evidence and rejects starts beyond the next unconsumed round.

## Apply pipeline

The happy path uses `revise-plan-with-waterfall.sh --patch-format file-replacement`, then `gate-b-dedup-plan.sh --snapshot-trailers` and `--dedup`, then `design-postplan-emit.sh --with-plan-size`. A loop-owned `plan-pre-apply-round-N.txt` snapshot is the restore source for dedup failure. The `.gate-b-postapply-ready-N` marker is written only after dedup succeeds.

## Harness

`skills/design/scripts/test-review-design-step3-loop.sh` covers the offline envelope, bail-out, phase-resume, postplan-routing, and dedup-restore seams. `skills/design/scripts/test-run-step3-review.sh` covers launcher argv and `--starting-round` validation.
