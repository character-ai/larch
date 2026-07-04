## Goal
Implement issue #6291: [IMPLEMENTING] [BUG] OOS issue rarely files: gate on aggregate severity, not per-item acceptance….

## Implementation Plan
## Plan

## Approach

Implement the minimum change at the tally and design OOS handoff seams.

Use the existing `_body_severity_for_block(block)` helper in `plan_review_tally.py` to read block body severity. In `review_tally.py`, add an equivalent `_body_severity_from_text(text)` inline helper (mirroring `compose_review._extract_body_severity`) rather than introducing a new shared module. Normalize the result to lowercase; classify `blocking` and `important` as high-trigger, `latent` as latent-trigger. Do not use judge vote severity for the aggregate trigger.

Preserve the current vote-accepted path. During each tally loop, collect the non-security OOS filing pool into a **cumulative per-run pool file** instead of evaluating the trigger per round:

- OOS-tagged review items with any vote result (including accepted, to make trigger counts accurate).
- Latent-rerouted findings.
- Neutral-rescued findings.
- Exclude security-classed blocks from the public filing pool.

Do not evaluate the aggregate trigger inside the tally functions. Append each public pool item (with its body severity) to `oos-aggregate-pool.md` for `/design` and a session-level pool file for `/implement`. This file accumulates across all review rounds.

Evaluate the trigger at filing time with the full per-run view. The trigger pool for **severity counting** is: the cumulative pool sidecar items plus non-security items already in the vote-accepted sink (de-duped by block identity). For `/implement`, also include items from `oos-accepted-main-agent.md`. This ensures vote-accepted latent items count toward the three-item threshold.

Fire if at least one pool item has body severity `important` or `blocking`, or if the total de-duped count of `latent`-severity items (across pool and accepted sink) is at least three.

When the trigger fires, add pool items not already in the accepted sink to the sink. Normalize rerouted findings (`FINDING_N`-headed blocks) to `### OOS_N:` headers (seed sequence from max existing `OOS_N` in the accepted sink). De-dupe promoted items against existing sink content before writing.

**Order of operations in `file_oos_prepare_main`**: run pool read, trigger evaluation, and promotion **before** any `skip-sentinel` or `skip-no-items` early returns, so pool-only qualifying OOS always reach filing, including on same-issue re-runs. Only after pool evaluation and any promotion: compute `_extract_unfiled_blocks`, and then evaluate sentinel/no-items early returns.

**`/implement` emit_tally promotion order**: run `oos serialize` first (produces vote-only output), then evaluate the aggregate trigger and append promoted items to `oos-accepted-review.md`. This prevents the `oos serialize` rebuild from wiping promoted blocks. Add `OOS_FILING_COUNT` KV equal to the non-security accepted-sink count after promotion. Keep `OOS_ACCEPTED_COUNT` vote-based.

**Bug A fix** (empty `/issue` stdout):

- `file_oos_annotate_main`: emit `FILE_DESIGN_OOS_STATUS=annotate-failed-empty-stdout` and `NEXT_ACTION=retry-file-and-annotate`. Do not write `oos-issues-created.md`. Limit this wrapper to emitting the retryable status; it does not call `/larch:issue`.
- `finalize-step5.md`: own the prompt-side retry branch. When `annotate-failed-empty-stdout` is returned with `NEXT_ACTION=retry-file-and-annotate`, re-run `/larch:issue` (capturing stdout to `oos-issue.stdout.txt`), then re-run annotate. Guard with a once-only sentinel (`.oos-issue-retry-used`) to prevent a second retry. On second failure, surface a non-retryable error without writing `.completed/step-5b`.

**Bug B fix** in `file_oos_prepare_main` (unchanged): after sentinel recovery, compute `_extract_unfiled_blocks`; emit `skip-sentinel` only when no unfiled blocks remain; else remove the restored sentinel and fall through.

**Pool cleanup on re-entry**: when Step 3 is re-entered from Gate C with `--reentry` (direct-review-entry cleanup), reset `oos-aggregate-pool.md` alongside existing stale review artifacts so previously rejected OOS cannot be re-promoted by the new review run.

## Files to modify/create

### UPDATED: python/larch/review/plan_review_tally.py

During `_render`, append public non-security pool items (any-vote OOS + rerouted findings) and their body severity to a cumulative `oos-aggregate-pool.md`. Include accepted OOS in the pool sidecar for trigger counting (de-dupe at evaluation time). Do not evaluate the trigger here. Use `_body_severity_for_block(block)` for body severity. Promotion and OOS header normalization happen at filing time in `design_oos.py`.

### UPDATED: python/larch/review/review_tally.py

Two changes:

- `tally_code_votes`: append public non-security pool candidates (any-vote OOS + rerouted findings, including accepted OOS) to a session-level pool file (via `oos_accepted_out.parent` or `session_env_path.parent`). Use `_body_severity_from_text(text)` inline helper for body severity. Keep vote-result counts and scoreboards unchanged.
- `emit_tally`: run `oos serialize` first (vote-only rebuild), then evaluate the aggregate trigger from the session pool (plus `oos-accepted-main-agent.md` if present), and append promoted items to `oos-accepted-review.md`. Add `OOS_FILING_COUNT` KV for the total non-security sink count after promotion. Relax no equality guard — keep the existing guard intact but add `OOS_FILING_COUNT` as a separate key. Also thread the pool file path through `emit_tally` call sites in `review_core_body.py` via `--session-env-path` or `--implement-tmpdir`.

### UPDATED: python/larch/review/review_core_body.py

Thread `--session-env-path` (or an explicit pool path) through every production `emit_tally` call so aggregate trigger evaluation can resolve the parent pool. Mirror the zero-findings branch where this flag is already threaded.

### UPDATED: python/larch/design/design_oos.py

Primary change: in `file_oos_prepare_main`, reorder so aggregate pool read, trigger evaluation, and promotion run **before** any `skip-sentinel` or `skip-no-items` returns. After pool evaluation and any promotion, continue with normal prepare (compute `_extract_unfiled_blocks`, sentinel checks, filing batch). Normalize promoted rerouted finding chunks to `### OOS_N:` headers (seeded from max existing OOS number). De-dupe against current accepted sink.

Bug A: emit `NEXT_ACTION=retry-file-and-annotate` on empty stdout. Keep `file_oos_annotate_main` limited to emitting the retryable status and withholding any sentinel write; it does not invoke `/larch:issue`.

Bug B: after sentinel recovery, check `_extract_unfiled_blocks` before emitting `skip-sentinel`.

### UPDATED: skills/design/references/finalize-step5.md

Document the `annotate-failed-empty-stdout` + `retry-file-and-annotate` retry branch in the Step 5b dispatch: re-run `/larch:issue` capturing stdout, then re-run annotate, guarded by `.oos-issue-retry-used` once-only sentinel. On second failure, surface a non-retryable error without writing `.completed/step-5b`.

### UPDATED: scripts/design-step3-entry.sh (or equivalent direct-review-entry cleanup)

Reset `oos-aggregate-pool.md` alongside stale review artifacts when `--reentry` runs, so re-entered review starts with a clean pool.

### UPDATED: python/tests/review/test_plan_review.py

Add focused plan-review tally tests:

- One non-accepted OOS with body severity `important` adds to `oos-aggregate-pool.md` during tally (not directly to accepted sink).
- Three latent pool items (counting pool + accepted sink) trigger filing at `file_oos_prepare_main`.
- Two latent pool items plus one latent already in accepted sink = three total, trigger fires.
- One or two latent items total do not trigger.
- Security-classed OOS excluded from pool and filing even when trigger fires.
- Vote-accepted OOS still writes when aggregate trigger does not fire.
- A promoted latent-rerouted `FINDING_N` block reaches `oos-combined.md` with an `OOS_N` header.
- Pool evaluation runs before skip-sentinel: a qualifying pool with a recovered sentinel still files.

### UPDATED: python/tests/review/test_review_tally.py

Add symmetric `/implement` code-review tally tests:

- Pool candidates accumulate to session-level pool file.
- Trigger evaluation after `oos serialize` (not before) so promoted items survive.
- Three latent pool items promote after emit-tally; accepted sink reflects promotion.
- `OOS_FILING_COUNT` reflects sink size after promotion; `OOS_ACCEPTED_COUNT` remains vote-based.
- Assert both local and session-level accepted OOS outputs.
- Pool plus main-agent OOS latent count reaches threshold and fires.
- `review_core_body.py` threads `--session-env-path` through emit_tally.

### UPDATED: python/tests/design/test_design_oos.py

Add or adjust tests for Bug A, Bug B, and the aggregate trigger:

- Empty stdout emits `annotate-failed-empty-stdout` and `retry-file-and-annotate`, no sentinel written.
- `finalize-step5.md` retry contract: once-only sentinel prevents second retry.
- Cross-session sentinel recovery with all blocks filed still emits `skip-sentinel`.
- Cross-session sentinel recovery with one new unfiled block falls through to `ready`.
- Qualifying pool evaluates before skip-sentinel: important pool item + recovered sentinel produces `ready`, not `skip-sentinel`.
- Multi-round pool: two latent in round 1 plus two in round 2 fires the three-latent trigger at prepare time.
- Pool plus accepted-sink latent count: one latent in pool plus two already in accepted sink fires trigger.

### MAY_UPDATE: docs/issue-anchored-plan.md

Only update if the accepted OOS artifact contract or Step 5b status grammar changes.

## Edge cases

- A qualifying trigger promotes all public pool items not already in the accepted sink.
- Security-classed OOS excluded from public pool and filing even when trigger fires.
- Pool evaluation runs before skip-sentinel/skip-no-items returns in `file_oos_prepare_main`.
- Promoted rerouted `/design` findings receive `OOS_N` headers so `_extract_unfiled_blocks` parses them.
- OOS sequence numbers seeded from max existing `OOS_N` in the accepted sink.
- `/implement` promotion appended after `oos serialize`, not before, so serialize cannot wipe it.
- `oos-aggregate-pool.md` reset on direct-review-entry (Gate C re-entry) so stale items do not re-trigger.
- Pool includes vote-accepted OOS for severity counting; de-dupe prevents re-promotion.
- Main-agent OOS in `/implement` counts toward trigger severity threshold.
- Bug A retry is once-only; second failure surfaces non-retryable without writing `.completed/step-5b`.

## Failure modes

- Evaluating trigger per-round instead of per-run misses latent items split across rounds.
- Skip-sentinel or skip-no-items returning before pool evaluation blocks pool-only qualifying OOS from filing.
- `oos serialize` running after pool promotion would wipe promoted blocks; fix: evaluate and append after serialize.
- Promoted `/design` rerouted chunks with `FINDING_N` headers bypass `_extract_unfiled_blocks`.
- Stale `oos-aggregate-pool.md` from a prior Gate C re-run can over-promote OOS from the previous plan.
- Bug A retry without a once-only sentinel can loop twice or silently continue to Step 5b.5.
- Bug B without checking `_extract_unfiled_blocks` before skip-sentinel still suppresses new OOS on re-runs.

## Testing strategy

Run focused unit tests only:

- `python -m pytest python/tests/review/test_plan_review.py -k 'oos or latent or pool'`
- `python -m pytest python/tests/review/test_review_tally.py -k 'oos or latent or pool or emit'`
- `python -m pytest python/tests/design/test_design_oos.py -k 'oos or stdout or sentinel or pool or retry'`

Then run changed-file lint:

- `make py-lint`
- `python3 python/cli.py checks run-relevant`

If `review_core_body.py` changes, also run: `python -m pytest python/tests/review/test_review_core_body.py`

## Acceptance

Run focused unit tests only:

- `python -m pytest python/tests/review/test_plan_review.py -k 'oos or latent or pool'`
- `python -m pytest python/tests/review/test_review_tally.py -k 'oos or latent or pool or emit'`
- `python -m pytest python/tests/design/test_design_oos.py -k 'oos or stdout or sentinel or pool or retry'`

Then run changed-file lint:

- `make py-lint`
- `python3 python/cli.py checks run-relevant`

If `review_core_body.py` changes, also run: `python -m pytest python/tests/review/test_review_core_body.py`

diff_lines: 490

## Test plan
(no test plan section in plan-file)
