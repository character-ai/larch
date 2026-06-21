## Proposed Design Outline

### Goals
- Thin `design-step3-review.sh`: move the post-loop status normalization, result-env synthesis, and KV envelope emission into a new `python/cli.py plan-review` verb.
- Preserve every Step 3 sentinel, status, stdout, and exit-code contract byte-identically.
- Shrink the wrapper materially while keeping shell job control.

### Non-goals
- Not a full migration; keep the `.sh` process-group launcher.
- No change to plan-review loop behavior, escalation semantics, or argv/resume-state validation.
- No new Step 3 status values or features.

### Approach sketch
- Add a verb in `python/plan_review.py` (dispatched via `python/cli.py plan-review <verb>`) that ingests the result-env path, plan-review stdout, and loop rc; emits the canonical `STEP3_REVIEW_LOOP_STATUS` / `LOOP_STATUS` / KV envelope; writes synthesized result-env + terminal-persist markers; and records escalation evidence.
- Fold the `--read-result-env` recovery branch into the same verb (a read mode) emitting the exact `READ_RESULT_ENV_STATUS` + 7-KV grammar.
- Wrapper keeps argv parse, resume-state validation, pause check, `set -m` setup, background loop launch, `kill -- -$pid` teardown, and EXIT-trap sentinel guarantees; the back half becomes verb calls.

### Surfaces in scope
- `skills/design/scripts/design-step3-review.sh` and its `.md` sibling
- `python/plan_review.py`, `python/cli.py` dispatch
- `python/test_plan_review.py`, `skills/design/scripts/test-design-step3-review.sh`

### Open questions
- None. Extraction boundary (full back half) and `--read-result-env` placement (fold into verb) were resolved in Step 1c.
