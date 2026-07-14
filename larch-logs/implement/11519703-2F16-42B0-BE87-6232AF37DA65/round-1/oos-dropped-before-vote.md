### FINDING_1: Missing `gh` maps to return code 127 → `gh_issue_view_unavailable`
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: `proc.run` maps `FileNotFoundError` to return code `127`, which the new guard treats like the old `(127, None)` path → `gh_issue_view_unavailable`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### FINDING_2: Degraded outcomes on nonzero exit / empty stdout / bad JSON unchanged
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: Nonzero exit / empty stdout / bad JSON / non-object or empty mapping: same degraded outcomes as before; no new exception surface on the era-boundary path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### FINDING_3: Successful payload field handling unchanged
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: Successful payload: same field set, same `normalized` overwrite of `number`, same `_ground_truth_calibration_incentive_shipped` and `closedAt_unavailable` handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### FINDING_4: Argv shape and plan completeness verified
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: `issue_view_field_read` → `_issue_view_read` builds `issue view <N> --json <fields> --repo <repo>`, matching what `test-voter-calibration.sh` fakes expect. The added 120s timeout and transient retry from `_retry_read` are plan-intended (`requirements` / `both`), not a logic regression: they degrade to `gh_issue_view_unavailable` instead of hanging indefinitely. Plan-correctness / completeness: all planned edits are present (`proc`/`gh` imports, wrapper call, `_run_gh_json` removal, unchanged listing/repo-resolution/`python/larch/`). No contradictions between feature description and plan in the diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
