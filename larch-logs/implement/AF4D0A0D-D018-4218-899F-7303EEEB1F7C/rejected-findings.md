### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: Compatibility monkeypatch seam bypassed for proposer sidecar neutralization
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: important
- **Concern**: The split bypasses the compatibility-module monkeypatch seam for `_write_proposer_sidecar_and_neutralize`. Callers patching `review_pipeline._write_proposer_sidecar_and_neutralize` can still hit the original helper through `review_pipeline.review_core(...)` on the validation-exhausted path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: Runner injection no longer protects subprocess paths
- **Reviewer(s)**: codex-specialist-edge-cases, codex-generalist
- **Severity**: important
- **Concern**: The split drops or ignores the injected `runner` across gather and review-core subprocess paths. `gather_context(..., runner=fake_runner)` and `collect_findings(..., runner=fake_runner)` can fail with `TypeError`, while `review_core(..., runner=fake_runner)` can still invoke real subprocesses through emit-tally, tally-code-votes, dispatch-voters, and related helpers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases, codex-generalist: Address the concern above.


Vote tally: YES=0 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: Dispatch panel moved helpers broke external_defaults monkeypatch seam
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: important
- **Concern**: Moving panel helper functions into `review_dispatch_panel.py` broke the old `review_pipeline.external_defaults` monkeypatch seam. Tests or callers patching the compatibility module can be ignored because the moved helpers read `larch.core.external_defaults` from their own module globals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.
Vote tally: YES=0 NO=2 JUDGE_ERROR=0

