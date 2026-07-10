### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/implement/checks_lint_fix.py:685-703
- **Concern**: [SCOPE-REDUCTION] Per-tier content baselines should reuse existing digest capture instead of new parallel machinery. Scenario: The plan requires content-aware dirty-path detection, but `_delta_paths_after_dispatch()` compares path membership only; adding a second bespoke digest scheme duplicates `dispatch_helpers._write_prelaunch_digests()` already used for pre-dispatch content snapshots
- **Proposed resolution**: Reuse or factor the existing SHA-256 digest helper for per-tier pre/post snapshots on already-dirty tracked and untracked paths; treat content hash change as useful delta
