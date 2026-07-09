## Proposed Design Outline

### Goals
- Add a mechanical fail-closed completeness check in the design publish path: when guidelines are `present` and the run outcome is approved, `architectural-guideline-assessment.md` must exist.
- Hard-fail publish on the interactive path when the artifact is missing; record a category-keyed execution issue and stamp final-summary on non-interactive/resume paths.
- Emit machine lines for the persist attempt and result so future audits can distinguish "helper failed" from "never called."

### Non-goals
- Architectural invariant assessment (companion issue for a later PR).
- Changing Gate C prose as the primary fix (mechanical check is the fix; prose is a secondary note at most).
- Affecting runs where guidelines are `absent` or `invalid` (check passes automatically).

### Approach sketch
- Locate the publish/step5c entrypoint in `python/design_publish.py` or `python/design_lifecycle.py` and identify the earliest point after the outcome is known and before run-log commit staging.
- Add a `check_guideline_assessment_completeness(design_tmpdir, repo_root, interactive)` function: reads guidelines status; if `present` and outcome is approved, checks for `architectural-guideline-assessment.md`; returns `ok` or `missing`.
- Interactive path (`missing`): raise a typed `PublishError` / return a non-zero exit so Step 5c aborts with operator-visible error pointing to Gate C re-entry.
- Non-interactive/resume path (`missing`): call `record_execution_issue` to append to `execution-issues.md`; write a warning line to `final-summary.md`.
- Extend (or add) the design-side run-log completeness verifier after checking `test-verify-run-log-completeness` in the Makefile.

### Surfaces in scope
- `python/design_publish.py` and/or `python/design_lifecycle.py` (publish entrypoint; precise file to be confirmed by code inspection)
- `python/design_summary.py` (final-summary stamping on degraded path)
- `python/test_design_publish.py` or `python/test_design_lifecycle.py` (unit test: seed tmpdir with guidelines present + no artifact; assert fail/record; with artifact, assert pass)
- `Makefile` / `scripts/test-verify-run-log-completeness` (extend or add completeness verifier)
- `skills/design/references/approval-gates.md` and `scripts/test-design-structure.sh` (pin any Gate C prose change, only if prose is updated)

### Open questions
- None.
