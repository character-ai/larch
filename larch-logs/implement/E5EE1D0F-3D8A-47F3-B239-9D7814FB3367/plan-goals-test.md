## Goal
Implement issue #4301: [IMPLEMENTING] [OOS] /design Step 3 plan-review & log-publish drift + bugs — 7 items.

## Implementation Plan
## Approach

Make the smallest targeted changes across the approved surfaces.

- Replace retired basename references with current Python CLI commands.
- Wire clarify wrapper edits to the existing clarify harness.
- Prevent a second prompt-side Step 2b postplan fence after partial drafter success.
- Use the resume-aware round-start reader on Step 3 loop timing exits.
- Pin Step 3 wrapper teardown ordering with line-order assertions.
- Refresh `origin/<default>` before final log-publish idempotency logic.
- Add a squash-like final idempotency test where default already has the same run snapshot and the log branch is gone.

## Files to modify/create

### UPDATED: skills/design/scripts/lib-plan-optional-trailers.md

Update the two `check-plan-size.sh` references in the invalid `mechanical_churn` and `block_len` sections.

- Use `python/cli.py plan check-size`.
- Keep the awk contract text unchanged.
- Do not change thresholds or parser behavior.

### UPDATED: docs/workflow-lifecycle.md

Update the `/design` lifecycle paragraph.

- Replace `revise-plan-with-waterfall.sh` with `python/cli.py plan revise-waterfall`.
- Keep the rest of the workflow description intact.

### UPDATED: skills/design/scripts/test-trailer-awk.md

Update the `block_len` parenthetical.

- Replace `check-plan-size.sh` with `python/cli.py plan check-size`.
- Do not change fixture expectations.

### UPDATED: skills/design/scripts/test-design-postplan-emit.md

Update the `--with-plan-size` harness note.

- Replace the fake-tree `check-plan-size.sh` wording with the current `python/cli.py plan check-size` surface.
- Keep this as documentation-only drift cleanup.

### UPDATED: scripts/relevant-checks.sh

Add a direct relevant-check mapping for clarify surfaces.

- Match:
  - `skills/design/scripts/design-clarify.sh`
  - `skills/design/scripts/design-clarify.md`
  - `skills/design/scripts/test-design-clarify.sh`
  - `skills/design/scripts/test-design-clarify.md`
- Append `test-design-clarify` once.
- Place the arm near the other `skills/design/scripts/design-*` mappings.
- Do not add unrelated structure or publish targets.

### UPDATED: skills/design/SKILL.md

Harden the drafter-success missing-row fail-safe prose.

- Keep the existing rule that wrapper-owned `POSTPLAN_RC=` and `POSTPLAN_STATUS=` rows are authoritative.
- Before the retained terminal postplan fail-safe, check whether `$DESIGN_TMPDIR/.completed/step-2b.5` already exists.
- If `.completed/step-2b.5` exists and wrapper-owned rows are still missing, do not run a second prompt-side postplan fence.
- Fail closed with diagnostics instead of continuing without authoritative postplan rows.
- State that the retained fail-safe may run only when the drafter fence exited zero, rows are missing, and `.completed/step-2b.5` is absent.
- Rationale: `.completed/step-2b.5` is written only on a successful postplan rc=0 path; `.completed/step-2b` can be written by `--write-step2b-completion-only` mode without successful postplan rows.
- Do not change inline fallback, rc 10/12/13 routing, or pause routing.

### UPDATED: scripts/test-design-structure.sh

Strengthen structural coverage without rewriting the wrapper.

- Add a helper `assert_line_order_in_file FILE LABEL_A NEEDLE_A LABEL_B NEEDLE_B [START_AFTER]` that finds the first occurrence of each needle after `START_AFTER` (default 0) and asserts the first is before the second.
- Use that helper for normal-path ordering assertions for `skills/design/scripts/design-step3-review.sh`, anchoring all checks after `_plan_review_rc=$?` (line ~383) to avoid matching lines inside `_step3_review_cleanup()`:
  - `_plan_review_rc=$?` before `_step3_review_teardown_loop_group "$_loop_pid"`.
  - `_step3_review_teardown_loop_group "$_loop_pid"` before `_loop_pid=""`.
  - `_loop_pid=""` before the normal-path `trap - EXIT` (the clear that follows teardown, not the one inside the cleanup function).
- Add cleanup-path ordering assertions (no start anchor needed; cleanup function comes first):
  - `_step3_review_cleanup()` before its local `trap - EXIT`.
  - that cleanup `trap - EXIT` before `_step3_review_teardown_loop_group "$_loop_pid"` (inside cleanup body).
- Add a SKILL.md pin near the drafter fail-safe text for `.completed/step-2b.5`.
- Keep existing literal `contains` pins.

### UPDATED: skills/design/scripts/review-design-step3-loop.sh

Fix timing start semantics on resumed Step 3 phases.

- In the `panel-failed` / `tally-error` / `degraded-empty-collector` branch, change the timing start argument from local `round_start_s` to `$(step3_loop_read_round_start_s "$round_num" "$round_start_s")`.
- In the `awaiting-continuation` success path, make the same substitution.
- Leave the failure paths unchanged where they already use the resume-aware reader.
- Do not change loop status routing or phase writes.

### UPDATED: scripts/design-log-publish.sh

Refresh the default branch before the non-final idempotency check.

- The `REASON=final` path is already handled by `design_publish_rebuild_final_commit`, which calls `design_publish_refresh_default_ref` at line 592.
- The bug is in the non-final (`else`) path: add a call to `design_publish_refresh_default_ref` immediately before the `if [[ -z "$_porcelain" ]]` check (line ~1065). Use best-effort semantics (`|| true`) so a fetch failure does not abort the publish; it just risks missing an already-merged snapshot and creating an unnecessary PR.
- Do not change the final-path rebuild or add a redundant pre-worktree fetch.
- Do not add flags or new env vars.

### UPDATED: scripts/test-design-log-publish.sh

Add a final-mode squash/idempotency regression.

- Add a case near the final idempotency tests.
- Simulate production squash semantics by:
  1. Running `design-log-publish.sh` once (with `TEST_CLONE_ROOT` and `TEST_MERGE_BRANCH` set so the gh stub merges it into main), which seeds main with the byte-complete normalized publish tree including `manifest.json`.
  2. Deleting the remote log branch from the upstream bare repo after the first publish, so a second run sees no live `larch-log-design-<RUN_ID>` ref.
  3. Fetching the stale upstream by NOT pulling in the consumer clone, so `origin/main` is behind.
  4. Re-running `design-log-publish.sh` from the consumer clone with the same design tmpdir and same RUN_ID.
- Do NOT seed main by hand-pushing only partial artifacts (e.g. just `plan.txt`) — rebuild compares the full staged tree and will see a delta, causing an unnecessary PR.
- Assert:
  - `PUBLISH_OK=true`,
  - no `gh pr create` in the second run,
  - no `gh pr merge` in the second run,
  - the default-branch content remains intact after pull.
- Keep the existing differing-snapshot squash test that expects a new PR.

## Edge cases

- A stale local `origin/main` may miss an already-published final log. The early fetch fixes that before final idempotency checks.
- A drafter can complete postplan internally but lose wrapper rows. The SKILL.md change prevents a second postplan run and fails closed.
- Resumed Step 3 phases may have no local start time from the real round start. The reader falls back to local `round_start_s` when no durable `round-start-s` exists.
- Pause-mode publish must not use final idempotent success. Keep existing pause tests unchanged.

## Failure modes

- If `git fetch origin "$ORIGIN_DEFAULT:refs/remotes/origin/$ORIGIN_DEFAULT"` fails in final publish, return `PUBLISH_OK=false` before worktree push or PR creation.
- If drafter rows are missing and `.completed/step-2b` exists, stop for inspection rather than re-running postplan.
- If line-order assertions become brittle, prefer anchoring on existing unique snippets before adding broad parser logic.

## Testing strategy

Run focused checks first.

- `bash scripts/test-design-structure.sh`
- `bash skills/design/scripts/test-design-clarify.sh`
- `bash scripts/test-design-log-publish.sh`
- `bash skills/design/scripts/test-design-postplan-emit.sh`
- `bash skills/design/scripts/test-trailer-awk.sh` if available through the local harness entrypoint.
- `bash scripts/relevant-checks.sh` after all edits.

Also run grep checks.

- `grep -RIn "check-plan-size\\.sh\\|revise-plan-with-waterfall\\.sh" skills/design/scripts/lib-plan-optional-trailers.md docs/workflow-lifecycle.md skills/design/scripts/test-trailer-awk.md skills/design/scripts/test-design-postplan-emit.md`
- Expect no retired basename hits in those four files.

diff_added: 86
diff_deleted: 12
mechanical_churn: false
diff_lines: 98

## Acceptance

- All 7 items from issue #4301 addressed.
- Doc files contain no references to `check-plan-size.sh` or `revise-plan-with-waterfall.sh`.
- `relevant-checks.sh` maps `design-clarify.sh` to `test-design-clarify`.
- SKILL.md fail-safe guard keys on `.completed/step-2b.5`.
- `test-design-structure.sh` ordering assertions are anchored and pass.
- `review-design-step3-loop.sh` lines 655 and 786 use `step3_loop_read_round_start_s`.
- `design-log-publish.sh` non-final path fetches `origin/<default>` before idempotency check.
- `test-design-log-publish.sh` has a byte-complete squash idempotency case.
- `make lint` passes; `bash scripts/test-design-structure.sh` passes; `bash scripts/test-design-log-publish.sh` passes.

diff_lines: 98

## Test plan
(no test plan section in plan-file)
