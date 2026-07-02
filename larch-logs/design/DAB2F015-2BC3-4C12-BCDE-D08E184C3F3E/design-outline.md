## Proposed Design Outline

### Goals
- Emit a bounded, structured failure digest (check name, first failing file:line, first error line, failure count) from `checks run-relevant` on the failure path.
- Make the digest the primary artifact the orchestrator reads: Checks Failure Entry Macro and the `/review` Step 3 helper consume it first.
- Keep the full redacted log as the escalation fallback when the digest is insufficient.

### Non-goals
- No change to repair-loop/lint-fix coder-prompt construction; that path keeps reading the full log tail.
- No change to Python-side truncation or redaction rules.
- No new token-measurement instrumentation; before/after deltas come from existing committed token reports.

### Approach sketch
- Add a digest builder in `checks_run_relevant.py` that scans the already-redacted log for failure patterns and writes a capped digest file next to the existing `.redacted.log`.
- Emit `DIGEST_FILE=<path>` alongside `REDACTED_LOG_FILE=<path>` in the failure line.
- Thread `DIGEST_FILE` through the one shared `/implement` composite relay so Step 3, Step 5 self-review, Step 5 MAV/coder, and Step 6 all forward it; `/review` Step 3 already calls `checks run-relevant` directly.
- Update the Checks Failure Entry Macro reference and the `/review` Step 3 helper prose to read `DIGEST_FILE` first, falling back to `REDACTED_LOG_FILE`.

### Surfaces in scope
- `python/larch/implement/checks_run_relevant.py`
- `python/larch/implement/dispatch_commit_route.py`
- `skills/implement/references/checks-repair-loop.md`
- `skills/implement/SKILL.md` (Step 5 MAV resume KV-scan list)
- `skills/review/SKILL.md` (Step 3 helper prose)
- Test coverage for the above (`python/tests/implement/`)

### Open questions
- None.
