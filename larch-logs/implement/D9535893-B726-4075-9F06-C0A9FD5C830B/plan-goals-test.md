## Goal
Implement issue #6531: [IMPLEMENTING] Review and plan-review engines emit bgjob merge-result KVs (#6524 chunk 2/11).

## Implementation Plan
## Plan

## Context

Parent: #6524 "Migrate remaining run_in_background call sites to bgjob start/wait (part 2)" — chunk 2/11.

Scope: make the long-running review and plan-review Python engines emit bgjob-mergeable completion KVs so the wrapper chunks can pass their outputs through `bgjob start --merge-result-env`; audit these loops for task-notification/background assumptions.

Dependencies: none — this chunk is independent and can merge in parallel with chunk 1. The /design Step 3 wrapper chunk and the /implement Step 5 wrapper chunk consume the KV emission added here and must merge after this chunk.

The parent's vetted plan was split into 11 self-contained chunk issues because a single /implement run could not complete all ~74 firm files. Nothing from the parent's failed run merged; implement this chunk from scratch on current main. Do not modify files outside this chunk's scope headings; sibling chunk issues own them (in particular: do not touch the shell wrappers, skill prose, or `plan_review_normalize.py` — those migrate in later chunks).

## Approach (global invariants inherited from #6524)

1. Keep `skills/shared/bgjob-wait.md` as the normative wait contract.
2. Move step result KVs into a merge env file passed through `bgjob start --merge-result-env`; the engine writes completion KVs into the merge input, and the daemon merges them into `$TMPDIR/bgjob/<step>.result.env`.
3. Treat `$TMPDIR/bgjob/<step>.result.env` as the completion source of truth after `bgjob wait` returns `DONE`.
4. Gate normal continuation on both `BGJOB_RC=0` and required step KVs present in the final `DONE` stdout and/or the bgjob result env; a result env that omits a required legacy KV causes false success or false stall.
5. Keep legacy hooks and marker helpers functional but inert until #6516 deletes them.
6. This chunk changes engine output surfaces only; it must remain backward compatible with the current (pre-bgjob) wrappers that still read legacy result envs.

## Files to modify/create

### UPDATED: python/larch/review/plan_review.py
- Ensure plan-review loop outputs remain merge-result-env compatible.
- Write completion KVs into the merge input consumed by `design-step3-review`.
- Chunk note: the current merge input is `$DESIGN_TMPDIR/.step3-review-result.env`; the Step 3 wrapper chunk will truncate it before `bgjob start` and pass it as `--merge-result-env`. Keep every existing loop-envelope KV (e.g. `STEP3_REVIEW_LOOP_STATUS`) present and unchanged so pre-migration readers keep working.

### UPDATED: python/larch/review/review_and_fix.py
- Audit standalone `/review --diff` and nested Step 5 paths for background assumptions.
- Ensure long loops produce mergeable result KVs for bgjob.
- Chunk note: keep the current Step 5 stdout/result contract intact; the Step 5 wrapper chunk rebinds consumption to `$IMPLEMENT_TMPDIR/bgjob/<step>.result.env`.

### UPDATED: python/larch/review/review_pipeline.py
- Ensure nested and standalone review loops do not depend on task-notification output.

### UPDATED: python/tests/review/test_plan_review.py
- Chunk-scoped: add coverage that the plan-review loop writes its completion KVs to the merge input file (mergeable KV grammar, one `KEY=value` per line, no banners).
- Do not add the `_step3_normalize_read_result_env` / `--read-result-env` bgjob-path pins here; the /design Step 3 chunk owns those together with `plan_review_normalize.py`.

### UPDATED: python/tests/review/test_review_and_fix.py
- Chunk-scoped: add coverage that long review loops produce mergeable result KVs for bgjob.
- Do not replace the Step 5 detached-wrapper expectations here; the /implement Step 5 chunk owns that swap together with the wrapper migration.

## Edge cases

- A result env that omits a required legacy KV causes false success or false stall; KV emission must be a superset of the current envelope, never a subset.
- Engines must write KVs unconditionally on loop completion (success and failure exits both emit status KVs) so `DONE` routing has data even on failure branches.
- Emission must not add prose or banners to KV streams consumed by wrappers or harness parsers.

## Failure modes

- A result env omits a required legacy KV, causing false success or false stall in a later wrapper chunk.
- KV emission lands only on the success path, so failure routing loses its envelope after migration.
- Engine changes break the current (pre-bgjob) wrappers before the wrapper chunks merge — backward compatibility is mandatory.

## Testing strategy

1. `python3 -m pytest python/tests/review/test_plan_review.py python/tests/review/test_review_and_fix.py -q`
2. Final validation: `make py-lint`, `make py-test`.

## Implementation notes

- Prefer Python helpers behind `python3 python/cli.py` for non-trivial parsing and result-env writes.
- Use `larch.io` helpers for result env writes and reads where practical.
- Use config constants for bgjob status and rc keys.
- Every existing consumer of these engines (current wrappers, `/review --diff`, nested Step 5) must keep working unchanged until the wrapper chunks migrate them.

## Acceptance

1. The plan-review loop writes completion KVs into the merge input consumed by `design-step3-review`, covering the full current loop envelope (pinned in `python/tests/review/test_plan_review.py`).
2. `/review --diff` standalone and nested Step 5 review loops produce mergeable result KVs and do not depend on task-notification output (pinned in `python/tests/review/test_review_and_fix.py`).
3. No existing loop-envelope KV is renamed or dropped; current wrappers and harnesses pass unmodified.
4. `make py-lint` and `make py-test` pass.

diff_added: 160
diff_deleted: 40
mechanical_churn: true
diff_lines: 200

## Test plan
(no test plan section in plan-file)
