### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Explicit coder-unavailable tests do not assert breadcrumb suppression
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Explicit coder-unavailable harness cases do not verify that coder breadcrumbs are suppressed when `LARCH_QUIET_BREADCRUMBS=1`. A coder-unavailable bail could still emit `step0: coder=` and confuse breadcrumb-count expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Cursor-first implicit default changes security posture
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: The implicit omitted-coder default is now Cursor-first, selecting a higher-trust Cursor path when both external tools are available. Operators who relied on Codex-first sandboxing may unexpectedly get Cursor full-trust writes unless they explicitly pass `--coder=codex`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: SECURITY.md no longer documents Step 2 mechanical guards clearly
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Condensed security documentation removed visibility into Step 2 mechanical guards that still exist in code. Reviewers or operators may incorrectly infer that submodule, path, or commit backstops were removed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: Deferred runs may reach coder selection before tracking metadata is published
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Widened `should_run_post_tracking_phase` lets deferred `POSTED=false` paths run `phase_coder_select`, so Step 2 can receive `coder=` before tracking metadata is fully published. This weakens the audit trail unless intentional and documented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Step 2.4 Claude messaging does not distinguish explicit Claude from fallback
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Step 2.4 messaging lacks a reliable explicit-argv signal for `--coder=claude`, so explicit Claude selection and implicit fallback-to-Claude paths can produce indistinct or misleading operator messaging. The implicit Codex-unavailable path may also miss the expected warning text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Coder harness labels do not match planned B11-B17 range
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Coder tests use `B5-coder-*` labels instead of the plan-specified contiguous `B11`-`B17` range, which can make issue and harness cross-references drift from actual test names.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

