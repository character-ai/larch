### FINDING_1: `make test-cleanup` not wired in Makefile / CI
- **Reviewer(s)**: unknown-slot, Cursor-Edge
- **Severity**: important
- **Concern**: Acceptance and testing require `make test-cleanup`, but the plan does not add a `test-cleanup` recipe or include it in `test-harnesses-12`. The repo may list `test-cleanup` in `.PHONY` without a target, run only related harnesses (e.g. `test-cleanup-tmpdir`) in shard 12, and document `make test-cleanup` in `docs/linting.md` while `make lint` / `bash scripts/relevant-checks.sh` never run `skills/cleanup/scripts/test-cleanup.sh`—so implementer gates fail or new harness cases ship without CI coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Add `test-cleanup` target (`bash scripts/harness-timer.sh $@ bash skills/cleanup/scripts/test-cleanup.sh`), append to `test-harnesses-12` and `.PHONY`, or change acceptance to direct `bash skills/cleanup/scripts/test-cleanup.sh`
  - From Cursor-Edge: Add Makefile step: test-cleanup target, .PHONY entry, and test-harnesses-12 prerequisite (or fix acceptance to bash skills/cleanup/scripts/test-cleanup.sh and align docs)
  - From unknown-slot: Add a minimal Makefile block: `test-cleanup` recipe → `bash scripts/harness-timer.sh $@ bash skills/cleanup/scripts/test-cleanup.sh`, add `test-cleanup` to `test-harnesses-12`, and align `docs/linting.md:284` (plan already updates that row’s depth wording)

### FINDING_2: SECURITY.md not updated for changed retention / enumeration semantics
- **Reviewer(s)**: Cursor-Edge, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan omits `SECURITY.md` while cleanup behavior changes (e.g. away from depth-5 per-entry activity scan, per-entry find fail-closed skip, and date `+%s` fatal exit toward top-level `find -mtime`, no clock-fatal path, and different symlink handling). Auditors and operators may still read stale trust-boundary text that no longer matches post-PR behavior, including silent global-find no-op on enumeration failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Add SECURITY.md to Files to modify: replace depth-5 and date-fatal prose with top-level mtime via find -mtime, document exit 0 on enumeration failure, keep symlink and dangling-reap bullets
  - From Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements: Add ### UPDATED: SECURITY.md:234 — replace depth-5/date/per-entry-scan sentences with top-level mtime via find -mtime +N note tmp entries use ! -type l (not -L on glob) and drop date-fatal / per-entry activity-scan failure bullets; add SECURITY.md to cleanup.md Edit-in-sync list
