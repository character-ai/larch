# Review Round 1

- Mode: `diff`
- 2 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Stale `complexity-baseline.json` for `run_dispatch_main`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Working tree sets `run_dispatch_main` complexity to `C901=14`, `PLR0912=14`, `PLR0915=56` and lint passes, but those baseline updates may not be committed with the dispatch lock changes.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_2: `lock_fd` leak when nonblocking `flock` fails on contention
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-dyn-dispatch-concurrency-output.txt
- **Severity**: important
- **Concern**: On the committed branch snapshot (`0ee145231`), when `lock_path.open("w")` succeeds but nonblocking `fcntl.flock(..., LOCK_NB)` fails with contention, the `except OSError` path returns exit code 2 without closing `lock_fd`. Each rejected concurrent caller leaks one file descriptor; in a long-lived orchestrator this can accumulate until `EMFILE` and break later dispatches or unrelated I/O. Uncommitted working-tree edits (`lock_fd = None` plus close in `except`) appear to be the right fix but are not in the committed snapshot; ensure they are staged and committed before merge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Close lock_fd in except OSError when open() succeeded; commit with matching complexity-baseline.json bump for run_dispatch_main.
  - From cursor-specialist-testing-output.txt: Initialize lock_fd = None; close lock_fd in except when not None; commit matching complexity-baseline bump (14/14/56).
  - From dyn-dyn-dispatch-concurrency-output.txt: Initialize `lock_fd = None` before the acquire `try`, close it in the `except OSError` path when non-`None`, and keep the existing `finally: lock_fd.close()` on the success path so contention rejections and normal completion both release the descriptor.


