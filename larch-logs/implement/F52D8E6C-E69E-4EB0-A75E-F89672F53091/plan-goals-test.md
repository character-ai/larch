## Goal
Implement issue #6791: [IMPLEMENTING] [BUG] /implement --merge: client pre-commit hook aborts run-log commit; ship stalls pre-PR and step8-shippr recovery deadlocks on pre-terminal 'stalled' label.

## Implementation Plan
## Plan

## Approach

Implement the five approved fixes as one coupled repair, incorporating the three accepted review revisions below.

1. Make `_commit_run` retry the git commit tail exactly once after a non-zero `git commit`.
   - Keep copy, scrub, volatile-only detection, and breadcrumb publish **outside** the retried block.
   - Factor **only** the post-copy `git add` → `git diff --cached --quiet` → `git commit` tail into a small helper.
   - Retry the helper once after the commit step fails; do not re-run copy or scrub on retry.
   - Do not use `--no-verify`.
   - If the retry's `git diff --cached --quiet` finds nothing staged, return the existing unchanged success shape with `SECRET_SCRUB_VIOLATIONS`.
   - If the retry also fails, detect both fixer-hook output (for example `files were modified by this hook`) **and** checking-only hook failure output, then append one remedy line mentioning `--no-logs-commit` and adding a `larch-logs/` exclude to the client's hook config file (name the file as `.pre-commit-config.yaml` in the remedy; the classifier fix in item 4 prevents that substring from misrouting recovery).

2. De-terminalize ship state and hydrated `RunContext` on Python ship-driver re-entry.
   - Add `_destall_pre_pr_reentry(ctx, resume, runner, repo_root) -> RunContext | ShipResult` in `ship.py`.
   - **Placement (single rule):** invoke only after `_resume_plan` is computed and after all early-return recovery branches finish (`done`, `merged`, `postmerge-push-watch`, `emergency-repair`); **immediately before** the first pre-PR call site that can reach `flush_logs_pre`. Do **not** assign at `run_ship` entry or immediately after `_blocked_resume_result`.
     - `fresh`: call after `_hydrate_fresh_context`, before `flush_logs_pre` in the postbump path.
     - `pre-pr-compose` / `open-pr`: call after `_hydrate_resume_context` (or equivalent), before `_compose_assessment_gate_before_pr` / `_flush_guideline_outcome_before_pr`.
   - **Scope:** only when `ship-pr-state.sh` has `PHASE=stalled` **and** `resume.start` is a pre-PR path (`fresh`, `pre-pr-compose`, or `open-pr`). Skip for post-merge resume starts and for `merged`/`done` recovery paths that still need the stalled overlay.
   - **Finalize-state handling (fail-closed):**
     - If `finalize-state.sh` is a regular file inside the allowed tmpdir, delete it.
     - If it exists but is a symlink or other non-regular shape, **fail closed**: return a terminal `ShipResult` or raise `Stalled` and do **not** call `flush_logs_pre`. Do not fall back to rewriting only `STALL_TRACKING=false` while leaving `PHASE`/`EXIT_CODE`/`BAIL_REASON` terminal residue.
   - On success: call `_write_ship_state` with `ctx.with_(stall_tracking=False, stall_step="")` (leave `terminal_outcome` unset) and the mapped in-progress phase for the selected `ResumePlan`, reusing the existing non-terminal key-pop path (`_TERMINAL_ONLY_STATE_KEYS` and `_NON_STALL_STATE_KEYS`).
   - Assign the returned de-stalled `ctx` to the working context variable (`fresh_context` or `pr_context`) at the single pre-PR callsite so every subsequent `_write_ship_state` and flush uses it.
   - Emit a breadcrumb recording prior phase and new phase.
   - Do not change prompt-side orchestration or session-env writers.

3. Add a dedicated pre-terminal refusal skip reason.
   - Add `REFRESH_SKIP_PRETERMINAL_OUTCOME`.
   - Return it from `_preterminal_outcome_refresh_skip`.
   - Mirror behavior wherever `REFRESH_SKIP_COMMIT_FAILED` currently means "allowed for merge refresh" or "blocks direct commit because the error is pre-terminal".
   - Keep the ship-driver flush callsites fail-closed; the new reason must still stall there.

4. Add explicit classifier routing for ship refresh stalls **before** the lint substring check.
   - In `_classify_text`, add an **early** branch (before the `pre-commit` / `lint-output` token check at ~line 174) keyed on:
     - `REFRESH_SKIP_PRETERMINAL_OUTCOME` in evidence text, and/or
     - `STALL_STEP=pr-create-guideline-outcome-refresh`, and/or
     - `pr-create-guideline-outcome-refresh` combined with pre-terminal refusal detail.
   - Return `FAILURE_CLASS=transient-infra` with `RESUME_HINT=step8-shippr`.
   - Do not rely on phase fallback alone; do not broaden unrelated commit failures.
   - Add a classify test where evidence includes the remedy line (mentioning `.pre-commit-config.yaml`) plus the refresh stall step, asserting `transient-infra` / `step8-shippr` rather than `lint-failure`.

5. Normalize run-log text emission.
   - Add one shared helper at the run-log batch write boundary for non-empty text: strip trailing newlines and append exactly one newline.
   - Apply it to replace batches, append batches, round artifacts, and shared archetype artifacts emitted through the run-log batch module.
   - Preserve validation semantics; JSON and JSONL payloads remain valid with a trailing newline.
   - Keep empty artifacts empty unless a specific writer already emits a newline.

6. Make volatile-only sidecar comparisons hook-tolerant.
   - Normalize trailing whitespace and final newline for `_committed_guideline_outcome_matches` and `_committed_invariant_outcome_matches`.
   - Keep the comparison conservative; only normalize the hook-fixer class, not arbitrary JSON semantics.

## Files to modify/create

### UPDATED: python/larch/report/run_log_commit.py

- Add a private post-copy commit-tail helper used by `_commit_run`.
- Keep copy, scrub, volatile-only detection, and breadcrumb publish outside the helper and outside the retry loop.
- Retry the helper exactly once after a failed commit; never re-run copy or scrub between attempts.
- Preserve existing return envelopes for success, unchanged, volatile-only, scrub failures, and add failures.
- Add a pre-commit failure detector covering both fixer output and checking-only hook output; append the remedy line on second failure.
- Leave `_larch_log_commit` unchanged unless implementation re-verifies a live production caller; if changed, keep behavior aligned instead of forking semantics.

### UPDATED: python/larch/implement/ship.py

- Add `_destall_pre_pr_reentry` that:
  - runs only for pre-PR stalled resume starts after merged/done/emergency early-return branches complete;
  - deletes stale `finalize-state.sh` when it is a regular file;
  - on non-regular `finalize-state.sh`, fails closed (terminal `ShipResult` or `Stalled`) without calling `flush_logs_pre`;
  - calls `_write_ship_state` with `ctx.with_(stall_tracking=False, stall_step="")` and the mapped in-progress phase;
  - returns the de-stalled `RunContext` on success.
- Invoke at the single pre-PR placement rule above; assign returned `ctx` to `fresh_context` or `pr_context` immediately before the first `flush_logs_pre` reachability point. Remove any `run_ship`-entry placement.
- Map resume starts to existing in-progress phases:
  - `fresh`: `pr-prep`
  - `pre-pr-compose` and `open-pr`: `config.SHIP_ROUTE_ACTION_ASSESSMENTS`
- Do not reset on post-merge resume starts.
- Normalize guideline and invariant sidecar byte comparisons for trailing whitespace and final newline.

### UPDATED: python/larch/core/config.py

- Add `REFRESH_SKIP_PRETERMINAL_OUTCOME`.
- Add it to `REFRESH_SKIP_MERGE_OK`.
- Keep it out of `REFRESH_SKIP_POST_ENSURE_PR_OK` unless existing behavior demands otherwise.

### UPDATED: python/larch/report/run_log_flush.py

- Return the new reason from `_preterminal_outcome_refresh_skip`.
- Include the new reason in refresh CLI reporting wherever commit-failed and recovery-failed are printed as `REFRESH_COMMITTED=false`.
- Keep `_check_preterminal_outcome_label`, `_preterminal_outcome_commit_blocked`, and forbidden labels unchanged.

### UPDATED: python/larch/implement/step_7a.py

- Update `_refresh_skip_blocks_direct_commit` to block on `REFRESH_SKIP_PRETERMINAL_OUTCOME`.
- Keep existing error-text fallback if needed for backward compatibility with old run logs or monkeypatched tests.

### UPDATED: python/larch/state/_classify.py

- Add an **early** `_classify_text` matcher (before the `pre-commit` lint substring branch) for evidence carrying `REFRESH_SKIP_PRETERMINAL_OUTCOME` and/or `STALL_STEP=pr-create-guideline-outcome-refresh` / `pr-create-guideline-outcome-refresh` pre-terminal refresh shape.
- Route that shape to `FAILURE_CLASS=transient-infra` with `RESUME_HINT=step8-shippr`.
- Avoid broadening unrelated commit failures or generic phase fallback.

### UPDATED: python/larch/report/run_log_batch.py

- Add the shared run-log text normalization helper.
- Apply it in `_write_batch`, `_append_batch`, `_stage_round_artifact`, and `_atomic_write` call paths owned by run-log artifacts.
- Keep redaction before publish.
- Keep validation before or after normalization in a way that preserves existing JSON and JSONL contracts.

### UPDATED: python/larch/report/run_logs.py

- Normalize round-artifact and shared archetype writes before comparing and writing.
- Keep duplicate basename, deny-list, and debug-artifact behavior unchanged.

### UPDATED: python/tests/report/test_run_logs.py

- Add hermetic git tests for `_commit_run`:
  - fixer pre-commit hook appends missing final newline, fails first commit, passes retry, and commits hook-clean logs;
  - checking-only hook fails both attempts, invokes exactly two commits, and surfaces the remedy line;
  - retry diff-quiet path returns unchanged success when the hook restores HEAD content;
  - assert copy/scrub does not run between the two commit attempts (for example via monkeypatch counters).
- Update existing newline-sensitive batch and round-artifact tests to expect normalized final newlines.

### UPDATED: python/tests/report/test_run_log_flush.py

- Update pre-terminal refusal assertions to expect `REFRESH_SKIP_PRETERMINAL_OUTCOME`.
- Add coverage that `flush_logs_pre` still refuses a genuinely terminal pre-terminal summary.
- Add coverage that neutral `shipping` still commits.

### UPDATED: python/tests/implement/test_ship.py

- Add a pre-PR stalled-state re-entry test that:
  - seeds `ship-pr-state.sh` with `PHASE=stalled` and `STALL_TRACKING=true`;
  - seeds `finalize-state.sh` with terminal stall overlay;
  - hydrates `ctx` with stall fields set;
  - runs the ship path far enough to reach the first pre-PR refresh;
  - asserts before the first `flush_logs_pre`: `PHASE` is an in-progress label, `STALL_TRACKING=false`, `STALL_STEP` is empty, and `finalize-state.sh` is absent;
  - asserts after the first post-reset state write: stall keys remain cleared on disk;
  - asserts `flush_logs_pre` is not skipped for the preterminal reason and `_flush_guideline_outcome_before_pr` does not raise after de-terminalize.
- Add a fail-closed re-entry test with a **symlinked** `finalize-state.sh` overlay asserting the drive stalls (or returns terminal) **without** reaching `flush_logs_pre` or looping on pre-terminal refresh.
- Update existing refresh-skip tests to keep fail-closed behavior for the new reason.

### UPDATED: python/tests/implement/test_ship_state.py

- Add focused coverage that non-terminal `_write_ship_state` clears terminal-only and stall-only fields when `stall_tracking` is false.
- Cover the state shape used by the re-entry reset with `ctx.with_(stall_tracking=False, stall_step="")`.

### UPDATED: python/tests/implement/test_step_7a.py

- Update the direct-commit block test for `REFRESH_SKIP_PRETERMINAL_OUTCOME`.
- Keep one compatibility case if the helper still accepts old `commit-failed` plus pre-terminal text.

### UPDATED: python/tests/core/test_config.py

- Assert `REFRESH_SKIP_PRETERMINAL_OUTCOME` is in `REFRESH_SKIP_MERGE_OK`.
- Assert it is not in post-ensure allowed sets unless implementation finds an existing consumer that requires it.

### UPDATED: python/tests/state/test_classify.py

- Add a focused classify test where evidence contains `REFRESH_SKIP_PRETERMINAL_OUTCOME` and `STALL_STEP=pr-create-guideline-outcome-refresh`.
- Assert `FAILURE_CLASS=transient-infra` and `RESUME_HINT=step8-shippr`.
- Add a second case where evidence includes the hook-failure remedy line (`.pre-commit-config.yaml` exclude text) plus `pr-create-guideline-outcome-refresh`, asserting the early branch wins over `lint-failure`.

## Edge cases

- A checking-only pre-commit hook still fails after exactly two commit attempts and surfaces the remedy.
- A file-modifying hook that restores staged files to HEAD returns unchanged success without a second copy.
- A hook that modifies only files outside the pathspec still fails or succeeds according to git's normal behavior.
- A stale `finalize-state.sh` symlink must fail closed: no silent unlink, no partial `STALL_TRACKING=false` rewrite, no `flush_logs_pre`.
- Merged/done/emergency-repair early-return branches must finish before de-terminalization so they can still read the stalled overlay.
- De-terminalization must not run on post-merge resume starts.
- A resumed drive that stalls again must re-mark terminal state through `_write_terminal_state`.
- `--no-logs-commit` remains a skip path, not a retry path.
- Existing pre-terminal forbidden labels remain forbidden.
- In-memory `ctx` stall fields must not be re-persisted after reset on the first post-reset `_write_ship_state`.
- Classifier must not route ship refresh stalls to `lint-failure` when remedy text contains `pre-commit` or `.pre-commit-config.yaml`.

## Failure modes when non-trivial

- Retrying copy/scrub instead of only the commit tail can wipe hook fixes and reproduce the original stall.
- Resetting state before merged/done reconciliation or at `run_ship` entry would erase the phase or summary signal recovery needs.
- Resetting on post-merge resume could clear legitimate terminal evidence.
- Partial finalize reset (only `STALL_TRACKING=false`) leaves `PHASE`/`EXIT_CODE`/`BAIL_REASON` residue and re-normalizes to `stalled`/`bailed`, reproducing the pre-terminal refresh deadlock.
- Deleting `finalize-state.sh` too broadly could erase terminal evidence outside ship re-entry; limit deletion to the allowed tmpdir on pre-PR stalled re-entry only.
- Broad newline normalization can perturb golden tests and JSON fixtures; normalize only non-empty text and keep schema validation.
- Relaxing `ship.py` refresh-skip handling would violate fail-closed behavior; do not add a warn-and-continue branch for the new reason.
- Omitting `ctx.with_(stall_tracking=False, stall_step="")` allows later non-terminal writes to re-persist stall overlay despite a rewritten state file.
- Placing the early classifier after the `pre-commit` lint substring check misroutes remedy-bearing refresh stalls to `step5-review`.

## Testing strategy

Run focused tests first:

- `python -m pytest python/tests/report/test_run_logs.py -k 'commit_run or write_round or batch'`
- `python -m pytest python/tests/report/test_run_log_flush.py -k 'preterminal or refresh'`
- `python -m pytest python/tests/implement/test_ship.py -k 'guideline or stalled or reentry or refresh or symlink'`
- `python -m pytest python/tests/implement/test_ship_state.py`
- `python -m pytest python/tests/implement/test_step_7a.py -k preterminal`
- `python -m pytest python/tests/core/test_config.py -k refresh`
- `python -m pytest python/tests/state/test_classify.py -k 'preterminal or refresh'`

Then run the relevant checker:

- `python3 python/cli.py checks run-relevant`

## Acceptance

Run focused tests first:

- `python -m pytest python/tests/report/test_run_logs.py -k 'commit_run or write_round or batch'`
- `python -m pytest python/tests/report/test_run_log_flush.py -k 'preterminal or refresh'`
- `python -m pytest python/tests/implement/test_ship.py -k 'guideline or stalled or reentry or refresh or symlink'`
- `python -m pytest python/tests/implement/test_ship_state.py`
- `python -m pytest python/tests/implement/test_step_7a.py -k preterminal`
- `python -m pytest python/tests/core/test_config.py -k refresh`
- `python -m pytest python/tests/state/test_classify.py -k 'preterminal or refresh'`

Then run the relevant checker:

- `python3 python/cli.py checks run-relevant`

mechanical_churn: false
oversize_override: operator
diff_lines: 930

## Test plan
(no test plan section in plan-file)
