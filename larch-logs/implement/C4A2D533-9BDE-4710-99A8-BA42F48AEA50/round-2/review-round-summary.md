# Review Round 2

- Mode: `diff`
- 1 accepted, 4 rejected (2 neutral)

## Accepted Findings

### FINDING_1: ThreadPoolExecutor timeout does not terminate in-process render work
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-generic-output.txt, dyn-migration-parity-output.txt
- **Severity**: important
- **Concern**: `_render_phase_detail_best_effort` in `python/progress_report.py:840-868` creates a fresh `ThreadPoolExecutor` on every call and uses `shutdown(wait=False, cancel_futures=True)` after timeout. On `future.result(timeout=15)` timeout the wrapper returns `""`, but the worker thread keeps running `render_phase_detail()` to completion on a non-daemon thread. Unlike the retired bash path (`subprocess.run(..., timeout=15)`) that killed the renderer process, in-process render work is not reliably bounded. During live Step 5 progress (frequent `_call_render_phase_detail()` / `_render_review_detail()` polling), overlapping timed-out renders can stack unbounded threads and CPU, partially defeating the 15s best-effort non-blocking contract from #4537. A pathological render can also keep a one-shot final-summary or design publish Python process alive at interpreter shutdown.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: use a module-level single-worker executor with daemon threads, or document and cap concurrent timed renders; alternatively isolate rendering in a subprocess that can be killed on timeout like the retired bash path.
  - From cursor-specialist-edge-cases-output.txt: Use a terminable isolation boundary (subprocess with timeout, or multiprocessing with terminate/kill), or enforce a single-flight/semaphore so timed-out renders cannot stack.
  - From codex-generic-output.txt: Run the best-effort renderer in a killable subprocess or `multiprocessing.Process`, terminate it on timeout, and return `""`.
  - From dyn-migration-parity-output.txt: Use a single shared executor (max_workers=1) or a lock so only one best-effort render runs at a time; on timeout, cancel or isolate work the way subprocess kill did (for example, keep subprocess with timeout for best-effort callers only, or run the core renderer in a dedicated short-lived process).


