### FINDING_4: [OUT_OF_SCOPE] missing end-to-end coverage for fallback labels
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: There is no integration test asserting that rendered phase-detail gantt output includes the `(via fallback)` suffix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a small fixture-based test like `test_render_phase_detail_gantt_includes_signal_vendor_rows` if you want end-to-end render coverage.

