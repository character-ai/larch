## Proposed Design Outline

### Goals
- Port the committed run-log surface (larch-log, lib-larch-log, batches, flush, refresh, transcript, completeness, append-tool-failure, append-execution-issue) into Python with full envelope parity.
- Port scrubbing and verification helpers (redact-secrets, redact-tmpdir-paths, scrub-log-secrets, scrub-submodule-paths, verify-skill-called) into Python CLI verbs.
- Cut over every runtime caller; delete the retired bash scripts and their harnesses.

### Non-goals
- Behavioral changes beyond parity with the existing bash surface.
- Merging `flush-vendor-failure-diagnostics.sh` into Python (it is kept as bash, updated to call Python).
- Changing `scripts/render-session-transcript.py` or `scripts/run-log-terminal-outcomes.inc.bash` contracts.

### Approach sketch
- Extend `python/run_logs.py` with 13 `run-log` CLI main functions and shared helpers.
- Extend `python/redact.py` with 4 `redact` CLI main functions; add Cursor API key parity.
- Add `python/verify_skill.py` with the `verify skill-called` verb.
- Register 18 new CLI verbs in `python/cli.py`.
- Cut over all shell and Python callers; run stale-reference sweep; delete retired scripts and harnesses.

### Surfaces in scope
- `python/run_logs.py` (UPDATED)
- `python/redact.py` (UPDATED)
- `python/verify_skill.py` (NEW)
- `python/cli.py` (UPDATED)
- `python/session_env.py` (UPDATED)
- `python/test_run_logs.py`, `python/test_redact.py`, `python/test_verify_skill.py` (UPDATED/NEW)
- Surviving shell scripts with updated call sites (scripts/ and skills/)
- `docs/run-log-cli.md`, `docs/run-log-batches.md` (NEW)
- Retired scripts and harnesses (DELETED)
- `python/migrated-scripts.tsv` and `Makefile` (UPDATED)

### Open questions
- None.
