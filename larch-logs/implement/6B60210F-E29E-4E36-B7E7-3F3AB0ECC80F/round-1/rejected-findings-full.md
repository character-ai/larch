### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: logging_util dataclasses are mutable
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Mutable dataclasses in `logging_util.py` are inconsistent with the frozen-record convention used elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: python/.pylintrc is mostly stock template
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The 661-line `.pylintrc` appears mostly stock, making active overrides hard to review and future diffs noisy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: pr_create dedup test asserts oversimplified argv
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The `pr_create` dedup test does not assert the full `gh pr list` argv, so regressions in flags like `--head` or `--repo` could pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: gh mutating payloads are not centrally redacted
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Mutating GitHub helpers may publish unredacted body/title text, allowing secrets or tmpdir paths from plans/logs to reach public GitHub surfaces in future Python wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_25: logging/journal APIs accept arbitrary unredacted strings
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Breadcrumb and JSONL logging utilities can persist arbitrary unredacted text, which future callers may use with stderr or plan content containing secrets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_26: python redact lacks streaming mode
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `python/redact.py` lacks the bash streaming redaction mode, so large future sidecar blobs may require full buffering or skip parity with streaming call sites.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_27

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_27: CI installs Python dev tools without hash pinning
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Python CI installs dev tools from package indexes without hash-locked requirements or a documented trusted install policy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_30

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_30: pr_create lacks post-create conflict recovery
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-retry-idempotency-output.txt
- **Severity**: latent
- **Concern**: PR creation is check-then-create only and lacks bash-style already-exists conflict recovery, so concurrent PR creation can surface as an unhandled error instead of returning the existing PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-retry-idempotency-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_32

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_32: run_waterfall API omits planned classify_fn
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The `run_waterfall` API omits the `classify_fn` described in the plan, risking duplicate or mismatched classification in later phases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_33

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_33: extra gitleaks edit is outside enumerated plan files
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `.gitleaks.toml` is an extra root edit beyond the four files enumerated in the plan and should be documented as a required CI adjunct if retained.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_34

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_34: config constant tests cover only a sample
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `test_config.py` samples a handful of constants, so renamed or removed public config constants may go untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_52

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_52: binary_present truthiness diverges from bash
- **Reviewer(s)**: dyn-waterfall-launch-output.txt
- **Severity**: important
- **Concern**: `classify_launch_failure` treats truthy strings such as `"0"` as binary-present, while bash only treats `1|true|yes` as present, so shell bridge values can misclassify binary-missing health failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-waterfall-launch-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_53

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_53: run_waterfall first-attempt short-circuit may diverge when tiers are skipped
- **Reviewer(s)**: dyn-waterfall-launch-output.txt
- **Severity**: latent
- **Concern**: Short-circuit logic uses list index rather than first launched attempt, which can diverge from bash if future tier skipping is modeled in Python.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-waterfall-launch-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: parse_json_stdout is unused
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `parse_json_stdout` in `python/git.py` is dead, untested API surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

