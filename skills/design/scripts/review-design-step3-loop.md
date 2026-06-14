# review-design-step3-loop.sh

**Consumer**: `skills/design/scripts/run-step3-review.sh --mode loop`.

## Purpose

Runs the `/design` Step 3 multi-round plan-review loop inside one Bash process. It is sourced by `run-step3-review.sh` after the shared single-round function is defined, then exposes `run_design_step3_loop()`.

## Contract

The loop emits a final `STEP3_REVIEW_LOOP_STATUS` envelope and exits only on:

- terminal statuses: `complete`, `cap-hit`, `panel-failed`, `tally-error`, `degraded-empty-collector`, `postplan-failed`
- main-agent/operator bail-outs: `main-agent-vote-required`, `main-agent-apply-required`, `per-round-approval-required`, `postplan-operator-required`

Carry-through KVs include `ROUNDS_COMPLETED`, `FINAL_ROUND_NUM`, `ACCEPTED_COUNT`, `DEGRADED_PANEL`, optional `SCOPE_ANCHOR_FILE`, `REASON`, `PLAN_REVIEW_CONTINUE_REASON`, `POSTPLAN_RC`, and `DEDUP_RC`. Clean terminal rounds write `REASON=` empty in the persisted envelope.

## Envelope KV safety

Emitted and durable loop-envelope KV values must be single-line. `PLAN_REVIEW_CONTINUE_REASON` strips CR/LF before FD3 emission and result-env persistence. Merged `PLAN_REVIEW_CONTINUE_REASON` values from an existing `.step3-review-result.env` strip CR/LF before being preserved; sanitized-empty merged values are omitted (no `PLAN_REVIEW_CONTINUE_REASON=` line). `SCOPE_ANCHOR_FILE` is omitted when it contains CR/LF; invalid multiline scope anchors are not repaired by stripping characters. When `phase_driver_write_result_env` fails, the loop emits a visible human warning via `emit` and a `WARN=` KV via `emit_kv` instead of silently swallowing the failure with `|| true`. It also records a best-effort `Tool Failures` entry in `execution-issues.md` when diagnostic allocation and `python/cli.py run-log append-failure` are available.

Persist failures do not emit replacement `STEP3_REVIEW_LOOP_STATUS` or `LOOP_STATUS` KVs. `step3_loop_emit_envelope` already emitted the operational status before persistence. `design-step3-review.sh` owns the production handoff fallback when no usable Step 3 status reaches the wrapper.

## Resume phases

For round `N`, `$DESIGN_TMPDIR/.step3-round-N.phase` records one of:

- `awaiting-apply` — review/tally has completed; accepted findings have not been applied.
- `awaiting-revise` — the reviser is running or was interrupted before a confirmed apply.
- `awaiting-post-apply` — the reviser applied findings; mechanical dedup/postplan must settle.
- `awaiting-postplan-operator` — in-loop postplan returned rc 10/13/14; prompt-side operator handling is required. Non-plan-changing Override/Continue resumes through `design-step3-review.sh --starting-round N --postplan-operator-continue`; the wrapper writes the marker before pause-save, and the loop consumes it once, promoting to `awaiting-continuation`. **rc=12 (plan-size trigger) is now handled inline as warn-and-continue**, promoting directly to `awaiting-continuation` without surfacing `postplan-operator-required`.
- `awaiting-continuation` — apply/postplan is settled; only `plan-review-continuation.sh` runs.

Prompt-side bail-outs resume through the launcher-owned wrapper that writes validated resume state before pause-save when a state flag is present:

```bash
design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND" --phase awaiting-continuation
design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND" --phase awaiting-apply
design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND" --phase awaiting-post-apply
design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND" --findings-file "<path>"
design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND" --postplan-operator-continue
```

Calls without resume-state flags preserve first-entry pause behavior. Calls with resume-state flags also resume the review loop after state write and pause-save. Callers must not split a migrated phase, findings env, or postplan continue write and the following review resume into two wrapper calls. The wrapper forwards to `run-step3-review.sh --mode loop --starting-round <round>`. `run-step3-review.sh` validates that a resume for an already consumed round has phase evidence and rejects starts beyond the next unconsumed round.

## Apply pipeline

The happy path uses `python/cli.py plan revise-waterfall --patch-format file-replacement`, then `gate-b-dedup-plan.sh --snapshot-trailers` and `--dedup`, then `design-postplan-emit.sh --with-plan-size`. A loop-owned `plan-pre-apply-round-N.txt` snapshot is the restore source for dedup failure. The `.gate-b-postapply-ready-N` marker is written only after dedup succeeds.

After a successful revise, the loop calls `write-design-round-meta.sh --round-dir round-N` to refresh `round-N/round-meta.json` with `revise.status` and `revise.tier` from `round-N/revise/revise.env`. The initial write (by `plan-review-loop.sh` at round end) contains `null` for both fields because revise has not yet run; this second call populates them so the Review Phase Detail table can show which tier was used each round.

## Harness

`skills/design/scripts/test-review-design-step3-loop.sh` covers the offline envelope, bail-out, phase-resume, postplan-routing, and dedup-restore seams. `skills/design/scripts/test-run-step3-review.sh` covers launcher argv and `--starting-round` validation.

## Report-gate evidence ownership

The Step 3 loop records escalation evidence for `main-agent-vote-required`, `main-agent-apply-required`, `postplan-operator-required`, `panel-failed`, `tally-error`, and `degraded-empty-collector`. `postplan-failed` stages terminal state as `failed-postplan`. Panel degradation statuses remain non-terminal and Step 2b.5 decompose-panel retry exhaustion is not handled here.
