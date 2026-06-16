## Goal
Implement issue #4476: [IMPLEMENTING] [OOS] /design & /implement workflow script fixes — 2 items.

## Implementation Plan
## Plan

### Files to modify/create

### UPDATED: `skills/design/scripts/design-step5c.sh`

On the success path (lines 325–327), `emit_final_summary_marked_from_disk` is called without first calling `python/cli.py design render-final-summary`. Add the render call immediately before `emit_final_summary_marked_from_disk` inside the `_publish_rc ∈ {0,1,3}` block.

Determine outcome from `PLAN_WRITE_OK`:
- `PLAN_WRITE_OK=true` → `approved`
- otherwise → `failed-plan-write`

Call pattern mirrors `abort_failed_publish_tail()`:

```bash
if [[ "${PLAN_WRITE_OK:-}" == true ]]; then
  _render_outcome="approved"
else
  _render_outcome="failed-plan-write"
fi
python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design render-final-summary   --outcome "$_render_outcome"   --mode "${MODE:-N/A}"   ${REPO:+--repo "$REPO"}   --post-publish-only   >"$DESIGN_TMPDIR/render-final-summary.${_render_outcome}.stdout.log" || true
```

### UPDATED: `skills/design/scripts/design-step5c.md`

Add invariant: wrapper calls `render-final-summary` before emitting summary markers on the normal publish path (rc 0, 1, 3), mirroring the failure-path tail.

### UPDATED: `skills/design/scripts/test-design-step5c.sh`

Add a success-path test case where the publish stub exits 0 with `PLAN_WRITE_OK=true` but does NOT pre-write `final-summary.md`. Assert that `render-final-summary` runs (verify by checking that the summary is written and marked output appears), and that the `LARCH_FINAL_SUMMARY_BEGIN` / `LARCH_FINAL_SUMMARY_END` markers appear in `design-step5c.sh` output. This provides red/green regression protection for the Item 1 fix.

### UPDATED: `python/agents.py`

Fix `seen.add()` placement in `ingest_launcher_token_sidecar` (lines 5075–5082). Currently `seen.add(token_record)` runs before the `if effective_tmpdir:` guard, so when `effective_tmpdir` is None on the first call, `append-record` is permanently skipped even when `effective_tmpdir` becomes available on a retry.

Move `seen.add(token_record)` inside the `if effective_tmpdir:` block:

```python
if token_record not in seen:
    if effective_tmpdir:
        seen.add(token_record)
        runner.run([sys.executable, str(_PY_CLI), "token", "append-record",
                    "--tmpdir", effective_tmpdir, "--input", token_record], cwd=cwd)
```

When `effective_tmpdir` is None, the record stays out of `seen` so a later retry with a non-None `effective_tmpdir` can record it.

### UPDATED: `python/test_agents.py`

Add test `test_ingest_launcher_token_sidecar_none_effective_tmpdir_first_call`: calls with `tmpdir=None` / `implement_tmpdir=None` (so `effective_tmpdir` is None) on first call, then calls again with non-None `tmpdir`. Asserts `append-record` runs on the second call (not silently missed). Also asserts `record-vendor-sidecar` runs on both calls.

## Approach

- Item 1 is a two-line mechanical bug: the success path forgot to call `render-final-summary` before emitting markers. The fix mirrors the failure-path pattern already in the same file. A targeted test case is added to `test-design-step5c.sh` that verifies the render call actually happens on publish success (not just that the summary appears).
- Item 2 (`agents.py`) fixes a subtle dedup edge case: `seen.add()` should only mark a record as processed when it was actually processed. Moving the add inside the `if effective_tmpdir:` block restores the intended semantics.
- Ship.py refactoring was dropped (scope-reduced by plan review panel): the pre-rebase blocks are identical but no concrete defect was identified, and the refactor adds unnecessary regression risk.

## Acceptance

- review_status: main-agent-adjudicated
- rounds_completed: 2

diff_lines: 72

## Test plan
(no test plan section in plan-file)
