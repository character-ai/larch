# test-step-8-assessment.sh

Offline harness for `step-8-assessment.sh`. Uses a fake plugin root with stubbed
Piece 2 (`normalize_kinds` / `validate_materialization`), bgjob registry,
`python/cli.py bgjob start|wait`, and `architectural-assessment run` responses.
No real assessment model, daemon, or repository mutation occurs.

## Coverage

- Fresh start: kind order normalization, covered fingerprint, plugin
  `PYTHONPATH`, stale merge clear, single `implement-step8-assessment` start with
  `--budget-s 5700` and wrapper-child argv (`bash …/step-8-assessment.sh
  --bgjob-child`); assessment CLI only from child mode. The adapter has no
  vendor availability probe or lane selector.
- Static budget pin (`BUDGET_S=5700`)
- Live rejoin: zero-duration probe, `WAIT` → blocking wait, no duplicate start;
  attempt-1 timeout after rejoin routes to in-invocation attempt 2
- Completed rejoin for `complete` (`BGJOB_RC=0`) and terminal `fail-closed`
  (non-zero / `timeout`) without attempt 3
- Deterministic skip / authored success states under Piece 2 success contract
- Stale rejection: changed kinds or fingerprint clears and relaunches; symlink /
  non-regular path refusal
- Active-stale live row: exit 2 + `ASSESSMENT_ERROR=active-stale-identity-mismatch`
- Timeout and invalid child-envelope retries with terminal `fail-closed` after
  attempt 2; adapter retries are distinct from Piece 2 model-lane attempts; no
  foreground inline Piece 2 call
- Required KVs and daemon-reserved merge-key refusal
- Fingerprint grammar: shared helper digest matches harness preimage
- Bash portability guards (no associative arrays / namerefs / `mapfile`)

## Edit-in-sync

Keep aligned with `step-8-assessment.sh` and `step-8-assessment.md`.
