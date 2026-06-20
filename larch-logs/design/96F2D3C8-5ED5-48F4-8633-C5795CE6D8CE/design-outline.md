## Proposed Design Outline

### Goals
- A healthy `--merge` run that creates a PR must never freeze a committed `final-summary.md` / `manifest.json` as terminal `bailed` / `partial`; the pre-terminal snapshot records a success-classified non-terminal token (e.g. `pr-created`).
- The committed manifest stays consistent with on-disk reality: a present `final-summary.md` is never stamped `step8=false` (so `status` is not falsely `partial`).
- Committed-log classifiers treat a merged-PR dir as merged despite a stale `bailed` token (audit tolerance).

### Non-goals
- No speculative pre-squash `merged` flush and no rollback (fix #1 rejected).
- No post-merge log commit; NEVER #16 stays intact.
- No backfill / rewrite of existing committed run-log dirs.
- Genuine bails (no PR ever created) still record `bailed`.

### Approach sketch
- In `stall_recovery.normalized_outcome_values`, stop defaulting a pre-terminal snapshot to `bailed`: when a PR exists or is imminent and no stall/bail signal is present, emit a neutral non-terminal token; keep `bailed` for true bails.
- In `final_report._stamp_skipped_steps_for_terminal_report`, keep `step8` true when `final-summary.md` is present, so the snapshot manifest is not falsely `partial`.
- Add tolerance in the committed-log readers (`audit-runs scan-run`, `run-log verify-completeness`): reinterpret a merged-PR dir as merged regardless of a stale outcome token.
- Wire #4900 blocked-by #4877 during finalize.

### Surfaces in scope
- `python/stall_recovery.py` — outcome cascade.
- `python/final_report.py` — outcome consumption + manifest step8/status stamping.
- `python/ship.py` / `python/run_logs.py` — pre-PR flush sequencing, only if needed to populate the token.
- `python/audit_runs.py` — `scan-run` + `verify-completeness` tolerance.
- Tests: `python/test_stall_recovery.py`, `python/test_final_report.py`, `python/test_audit_runs.py` (+ ship/run-log tests as touched).

### Open questions
- Neutral token: reuse the existing `pr-created` (already in the `succeeded` set) vs a dedicated `pr-pending` / `in-progress`. Lean: reuse `pr-created`. Resolved in plan drafting.
- Audit-tolerance reach: `audit-runs` + `verify-completeness` only (lean), or also token/cost/fluff analyzers keyed on outcome.
