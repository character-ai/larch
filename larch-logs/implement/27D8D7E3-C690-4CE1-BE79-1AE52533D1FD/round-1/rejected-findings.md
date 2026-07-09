### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: SessionStart source contract is underspecified
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-statusline-reset
- **Severity**: major
- **Concern**: Reset routing depends on `payload["source"]`, but the in-repo SessionStart harnesses do not establish that the platform always supplies `source`. If `source` is absent or not matched as expected, reset can no-op and stale breadcrumbs keep rendering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: "Split hooks.json matchers for startup|clear vs resume|compact, or document and test real payload source; if source is absent default reset on startup hook invocation only."
  - From cursor-specialist-edge-cases: "Split hooks.json matchers for startup|clear vs resume|compact, or document and test real payload source; if source is absent default reset on startup hook invocation only."
  - From cursor-specialist-testing: "Add hook fixture with source=startup using real cli.py or split hooks.json matchers so reset does not depend on undocumented payload fields."
  - From dyn-dyn-statusline-reset: "Split hooks.json into separate SessionStart matchers (`startup|clear` vs `resume|compact`) so reset behavior is matcher-driven and does not rely on an undocumented JSON field, and add a harness fixture that asserts reset actually clears `current` on the startup-shaped payload the platform delivers."


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: `clear` can erase the active run mid-session
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-statusline-reset
- **Severity**: major
- **Concern**: Allowing `source=clear` to trigger session reset can delete `current` while a foreground run is still active and before a bgjob is registered, which silences the statusline for the remainder of that run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: "Limit RESET_SESSION_SOURCES to {\"startup\"} only, or add active-run guard before clearing on clear events."
  - From cursor-specialist-edge-cases: "Limit RESET_SESSION_SOURCES to frozenset startup only or add an active-session guard before deactivate_run on clear events"
  - From cursor-specialist-testing: "Add unit test documenting clear resets current with no live bgjob while preserving run logs"
  - From dyn-dyn-statusline-reset: "Restrict reset to `source=startup` only, matching the reported bug (“when Claude starts”), or add a foreground-session guard (for example, skip reset when an active design/implement tmpdir exists for the clone, mirroring `scripts/sessionstart-health.sh`) in addition to the bgjob check."


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: bgjob liveness errors fail open
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-statusline-reset
- **Severity**: minor
- **Concern**: `_clone_has_live_bgjob` suppresses registry exceptions and returns `False`, so unreadable or corrupt registry state can let reset proceed even when live breadcrumbs may still need protection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: "Fail closed on registry errors for mutation paths skip reset when iteration cannot complete and optionally record a bounded execution issue"
  - From dyn-dyn-statusline-reset: "Treat registry read/parse failures as “unknown liveness” and skip reset (fail closed), or distinguish `False` (no live job) from an error path that preserves `current`; at minimum, do not blanket-suppress `Exception` around `registry.iter_entries()`."


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** dismissed (0 YES)

### FINDING_4: no regression test for the no-`current` branch
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: minor
- **Concern**: The new coverage does not exercise the path where the clone directory exists but `current` is already absent, so a fresh-session reset regression could slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: "Add a test that creates the clone dir without `current`, calls `deactivate_run(repo)`, and asserts it returns false and leaves the directory tree untouched."


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

