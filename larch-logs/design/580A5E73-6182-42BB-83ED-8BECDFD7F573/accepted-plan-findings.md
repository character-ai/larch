### FINDING_1: Per-status Step 5b mapping omits NEXT_ACTION=skip-pipeline on three skip arms
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: blocking
- **Concern**: The per-status Step 5b mapping in `python/design_lifecycle.py` still omits explicit `NEXT_ACTION=skip-pipeline` on `skip-already-filed-sentinel`, `skip-no-items`, and `skip-all-security`. A global rule requires every skip status to emit `NEXT_ACTION=skip-pipeline`, but those three bullets list only `OOS_SKIP_BREADCRUMB` (and conditional annotate flags). An implementer following the per-status block can omit `NEXT_ACTION` while tests and Step 5b prose expect it on every skip path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add NEXT_ACTION=skip-pipeline to each of the three skip-arm bullets (mirror skip-sentinel) so the per-status table matches the global rule and parametrized tests.
  - From Cursor-Innovation: Add NEXT_ACTION=skip-pipeline to each of the three skip arms in the per-status mapping, mirroring skip-sentinel.
  - From Cursor-Pragmatic: Add NEXT_ACTION=skip-pipeline to each of the three skip-arm bullets, matching skip-sentinel
  - From Cursor-Requirements: Add NEXT_ACTION=skip-pipeline to each of the three per-status bullets, matching skip-sentinel.


