## Plan

## Approach

Add the missing Step 5 batch flush on normal terminal exits.

Keep the change narrow:
- Flush before `_emit_step5_envelope(...)` on `cap-hit`.
- Flush before `_emit_step5_envelope(...)` on `complete`.
- Match the current `stall` and `self-review-required` ordering.
- Leave `mav-resume-past-cap` unchanged.

Surface flush wrapper failures without changing the terminal review result:
- Replace `contextlib.suppress(Exception)` in `_flush_review_batches_for_result(...)`.
- On exception, print a warning to stderr with `_err(...)`.
- Append an `execution-issues.md` `Warnings` entry with `run_logs.append_execution_issue(...)`, wrapped in its own `contextlib.suppress(OSError)` (matching the `_append_record_escalation_tool_failure` precedent at `review_and_fix.py:437-438`), so a failure writing the warning itself cannot raise.
- Keep Step 5 return behavior unchanged. A failed observability flush should warn, not convert a converged review into a stall. The stderr warning is the only unconditional side effect of the flush-failure path; the execution-issues append is best-effort on top of it.

Make the final report source explicit:
- Remove the `_read_kv(path=ship, key="CODE_REVIEW_LINE")` branch.
- Derive the code-review line only from `code-review-tally.json`.
- Keep the plan-review line behavior unchanged.

## Files to modify/create

### UPDATED: python/larch/review/review_and_fix.py

- Add `_flush_review_batches_for_result(...)` to the `terminal_status == "cap-hit"` branch before the envelope.
- Add `_flush_review_batches_for_result(...)` to the final `complete` branch before the envelope.
- Replace the suppressing wrapper with `try/except Exception as exc`.
- Emit a concise warning via `_err(...)` unconditionally on exception.
- Wrap the `run_logs.append_execution_issue(...)` call in its own `contextlib.suppress(OSError)` so a failure writing the warning cannot propagate out of `_flush_review_batches_for_result` and turn a `complete`/`cap-hit` exit into a stall.
- Do not change the `mav-resume-past-cap` stub flush.

### UPDATED: python/larch/report/final_report.py

- Change `code_line` derivation to:
  - `_derive_review_line(run_dir=run_dir, filename="code-review-tally.json")`
- Do not add a `CODE_REVIEW_LINE` producer.

### UPDATED: python/tests/review/test_review_and_fix.py

- Extend or add Step 5 loop regression tests for:
  - `complete` terminal exit calls `flush_review_batches(...)`.
  - `cap-hit` terminal exit calls `flush_review_batches(...)`.
- Assert flush call arguments include the expected `run_id`, `rounds`, accepted count, rejected count, exonerated count, and neutral count.
- Add a wrapper-failure test:
  - monkeypatch `flush_review_batches(...)` to raise.
  - assert Step 5 still returns the expected terminal rc.
  - assert stderr contains a warning.
  - assert `execution-issues.md` receives a `Warnings` entry.
- Add a second wrapper-failure test proving the fix is not itself fragile:
  - monkeypatch `flush_review_batches(...)` to raise AND monkeypatch `run_logs.append_execution_issue(...)` to also raise (e.g. `OSError`).
  - assert Step 5 still returns the expected `complete`/`cap-hit` terminal rc (not a stall), proving the execution-issues append failure is fully contained.

### UPDATED: python/tests/report/test_final_report.py

- Add coverage that a stale `CODE_REVIEW_LINE` in `ship-pr-state.sh` no longer overrides `code-review-tally.json`.
- Keep existing `_derive_review_line(...)` behavior tests as-is.

## Edge cases

- `complete` can come from several round statuses, including `no-findings`, `no-changes`, and `prune-skipped`. The flush should run for all mapped complete paths.
- `cap-hit` can result after a `fix-applied` round stops at the configured cap. It should flush with the current cumulative `RoundResult`.
- If `flush_review_batches(...)` raises, Step 5 should still emit its terminal envelope.
- If the `execution-issues.md` append itself raises (for example a transient `OSError`), that failure must not propagate; the stderr warning already fired and Step 5's terminal rc must stay unaffected.
- If `flush_review_batches(...)` returns `False`, keep current semantics unless the implementer finds an existing wrapper contract that treats false as warn-worthy. Do not expand scope into `batch_report.py`.

## Failure modes

- A flush placed after envelope emission can be skipped by future early returns. Keep it before the envelope.
- Turning a flush warning into a hard Step 5 failure would change workflow semantics and may block successful implementations.
- An unguarded execution-issues append inside the flush-failure handler would let a second, unrelated I/O failure convert a successful review into a stall; guard it with its own suppression.
- Adding a `CODE_REVIEW_LINE` producer would create two sources of truth, contrary to the approved scope.
- Editing historical `larch-logs/` backfill data is out of scope.

## Testing strategy

Run targeted tests only:

```bash
python3 -m pytest python/tests/review/test_review_and_fix.py -k "step5 and (flush or cap_hit or complete or warning)"
python3 -m pytest python/tests/report/test_final_report.py -k "code_review or final_report"
```

If the exact `-k` filters miss new tests, run the two full files:

python3 -m pytest python/tests/review/test_review_and_fix.py python/tests/report/test_final_report.py

Then run Python lint for changed Python files if available:

make py-lint

## Acceptance

Run targeted tests only:

```bash
python3 -m pytest python/tests/review/test_review_and_fix.py -k "step5 and (flush or cap_hit or complete or warning)"
python3 -m pytest python/tests/report/test_final_report.py -k "code_review or final_report"
```

If the exact `-k` filters miss new tests, run the two full files:

python3 -m pytest python/tests/review/test_review_and_fix.py python/tests/report/test_final_report.py

Then run Python lint for changed Python files if available:

make py-lint

review_status: ok
rounds_completed: 2
difficulty: MODERATE
diff_lines: 80
