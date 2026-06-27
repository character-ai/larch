### OOS_1: [OUT_OF_SCOPE] terminal-outcome regexes omit shipping and merged for audit completeness
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: `python/run_log_tolerance.py` terminal-outcome regexes omit `shipping` and `merged`. Audit completeness rules may not classify frozen `shipping` snapshots on later-merged PRs. Operators lack guidance on whether tolerance helpers should be extended if `shipping` becomes a common committed heading.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] shipping outcome token undocumented in run-logs docs
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The new `shipping` outcome token is undocumented for consumers in `docs/run-logs.md`. Operators and audit tools lack canonical guidance on provisional committed outcomes. Add `shipping` to run-logs outcome vocabulary and provisional-snapshot semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] write_final_report_comment failures are warn-only in ship.py
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: In `python/larch/implement/ship.py` (2003–2007), `write_final_report_comment` failures are warn-only breadcrumbs (pre-existing). The tracking issue may lack implement `larch:final-summary` even when the PR merges. Upsert failures should be surfaced in execution-issues or stall state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

