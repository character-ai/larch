## Proposed Design Outline

### Goals
- Confirm the Step 3 `implement-step3-checks` bgjob path inherits the #6580/#6595 false-orphan fixes.
- Pin the shared launcher/daemon owner-pid behavior with a regression test parameterized across step3, step5, step6, step7a, step8.
- Correct the #6591 record with one comment (posted by the /implement run, file-backed body).

### Non-goals
- No reopen or close-reason change on #6591.
- No daemon or launcher code changes unless drafting-time analysis finds an uncovered Step 3 trigger.
- No live end-to-end harness-kill reproduction.

### Approach sketch
- Trace `run-step-checks.sh --site step3` → `bgjob start --owner-pid "${LARCH_CLAUDE_PID:-$PPID}"` → daemon owner-validation to confirm coverage statically.
- Extend the existing `test_implement_dispatch.py` `bgjob_rc` parametrization (or a sibling test) across the shared-launcher steps.
- Add or extend a daemon-level false-orphan test only if the dispatch-level test cannot pin the owner-pid behavior; use fake clocks, no real sleeps.
- Plan step: implement run posts the #6591 correcting comment via `gh issue comment 6591 --body-file`.

### Surfaces in scope
- `python/tests/implement/test_implement_dispatch.py`
- `python/tests/bgjob/test_daemon.py` (only if a daemon-level gap shows up)
- `skills/implement/scripts/run-step-checks.sh`, `python/larch/state/session_env.py`, `python/larch/bgjob/daemon.py`, `python/larch/core/process_identity.py` (read-only confirmation surfaces)

### Open questions
- Does the Step 3 second-launch path have any owner-pid source or wrapper-lifetime trigger the #6580/#6595 fixes miss? Settled during Step 2b drafting inspection.
