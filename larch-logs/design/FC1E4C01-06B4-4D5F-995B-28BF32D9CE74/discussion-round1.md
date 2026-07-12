## Decision 1: Dual-name adapter scope
- **Question**: Should `load_run_manifest` be extended to also check `run-manifest.json`, or only the new helper functions?
- **Resolution**: New helpers (`run_started_at`, `larch_version`) own the dual-name loop. `load_run_manifest` stays `manifest.json`-only (it's a manifest-acceptance gate for committed design/implement runs; `run-manifest.json` is a review-skill artifact).
- **Source**: codebase — callers that read `run-manifest.json` only need `started_at`/`larch_version`, not the full acceptance check.

## Decision 2: Which modules are excluded (dead-code batch)
- **Question**: Which three bypassing walker modules does #7008 remove?
- **Resolution**: `retro_fix_cursor.py`, `retro_v3_sweep.py`, `cleanup_implement_logs.py` are the expected deletions. Since #7008 is CLOSED but these files are still present, plan repointing for all currently-present callers; mark the retro trio as likely-deleted and include guarded stubs.
- **Source**: codebase (files still exist) + issue #7008 goal description

0 decisions resolved by user; all resolved from codebase inspection.
