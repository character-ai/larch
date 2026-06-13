## Proposed Design Outline

### Goals
- Fix all 6 token-record sidecar ingestion and env-hygiene gaps across lint-fix, research/validation, drafter, and ship paths.
- Ensure `LARCH_TOKEN_SESSION_ID` and other ledger env vars are cleared at every `token record-vendor-sidecar` call site.

### Non-goals
- Refactoring the token ledger subsystem beyond what the 6 items require.
- Adding new token telemetry surfaces not mentioned in the issue.

### Approach sketch
- **Item 1 (lint-fix-loop.sh)**: replace bare `IMPLEMENT_TMPDIR=... python3 ... token record-vendor-sidecar` with `env -u LARCH_TOKEN_LEDGER -u LARCH_TOKEN_SESSION_ID -u DESIGN_TMPDIR -u RESEARCH_TMPDIR -u SESSION_ENV_PATH IMPLEMENT_TMPDIR=...`; capture stderr to relay warnings rather than discarding via `>/dev/null 2>&1`.
- **Item 2 (research harness)**: add test coverage to `python/test_checks.py` (or `scripts/test-lint-fix-loop.sh`) for the sidecar ingestion path.
- **Item 3 (launch-codex-drafter.sh)**: on `cp` failure, do not emit `TOKEN_RECORD=` pointing at a non-existent stable path; suppress the KV or emit a `TOKEN_RECORD_MISSING=true` flag instead.
- **Item 4 (Python ship driver)**: verify whether `ci_monitor.py`'s `_make_default_launch_fn` already covers recovery sidecar ingestion; if a gap exists in `python/agents.py`'s `ingest_launcher_token_sidecar`, pass a clean env dict (similar to `checks.py`'s `_lint_fix_token_env`) when calling `record-vendor-sidecar`.
- **Item 5 (validation-phase.md)**: add a Codex sidecar ingestion block after `collect-agent-results.sh` settles, mirroring the block in `research-phase.md` (lines 188-215) including both `token append-record` and `token record-vendor-sidecar` with proper env -u.
- **Item 6 (env -u hygiene)**: extend env -u unsets to include `LARCH_TOKEN_SESSION_ID` in `ship-pr.sh` `ship_pr_ingest_token_record_once`, in `agents.py` `ingest_launcher_token_sidecar`, and in `design-step2b-drafter.sh`; confirm research-phase.md already has the fix.

### Surfaces in scope
- `scripts/lint-fix-loop.sh`
- `skills/research/references/research-phase.md` (harness only, prose may not change)
- `skills/research/references/validation-phase.md`
- `scripts/launch-codex-drafter.sh`
- `python/ship.py` or `python/ci_monitor.py` / `python/agents.py`
- `scripts/ship-pr.sh`
- `skills/design/scripts/design-step2b-drafter.sh`
- Test files: `python/test_checks.py` or `scripts/test-lint-fix-loop.sh`

### Open questions
- For Item 4, is the existing `ingest_launcher_token_sidecar` in `agents.py` the correct fix site or is there a separate recovery path in `ci_monitor.py` that bypasses it?
