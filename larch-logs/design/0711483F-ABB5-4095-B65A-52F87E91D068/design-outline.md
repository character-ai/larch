## Proposed Design Outline

### Goals
- Wire `/design` Gate C to call the existing `architectural-invariants persist-design-assessment` verb so approved runs commit `architectural-invariant-assessment.md`.
- Extend the #6746 fail-closed completeness validator to invariants: present + non-empty + approved run must produce the artifact or refuse publish.
- Give the invariant tier (the blocking tier) the same committed-run-log audit trail the guideline tier already has.

### Non-goals
- No change to the `persist-design-assessment` verb, artifact name, or atomic writer (all already exist and are tested).
- No refactor of, or behavior fix to, the existing guideline enforcement path (surgical mirror; note inconsistencies, do not fix them).
- No new run-log `verify_completeness` TSV entry; enforcement stays publish-time + run-log manifest, matching guidelines.

### Approach sketch
- Add invariant persist prose to Gate C in `approval-gates.md`, mirroring the guideline clean / deviation / absent-invalid branches, invariant persist before guideline persist, under the same fail-closed contract.
- Mirror the publish-time completeness validator for invariants in `design_publish.py` (+ `design_step5c.py` KV and refuse-reason plumbing), keyed on present AND non-empty content.
- Mirror the run-log required-artifact in `run_log_manifest.py`, the log-publish flow check in `design_log_publish_flow.py`, and the missing-assessment summary warning in `design_summary.py`.
- Pin the new Gate C prose in `scripts/test-design-structure.sh`; add invariant-branch unit tests beside the existing guideline ones.

### Surfaces in scope
- `skills/design/references/approval-gates.md`, `skills/design/references/finalize-step5.md`
- `python/larch/design/design_publish.py`, `design_step5c.py`, `design_log_publish_flow.py`, `design_summary.py`
- `python/larch/report/run_log_manifest.py`
- `scripts/test-design-structure.sh` plus mirrored Python tests

### Open questions
- None.
