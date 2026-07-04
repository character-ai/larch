# Discussion Round 1 — Resolved Decisions

## Decision 1: Fence fix shape (work items 1/2)
- **Question**: Keep the every-py-exit `kill-active-leg` fence in larch-run.sh with identity validation + ownership token, or remove the fence entirely and rely only on the dispatcher's in-process cleanup?
- **Resolution**: Validate and keep. The fence stays as the crash backstop (covers SIGKILL of the whole task group). Add identity validation so it signals only a positively identified leg, plus an ownership token so bystander wrappers no-op on live legs. Both defects (stale-recycled pgid; same-session friendly fire) must close; crash cleanup must survive.
- **Source**: user

## Decision 2: Audit scope (work item 5)
- **Question**: How much of the persisted/retained-PID signal-site audit belongs in this PR?
- **Resolution**: Full fix in-PR. Audit every `os.kill` / `os.killpg` / `kill --` / `pkill`-family site that signals a persisted or retained PID, and fix every gap found in this same PR, however large the diff grows.
- **Source**: user

## Hard constraints (from issue #6213 + repo rules)
- No larch process may signal a PID/pgid it cannot positively identify as the process it recorded (identity = start time + command signature, not `kill -0`).
- Never SIGKILL-escalate an unvalidated target.
- Every larch-initiated kill logs target pgid/pids, resolved victim command line, caller, and reason BEFORE signaling; remove `2>/dev/null` silencing on the fence call (work item 4).
- Committed shell must stay Bash 3.2 compatible; new logic goes in Python behind `python3 python/cli.py` (python-first rule).
- `larch-run.sh` template changes require same-PR `scripts/test-implement-fence-shape.sh` EXPECTED updates; launcher/dispatcher changes require same-PR harness updates (`python/test_implement_dispatch.py`, `scripts/test-implement-structure.sh` pins).
- Do not change the single-runner invariant or serialize runners; scope is kill safety only.
- `kill_session_background_processes` (finalize.py ps-scan reaper) scoping stays as-is; it gains logging only.
