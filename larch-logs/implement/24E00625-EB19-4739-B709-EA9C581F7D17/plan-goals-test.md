## Goal
Implement issue #5307: [IMPLEMENTING] [BUG] implement run-dispatch has no concurrency guard — concurrent dispatches to the same IMPLEMENT_TMPDIR both proceed.

## Implementation Plan
## Summary

`python/cli.py implement run-dispatch` has no concurrency guard. Two callers with the same `--implement-tmpdir` pass all precondition checks and both proceed to spawn a full Codex/Cursor implementation session. The existing `spawn_coder_file` check in `step2_dispatch_main` is a sequential-reuse guard (different-coder detection), not a concurrency guard — two concurrent dispatches with the same coder both pass it. Each dispatch also deletes the other's manifest outputs on entry, so the race can leave the working tree in an inconsistent state.

## Original report

During an `/implement` run for issue #5277, two background `run-dispatch` invocations (task IDs b21r20o1o and b5tt38gys) were launched concurrently against the same `IMPLEMENT_TMPDIR`. Both completed: b5tt38gys finished at ≈1419s; b21r20o1o ran for ≈5166s, spanning the entire code-review phase. Symptoms:

- Two `codex-implement` entries in `timing-report.json` (min=1419s, max=5166s, samples=2).
- `WARN_PLAN_FILES_UNTOUCHED=true count=11` in the late dispatch's envelope — it ran on an already-committed tree.
- A spurious full-width `codex/impl-transcript` bar in the round-1 Gantt chart (the late dispatch's vendor-row overlapped the entire review window and was clamped to it by `_progress_vendor_rows`).

## Reproduction scenario

1. Start an `/implement` session that reaches Step 2.
2. While the first `run_in_background` `implement run-dispatch` call is in flight, issue a second `implement run-dispatch` call with identical `--implement-tmpdir` and `--coder` arguments.
3. Both dispatches proceed past all precondition checks and spawn concurrent Codex/Cursor sessions against the same working tree.

The specific double-call in issue #5277's run was an orchestrator error (re-issuing the command while checking progress), but the underlying vulnerability is in the dispatcher: there is no guard that would have rejected the second call.

## Expected behavior

The second `run-dispatch` call should fail immediately with a non-zero exit and a clear error message such as:

```
implement run-dispatch: another dispatch is already running in this tmpdir
```

## Observed behavior

Both dispatches pass all precondition checks in `run_dispatch_main` (directory existence, `session-env.sh`, `feature-description.txt`, `plan.txt`, binary availability) and proceed to `step2-dispatch`. The `spawn_coder_file` check in `step2_dispatch_main` detects coder mismatches only; two same-coder dispatches both pass it. Both spawn a full implementation session.

Additionally, each dispatch deletes the other's manifest outputs at entry (`python/implement_dispatch.py` line ~1950):

```python
for path in (st.manifest_path, st.manifest_raw_path, st.qa_pending_path, st.transcript_path, ...):
    with contextlib.suppress(OSError):
        path.unlink()
```

This means whichever dispatch starts second wipes the first's outputs, potentially destroying a committed manifest if the first dispatch had finished.

## Root cause analysis

`run_dispatch_main` (`python/implement_dispatch.py` lines 1197-1266) performs only static precondition checks (directory/file existence, binary availability). It has no lockfile, no in-progress sentinel, and no exclusive-access mechanism. Any number of callers with the same `--implement-tmpdir` can pass these checks simultaneously.

The `spawn_coder_file` write in `step2_dispatch_main` (lines 1913-1917) is the closest thing to a guard:

```python
if st.spawn_coder_file.is_file():
    if st.spawn_coder_file.read_text(...).strip() != st.coder:
        return st.emit_bailed("coder-mismatch-tmpdir-reuse")
else:
    _write_text_atomic(st.spawn_coder_file, st.coder + "\n")
```

But this is a sequential-reuse guard for coder consistency across resume runs, not a concurrency guard. If two dispatches with the same coder race: the first writes `codex`, the second reads `codex`, sees no mismatch, and continues. There is no atomic `O_CREAT | O_EXCL` creation that would serialize them.

## Evidence

- `python/implement_dispatch.py` lines 1197-1266 (`run_dispatch_main`): no lock or sentinel acquired before calling `step2-dispatch`.
- `python/implement_dispatch.py` lines 1913-1917 (`step2_dispatch_main`): `spawn_coder_file` write-or-check uses `_write_text_atomic` but does not use exclusive-create semantics that would detect a concurrent writer.
- `python/implement_dispatch.py` lines 1950-1952: manifest/transcript/qa-pending paths are unconditionally unlinked at dispatch entry.
- `larch-logs/implement/32DCC508-AED2-4EAF-951B-47318491E577/timing-report.json`: two `codex-implement` entries (min=1419s, max=5166s, samples=2).
- `WARN_PLAN_FILES_UNTOUCHED=true count=11` in the late dispatch's output: confirms it ran on an already-committed tree.

## Affected files

- `python/implement_dispatch.py` — `run_dispatch_main` (primary fix site), `step2_dispatch_main` (secondary; manifest-deletion and spawn_coder_file logic).
- `python/test_implement_dispatch.py` — regression harness; needs assertions for the new reject path (per `.claude/rules/launcher-argv-test-coverage.md`).

## Suggested fix(es)

Add an exclusive lockfile at `$IMPLEMENT_TMPDIR/dispatch.lock` acquired at the top of `run_dispatch_main`, before `step2-dispatch` is forked. Use non-blocking `fcntl.LOCK_EX | fcntl.LOCK_NB` so a second concurrent caller gets an immediate, clear error:

```python
import fcntl
lock_path = tmpdir / "dispatch.lock"
try:
    lock_fd = open(lock_path, "w")
    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
except (OSError, BlockingIOError):
    _err("implement run-dispatch: another dispatch is already running in this tmpdir")
    return 2
```

A lighter alternative: a `dispatch-in-progress` sentinel created with `O_CREAT | O_EXCL` (atomic exclusive-create) at entry and unlinked at exit. Either approach must be covered by a new reject-path assertion in `python/test_implement_dispatch.py` in the same PR.

## Open questions

- Should the lock also be checked in `step2_dispatch_main` directly, or is guarding `run_dispatch_main` sufficient (since `step2_dispatch_main` is always called through `run_dispatch_main` in production)?
- Should the manifest-deletion block (lines 1950-1952) be conditioned on holding the lock, or should it remain unconditional for the sequential-resume case?
- `fcntl.flock` is not available on Windows; if cross-platform support is ever needed, use `O_CREAT | O_EXCL` sentinel files instead.

## Test plan
(no test plan section in plan-file)
