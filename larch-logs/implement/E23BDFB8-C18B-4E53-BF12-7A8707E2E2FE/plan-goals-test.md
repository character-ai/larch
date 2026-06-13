## Goal
Implement issue #4180: [IMPLEMENTING] [BUG] ship.py postmerge does not write finalize-state.sh; step-18-finalize.sh restore fallback triggers instead.

## Implementation Plan
## Plan

## Source notes

- `approach-synthesis.txt`, `discussion-round1.md`, `brainstorm.md`, `design-outline.md`, and `.outline-approved` were not present in the repository cwd during discovery.
- The provided approach synthesis says `NO_SKETCHES`.
- This plan uses direct code and doc inspection plus the provided feature report and accepted reviewer findings.
- Keep the existing `restore-finalize-state` fallback unchanged.

## Approach

- Treat the likely teardown signal issue as the correctness fix.
- Expand process-kill skip logic from current process plus direct parent to the active process plus its full ancestor PID chain.
- Implement the skip change in both teardown surfaces:
  - `scripts/implement-finalize.sh`
  - `python/finalize.py`
- In Python, collect ancestors from live Python process IDs, not only from an ephemeral probe subshell.
- Add one breadcrumb after `finalize-state.sh` is written and merged.
- Update the teardown doc to match the new ancestor-skip behavior.
- Add focused regression tests.
- Do not add fsync hardening.
- Do not change `finalize-state.sh` content.
- Do not change Step 18 fallback branching.

## Files to modify/create

### UPDATED: scripts/implement-finalize.sh

Add a small helper near `kill_session_background_processes`:

- Collect ancestors for a supplied PID.
- Walk parent PIDs with `ps -o ppid= -p "$pid"`.
- Stop on empty, non-numeric, `0`, `1`, repeated PID, or a small depth cap such as 32.
- Return best-effort results.
- Do not fail teardown when `ps` fails.

Update `kill_session_background_processes`:

- Build a skip set from:
  - `$$`
  - the immediate parent
  - every collected ancestor for `$$`
- Use the same skip check in both SIGTERM and SIGKILL loops.
- Keep current fixed-string argv matching.
- Keep existing warning text and counts.
- Keep current behavior for stale non-ancestor session processes.

### UPDATED: python/finalize.py

Add `_collect_ancestor_pids(runner, pid, max_depth=32)`:

- Return a `set[str]`.
- Use `runner.run(["ps", "-o", "ppid=", "-p", pid])`.
- Strip and validate numeric output.
- Stop on empty, non-numeric, `0`, `1`, repeat, or depth cap.
- Treat failures as best effort.

Update `kill_session_background_processes`:

- Seed `skip` with live Python process IDs from `os.getpid()` and `os.getppid()`.
- Collect ancestors from `os.getpid()` or, at minimum, from `os.getppid()` when it is numeric and non-root.
- Make the live-process ancestor walk mandatory for the Python parity fix.
- Keep the existing shell probe only as best-effort extra coverage.
- Do not rely on the probe subshell `$$` as the primary ancestor seed.
- Add numeric values from the probe to `skip` when available.
- If the probe shell PID has already exited and `ps -p <probe_pid>` is blank, continue with the live Python ancestor chain.
- Leave process discovery and TERM behavior otherwise unchanged.
- Do not add SIGKILL parity in Python unless already required by tests.

### UPDATED: python/ship.py

Update `_write_terminal_finalize_if_terminal`:

- After `finalize.write_finalize_state_merged(path, data)` succeeds, emit:
  - `_breadcrumb("finalize-state-written", ...)`
- Include enough detail to confirm the terminal state write:
  - path
  - outcome
  - step, with an empty-safe value
- Emit the breadcrumb only after the merged write succeeds.
- Do not catch write exceptions.
- Do not emit the breadcrumb for early-return outcomes or disallowed tmpdirs.

### UPDATED: scripts/test-implement-finalize.sh

Extend the existing `ps` stub:

- Add per-queried-PID parent responses.
- Support a parent map format suitable for shell tests, for example `pid=ppid` entries.
- Preserve existing simple stub modes for current tests.
- Document the expected lookup sequence for the ancestor skip regression.

Add a teardown regression test:

- Launch two background scripts under the sandbox tmpdir.
- Make the process list include:
  - one stale background process that should be killed
  - one fake ancestor process whose argv contains `$IMPLEMENT_TMPDIR` and should be skipped
- Configure the per-PID stub parent map so the fake ancestor appears in the collected chain.
- Run `teardown`.
- Assert the stale process was killed.
- Assert the fake ancestor process is still alive.
- Clean up the fake ancestor process at test end.
- Assert the warning still reports only the killed stale process.

### UPDATED: python/test_finalize.py

Add a unit test for Python cleanup skip behavior:

- Use `RecordingRunner` with strict responses.
- Simulate `os.getpid()` and `os.getppid()` through monkeypatching.
- Model the old failure path:
  - the transient probe shell PID returns no `ps` row
  - the live PPID chain contains a grandparent PID
- Return a process list containing:
  - the grandparent PID with the tmpdir in argv
  - a stale non-ancestor PID with the tmpdir in argv
- Assert `kill_session_background_processes` returns `True`.
- Assert `kill -TERM` is called only for the stale non-ancestor PID.
- Assert no kill call targets the ancestor PID.
- Assert the test would fail if the implementation walked only from the transient probe shell PID.

### UPDATED: python/test_ship.py

Add or extend a focused breadcrumb assertion:

- Exercise a terminal OK finalize-state write path.
- Capture stderr.
- Assert `ship.py: finalize-state-written` appears after the write path succeeds.
- Assert invalid tmpdir and non-terminal outcomes still do not create `finalize-state.sh`.
- Avoid brittle full stderr matching.

### UPDATED: scripts/implement-finalize.md

Update the teardown process cleanup paragraph:

- Replace the direct-parent-only statement with full ancestor-chain skip semantics.
- Keep the doc scoped to behavior.
- Do not rewrite unrelated teardown documentation.

## Edge cases

- `ps` may fail or return blank output. Continue with the skip PIDs already known.
- A parent process may exit during collection. Stop the walk and continue.
- A probe subshell may exit before Python can inspect it. Do not depend on that PID for Python ancestor coverage.
- A PID chain may loop due to bad stub output or platform oddity. Stop on repeats.
- PID reuse may cause an unrelated process to be skipped. This is safer than killing the active teardown lineage.
- Process argv may use a physical tmpdir path such as `/private/tmp`. Keep the current lexical plus physical match.

## Failure modes

- If ancestor collection is too broad, stale processes may survive. The session cleanup still proceeds.
- If ancestor collection is too narrow, teardown may still signal a wrapper process in the active chain.
- If Python starts its walk from only the transient probe shell PID, the probe may be dead and the parity fix may fail. Walk from live Python process IDs.
- If the breadcrumb is placed before the merged write, it can falsely confirm success. Place it after the merged write only.
- If tests use real ancestor processes, they can kill the harness. Use controlled background processes and stubbed parent data.

## Testing strategy

- Run `python3 -m pytest python/test_finalize.py python/test_ship.py`.
- Run `bash scripts/test-implement-finalize.sh`.
- Run `bash scripts/relevant-checks.sh`.
- Manually inspect breadcrumb text in captured stderr tests only. Do not rely on exact elapsed or full log output.

## Acceptance

- `kill_session_background_processes` in `scripts/implement-finalize.sh` skips `$$`, direct parent, and all ancestor PIDs during SIGTERM and SIGKILL passes.
- Python `kill_session_background_processes` seeds `skip` from `os.getpid()` / `os.getppid()` and walks the live ancestor chain.
- `_write_terminal_finalize_if_terminal` emits `ship.py: finalize-state-written` breadcrumb on every terminal OK write.
- All three existing test suites pass: `pytest python/`, `test-implement-finalize.sh`, `relevant-checks.sh`.
- New ancestor-skip regression test in bash confirms ancestor process is not killed.
- New Python unit test confirms ancestor PID is excluded from SIGTERM targets.

diff_lines: 143

## Test plan
(no test plan section in plan-file)
