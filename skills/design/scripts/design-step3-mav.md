# design-step3-mav.sh

## Purpose

`design-step3-mav.sh` owns the mechanical `/design` Step 3 MainAgent vote and re-tally flow. It keeps the prompt-side branch to one LLM judgment boundary: read the wrapper-rendered evidence and ballot, then write `voter-main-agent.txt`.

## Interface

```text
design-step3-mav.sh --phase pre|post --session-env-path PATH --claude-pid PID --plugin-root PATH
```

- `--phase pre` runs before the LLM reads the ballot.
- `--phase post` runs after the LLM writes `$DESIGN_TMPDIR/voter-main-agent.txt`.
- The wrapper sources the session env, requires a valid `DESIGN_TMPDIR`, and honors `.pause-requested` by `exec`ing `python/cli.py design pause-save` before any MAV work.

## Pre phase

The pre phase reads `.step3-plan-review-result.env` as the base and `.step3-review-result.env` as the authoritative source through `scripts/read-result-env.sh`. Session-env values remain fallback defaults, base (plan-review) values fill absent keys, and `.step3-review-result.env` (sourced second) wins when both files define the same key. Symlinked result-env files fail closed.

When `SCOPE_ANCHOR_FILE` is present, the wrapper renders it with `python/cli.py render scope-anchor --design-tmpdir "$DESIGN_TMPDIR"`. Every rendered evidence line is prefixed with `SCOPE_ANCHOR_EVIDENCE:` so anchor content cannot spoof trusted KVs. Render failures propagate.

Trusted machine KVs are emitted only inside this frame:

```text
DESIGN_STEP3_MAV_KV_BEGIN
BALLOT_PATH=...
STEP3_RESUME_ROUND=...
DESIGN_STEP3_MAV_KV_END
```

Prompt-side orchestration must parse only the final `DESIGN_STEP3_MAV_KV` frame and must abort the MAV branch when `BALLOT_PATH` is missing.

## Post phase

The post phase snapshots loop mode, artifact round, resume round, and `SCOPE_ANCHOR_FILE` before re-tally or env persistence. It runs:

```text
tally-plan-review.sh --ballot-file "$DESIGN_TMPDIR/ballot.txt" --design-tmpdir "$DESIGN_TMPDIR" --voter "MainAgent:$DESIGN_TMPDIR/voter-main-agent.txt" --findings-classification-out "$DESIGN_TMPDIR/plan-review/round-N/findings-classification.tsv"
```

Then it calls `persist-retally-step3-env.sh` for both `ok` and handled `tally-error`. The post phase appends the idempotent 0-judge warning under `Warnings`, records deferred round timing only after successful `ok`, and writes `.step3-round-N.phase` only for successful loop-mode re-tally. Zero accepted findings route to `awaiting-continuation`; accepted findings route to `awaiting-apply`; legacy single mode emits `PHASE=unchanged` and does not create a phase file.

## Output KVs

Post phase emits trusted KVs in the same `DESIGN_STEP3_MAV_KV` frame:

- `TALLY_PLAN_REVIEW_STATUS=ok|tally-error`
- `NEXT_ACTION=step3b-bypass` when re-tally fails
- `LOOP_STATUS=complete`
- `ACCEPTED_COUNT=N`
- `PHASE=awaiting-continuation|awaiting-apply|unchanged`
- `STEP3_RESUME_ROUND=N` when known

`TALLY_PLAN_REVIEW_STATUS=tally-error` is a handled result and exits `0`; prompt-side routing proceeds through the Gate B bypass path. Wrapper argv/configuration errors exit `2`.

## Harness

`test-design-step3-mav.sh` covers pause handling, safe result-env reads, pre-phase rendering, post-phase re-tally success and handled `tally-error`, loop/single routing, round precedence, and prose regression pins.

```bash
bash skills/design/scripts/test-design-step3-mav.sh
```

Wired through `make test-design-step3-mav`.
