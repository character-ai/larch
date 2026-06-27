## Proposed Design Outline

### Goals
- `record-escalation` records a specific, diagnosable reason per validation cause, replacing the generic `failure-detail-log-invalid`.
- Oversize detail logs (Hypothesis A) get truncated to the 64KiB cap and attached, not rejected; the escalation succeeds.
- The lint-fix checks-log path (Hypothesis B) resolves inside the `--tmpdir` that record-escalation validates against, so it is not rejected as outside-tmpdir.

### Non-goals
- No change to the `classify` command contract or its existing oversize / outside-tmpdir stderr assertions.
- No renaming or backfilling of historic `failure-detail-log-invalid` tokens in committed run logs.
- Keep the hard-fail for genuinely broken wiring: symlink, non-absolute, non-regular-file.

### Approach sketch
- Add `classify_failure_detail_log(...) -> str` returning `""` or a specific cause token. Keep `validate_failure_detail_log` as a thin bool wrapper so the `classify` read path and its tests stay unchanged (G-Py-4 fail-closed parity).
- In `record_escalation`: oversize truncates to a 64KiB-capped copy under tmpdir and records that path; any other invalid cause calls `hard_fail("failure-detail-log-<cause>")`; a valid log records as today.
- In `python/checks.py`: align the lint-fix checks-log root with the escalation `--tmpdir` so the detail log resolves under it.

### Surfaces in scope
- `python/larch/state/stall_recovery.py`: validation classifier, record-escalation branch, oversize truncation + re-verify (G-Py-8).
- `python/checks.py`: checks-log path / root alignment with the record-escalation tmpdir.
- `python/test_stall_recovery.py` and the checks test surface: specific-reason, oversize-truncate, containment coverage.

### Open questions
- Truncate mechanism: capped sidecar copy under tmpdir (record-escalation-local) vs. record original path and truncate on read (touches the shared compose path). Outline favors the local sidecar to keep blast radius minimal; finalized in plan drafting.
