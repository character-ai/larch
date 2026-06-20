## Goal
Implement issue #4864: [IMPLEMENTING] [OOS] /design Step 5c publish/final-summary + plan-review/slot/timeout (7 items).

## Implementation Plan
## Plan

## Approach

- Treat `NO_SKETCHES` as binding. Use direct code and test inspection only.
- Keep the 60s probe timeout. Add a code comment only.
- Preserve Step 5c contracts:
  - FD3 / `emit_kv` grammar.
  - `LARCH_FINAL_SUMMARY_BEGIN` / `LARCH_FINAL_SUMMARY_END`.
  - publish exit codes `{0,1,3,4}` as normal paths.
  - `.completed/step-5c-terminal` and `.completed/step-5c` semantics.
  - `PLAN_WRITE_OK` / `PUBLISH_OK` cleanup gating.
- Keep `python/design_publish.py` edits merge-order agnostic because #4865 may touch a nearby publish surface.
- Do **not** edit `python/plan_review.py`. Round-2+ duplicate convergence (`prior_keys`, `high_new`, `non_nit_new`, `DUPLICATE_ACCEPTED_COUNT`) and applied-finding ledger behavior already exist; extend tests only.

## Files to modify/create

### UPDATED: python/design_publish.py

- In `publish_core`, update the `named-block write` subprocess so child stdout cannot inherit Step 5c's captured fd1.
  - Add `stdout=subprocess.DEVNULL` to that subprocess.
  - Leave return-code handling unchanged.
  - Do not redirect stdout for unrelated subprocesses.
- Distinguish **omitted** `--session-id` from **present empty** `--session-id ""`:
  - During argv parsing, track `session_id_provided: bool` (set `True` when the `--session-id` token is consumed).
  - Keep `--design-tmpdir`, `--issue`, and `--claude-pid` required.
  - When `--session-id` is **omitted** (`session_id_provided` is `False`), return usage rc `5` (fail closed).
  - When `--session-id` is **present** with an empty value (`session_id_provided` is `True` and `parsed["--session-id"] == ""`), allow publish to continue.
  - On the present-empty path, skip the `design log-publish` subprocess entirely.
  - Do not append `PUBLISH_OK` from log-publish on the skip path; leave rename / plan-write / validator behavior unchanged.
- Do not change validation, rename, result-env write, or non-empty session log-publish behavior.

### UPDATED: python/design_lifecycle.py

- Harden `_step5c_render_final_summary` against stale success-path output.
- **Gate pre-render unlink to success outcomes only** so failed-plan-write (`outcome == "failed-plan-write"`, `plan_write_ok != "true"`) preserves the existing stdout-fallback summary contract exercised by `test_step5c_core_rc1_uses_stdout_over_stale_primary_and_binds_final_summary_path`.
  - Run pre-clear only when `outcome == "approved"` **or** `plan_write_ok == "true"` (pass `plan_write_ok` into `_step5c_render_final_summary`, or derive the same gate at each call site before unlink).
  - Skip unlink entirely on failure outcomes (`failed-plan-write`, `failed-publish-tail`, and any path where `plan_write_ok != "true"`).
- When the success gate passes, clear only the summary file that emit will later read:
  - Resolve the target with the **same rule as** `_emit_final_summary_marked_from_disk`:
    - `Path(os.environ.get("FINAL_SUMMARY_PATH"))` when `FINAL_SUMMARY_PATH` is set in `os.environ`.
    - Otherwise `design_tmpdir / "final-summary.md"`.
  - Do **not** use only the stale `env` dict or a hard-coded `design_tmpdir / "final-summary.md"` when `os.environ["FINAL_SUMMARY_PATH"]` was set by Step 5c after publish.
- Apply resolved-path containment before unlink:
  - `summary_resolved = summary_path.resolve()`
  - `tmpdir_resolved = design_tmpdir.resolve()`
  - Unlink only when `summary_resolved.is_relative_to(tmpdir_resolved)` and the file exists.
  - Skip unlink when the path is outside `design_tmpdir` (prefix checks alone are insufficient).
- Keep the existing render failure gate:
  - Return `False` when rendering returns non-zero or raises.
  - Emit marked final summary only when render returns `True`.
- Leave cleanup eligibility logic unchanged:
  - `plan_write_ok == "true"`.
  - `STANDALONE_HEAVY_FAILED != "true"`.
  - no `SESSION_ID`, or `PUBLISH_OK=true`.

### UPDATED: python/plan_review_panel.py

- Add an explicit failure handoff from `_dynamic_slot_rows` to `dispatch_panel`.
- Change `_dynamic_slot_rows` to return `tuple[list[dict[str, object]], list[tuple[str, str, int]]]`:
  - First element: slot rows (unchanged shape).
  - Second element: per-slot failures as `(slot_name, tool, return_code)`.
- On dynamic `render plan-review` non-zero exit:
  - Keep writing the current one-line fallback prompt through `_slot_row`.
  - Append `(slot, tool, proc.returncode)` to the failures list.
  - Append a sanitized per-slot warning to `execution-issues.md` under `Warnings`.
- In `dispatch_panel`:
  - Replace `rows.extend(_dynamic_slot_rows(...))` with unpacking `dynamic_rows, dynamic_failures = _dynamic_slot_rows(...)`.
  - Extend `rows` with `dynamic_rows`.
  - When `dynamic_failures` is non-empty, emit one compact stdout warning KV.
    - Reuse `INVALID_SLOT_PANEL_WARNING` if that key already carries degraded-panel warnings; otherwise add a dedicated key such as `DYNAMIC_RENDER_PANEL_WARNING`.
    - Summary format: count plus up to three slot names; sanitize multiline stderr before logging.
  - Do not alter static slot fallback behavior.
  - Do not fail panel dispatch solely because dynamic render warnings were emitted.
- Keep the dynamic manifest contract unchanged.

### UPDATED: python/agents.py

- Add a short comment near the `LARCH_PROBE_TIMEOUT_SECONDS` default.
- State that `60` is intentional to avoid degraded-tools false negatives from slow probes.
- Mention that timeout retries default to `0`.
- Do not change behavior.

### UPDATED: python/test_design_publish.py

- Extend the fake CLI so `named-block write` can print a sentinel line to stdout.
- Add a regression test that:
  - Runs `publish_core`.
  - Makes fake `named-block write` print stdout noise.
  - Asserts the sentinel line is absent from `publish_core` stdout.
  - Asserts normal publish rows still appear.
- Add a regression test that **present empty** `--session-id ""` allows publish to complete with `PLAN_WRITE_OK=true` and does not invoke `design log-publish`.
- Add a regression test that **omitted** `--session-id` returns usage rc `5` and does not write the plan block or rename.
- Do **not** add or keep a test that treats empty `--session-id` usage rc `5` as the desired contract for Step 5c's explicit-empty path.

### UPDATED: python/test_design_lifecycle.py

- Add Step 5c stale-summary **success-path** coverage only (gated unlink):
  - Pre-create a stale summary at a custom path inside `design_tmpdir`.
  - Make publish succeed with `PLAN_WRITE_OK=true` and set `FINAL_SUMMARY_PATH` in the environment to that path (via fake publish rows / Step 5c flow).
  - Make render return `0` without writing new content.
  - Assert no final-summary markers are emitted and the stale file was cleared before render.
- Keep existing `test_step5c_core_rc1_uses_stdout_over_stale_primary_and_binds_final_summary_path` behavior: failed-plan-write must **not** pre-clear the bound summary file; stale `current-summary.md` text may still appear in markers when render returns `0` without writing.
- Keep existing render-failure stale-summary coverage.
- Add failure-tail coverage:
  - rc `2` / rc `5` stages failure-tail state.
  - `.completed/step-5c-terminal` is written.
  - failure sidecars can be emitted.
- **Required** cleanup eligibility matrix expansion:
  - Add parametrized case: `STANDALONE_HEAVY_FAILED=true`, `PUBLISH_OK=true` → `CLEANUP_ELIGIBLE=false`.
  - Keep existing rows: no session id; session id plus `PUBLISH_OK=true`; session id plus `PUBLISH_OK=false`; session id plus missing `PUBLISH_OK`.
- Add integration coverage that empty `SESSION_ID` reaches the cleanup gate with `CLEANUP_ELIGIBLE=true` when publish succeeds (fake `publish_core` returns `0` with `PLAN_WRITE_OK=true`).

### UPDATED: python/test_plan_review.py

- Keep existing regression tests for round-2+ already-applied findings:
  - Round 1 accepted important/blocking finding continues.
  - Round 2 re-raises the same finding.
  - Continuation stops with `PLAN_REVIEW_CONTINUE=false`.
  - Output includes `DUPLICATE_ACCEPTED_COUNT`.
- Keep existing tests that:
  - Direct review entry clears the applied-finding ledger.
  - `emit-rejected` filters applied findings from the emitted body without mutating `rejected-findings.md`.
- No production edits to `python/plan_review.py` in this change set.

### UPDATED: python/test_plan_review_panel.py

- Add a dynamic render failure regression test.
- Use a fake plugin `python/cli.py` or monkeypatch so `render plan-review` exits non-zero for dynamic slots only.
- Assert:
  - `_dynamic_slot_rows` returns failures alongside rows.
  - `plan-review-slots.ndjson` still includes the dynamic rows.
  - The dynamic prompt file contains the one-line fallback.
  - `execution-issues.md` contains a dynamic render warning.
  - `dispatch_panel` stdout contains the aggregate warning key.
  - static slots still render or fall back as before.

## Edge cases

- If `FINAL_SUMMARY_PATH` resolves outside `design_tmpdir`, do not unlink it; emit may still read it, but pre-render clear must skip deletion even on success paths.
- Pre-render unlink runs only on success outcomes (`outcome == "approved"` or `plan_write_ok == "true"`). Failed-plan-write must not delete the bound summary file before emit.
- If `FINAL_SUMMARY_PATH` is set in `os.environ` after publish but `_step5c_render_final_summary` only reads `env`, stale custom-path summaries can leak on success paths; pre-clear must read `os.environ` with the same fallback as emit.
- If a dynamic render failure has multiline stderr, sanitize it before any warning row.
- If multiple dynamic slots fail, emit one compact aggregate warning instead of many noisy stdout rows; per-slot detail may still land in `execution-issues.md`.
- If the named-block subprocess fails, keep the existing rc `1` / `3` fallback behavior.
- If `--session-id` is **present empty**, skip log-publish without fabricating `PUBLISH_OK=false`; cleanup remains eligible when `plan_write_ok == "true"` and `SESSION_ID` is empty.
- If `--session-id` is **omitted**, fail closed with usage rc `5`; do not treat omission as an empty session.

## Failure modes

- A child process can still write to stderr. This plan only fixes the reported fd1 leak.
- A malicious or invalid `FINAL_SUMMARY_PATH` may point outside the tmpdir. Resolved `is_relative_to` containment avoids unsafe unlink; emit-side checks remain the backstop.
- Unconditional pre-render unlink on failed-plan-write would break the rc `1` stdout-fallback summary contract; success-only gating prevents that regression.
- Dynamic render failure warnings must not make panel dispatch fail by themselves.
- Allowing present-empty session id must not weaken omitted-flag validation; legacy callers that drop `--session-id` entirely should still fail closed with rc `5`.

## Testing strategy

- Run targeted tests first:
  - `python3 -m pytest python/test_design_publish.py`
  - `python3 -m pytest python/test_design_lifecycle.py`
  - `python3 -m pytest python/test_plan_review.py`
  - `python3 -m pytest python/test_plan_review_panel.py`
  - `python3 -m pytest python/test_agents.py`
- Then run required repo checks:
  - `make py-lint`
  - `make py-test`
  - `make lint`

## Acceptance

- **Item 1**: `publish_core`'s `named-block write` subprocess sets `stdout=subprocess.DEVNULL`; a regression test asserts child stdout noise is absent from `publish_core` stdout while normal publish rows remain.
- **Item 2**: `design_publish.py` distinguishes omitted `--session-id` (rc `5`, fail closed) from present-empty `--session-id ""` (publish continues, log-publish skipped); tests cover both, plus the cleanup-eligibility matrix in `test_design_lifecycle.py` (including `STANDALONE_HEAVY_FAILED=true` and empty-`SESSION_ID`-eligible rows).
- **Item 3**: Step 5c pre-render unlink runs only on success outcomes, resolves the target via the same `FINAL_SUMMARY_PATH`/fallback rule as emit, and is `is_relative_to`-contained to `design_tmpdir`; the rc-1 stdout-fallback summary contract is preserved; a success-path stale-summary test asserts no markers leak.
- **Item 4**: `test_design_lifecycle.py` covers Step 5c failure-tail (rc `2`/`5` staging, `.completed/step-5c-terminal`, sidecars) and the expanded cleanup-eligibility matrix.
- **Item 5**: no production change to `plan_review.py`; the existing round-2+ dedup ledger and `DUPLICATE_ACCEPTED_COUNT` behavior is covered by retained/extended tests in `test_plan_review.py`.
- **Item 6**: `_dynamic_slot_rows` returns per-slot failures; `dispatch_panel` emits one aggregate warning KV plus per-slot `execution-issues.md` warnings on dynamic render non-zero exit, without changing the static fallback or failing dispatch; `test_plan_review_panel.py` asserts this.
- **Item 7**: `agents.py` carries a comment explaining the intentional 60s `LARCH_PROBE_TIMEOUT_SECONDS` default and 0 default retries; no behavior change.
- `make py-lint`, `make py-test`, and `make lint` pass.

diff_lines: 213

## Test plan
(no test plan section in plan-file)
